# Common likeness mistakes and diagnostics

> Likeness failures in portrait sculpture are few and predictable: eyes too big, too open or too far forward; a face too flat and a cranium too short; nose width and projection wrong; lips idealised; ears misplaced; the sitter's asymmetries erased. Many come from the reference rather than the hand: wrong camera distance, unsolved head pitch, mirrored or filtered photos, and projected textures that hide shape errors. The rest come from perception (schema-driven seeing, adaptation to one's own work, idealisation, the other-race effect) and from priors that pull every fit toward the average. Each studio check (flip, squint, thumbnail, silhouette, overlay, blink, grayscale, inversion) defeats one of these mechanisms and has an exact computational counterpart. With no harvest or earlier draft, everything here is expert knowledge or pinhole arithmetic.
>
> Evidence status: 0 ✅ / 3 📄 / 44 🧠 / 17 ↔️ — verified 2026-11-20 (pass 1: 4 claims checked: 1 confirmed, 1 contested, 2 unconfirmed; pass 2: 2 claims checked: 1 corrected, 1 unconfirmed); remaining 🧠 items are queued for web verification.

## Key facts

**Why the errors happen**
- **Schema over observation.** People draw what they know, not what they see; drawing research blames misperception more than motor skill (Cohen & Bennett 1997; Ostrofsky, Kozbelt and colleagues on size constancy). Carbon & Wirth (*Perception*, 2014) report eyes placed systematically too high in drawn faces (effect size to verify) 🧠
- **Adaptation.** Minutes of looking at a face shift "normal" toward it (face aftereffects: Webster & MacLin 1999; Leopold et al. 2001), so after an hour the sculpt's own errors look right. Flipping, inverting, time away and fresh viewers reset this 🧠
- **Idealisation drift.** Unchecked sculpts slide toward an attractive average: bigger eyes, narrower straighter nose, fuller lips, slimmer jaw, perfect symmetry, younger skin. Together these make "a good-looking cousin". Caricature research runs the other way: exaggerating differences from the average aids recognition (Rhodes, Brennan & Carey 1987; Benson & Perrett 1991) 🧠 ↔️ (unmeasured for realistic 3D)
- **Other-race effect.** People discriminate less familiar groups' faces worse (Meissner & Brigham 2001), and most base meshes, canons and norms are European-derived. A template pulls nose width, lip volume, lid fold and canthal tilt toward itself 🧠
- **One photo is not the person.** Viewers sorting photos of two unfamiliar people typically produced several "identities" (Jenkins et al. 2011), and matching unfamiliar faces between good photos fails roughly 10–30% of the time (Bruce et al. 1999; Burton, White & McNeill 2010). Familiar viewers judge against many encounters, so a sculpt matched to one photo can fail against the rest 🧠
- **Coarse configuration carries identity.** Familiar faces survive very low resolution (Harmon 1973; Sinha et al. 2006); roughly 8–16 cycles per face width matter most (Costen, Parker & Craw 1996; Näsänen 1999). Brows and hair are strong cues (Sadr, Jarudi & Sinha 2003; Sinha & Poggio 1996): a bald, browless grey sculpt looks less like the sitter even when its geometry is right, so do not "correct" geometry to compensate 🧠

**The usual mistakes, by feature**
- **Eyes**, the most common critique 🧠
  - Globe too far forward, socket too shallow: from above, the corneal apex sits about 12–20 mm in front of the lateral orbital rim (Hertel range), and in profile behind the brow.
  - Aperture too open: at rest the upper lid covers 1–2 mm of iris (MRD1 ≈ 4–5 mm) and the lower lid meets the limbus. Sclera above the iris reads as a stare.
  - Lids too thin, no hooding or epicanthal fold, irises enlarged (iris diameter is nearly constant, ≈ 11.7 mm), and width, spacing and canthal tilt "normalised" toward the canon.
- **Nose.** Width errs both ways: too wide from close photos, too narrow from idealisation or a European template. Projection is too low when built from frontal photos only. Also: alar base too far forward, nostrils over-visible from the front, tip too pointed, real deviation erased by symmetry 🧠
- **Mouth.** Idealised volume (fuller lips, sharp vermilion border, equal upper and lower lip); corners placed under the pupils (they usually sit inside); a barrel too flat to wrap the dental arch, corners not tucked into the modiolus; a reference smile baked into the neutral 🧠
- **Ears.** Too high or low (usually unsolved pitch), too far forward, too upright, too flat to the head, too small, generic shape. Hidden in frontal selfies, they get placed by guess 🧠
- **Head and neck.** Cranium behind the ears too short; face too flat across, with side planes turning too late; jaw guessed under a beard; neck too thin and too vertical 🧠
- **Symmetry fails three ways:** mirroring erases identity-bearing asymmetry; yaw or roll in a photo is read as anatomy; a mirrored selfie puts real asymmetry on the wrong side 🧠
- **Drift of age, weight and expression** from references spanning years or smiling 🧠

**Camera and input mistakes**
- **Wrong distance or focal length.** Perspective depends only on distance. Tracing a 0.3–0.5 m phone photo as orthographic, or through Blender's default 50 mm camera at the wrong distance, makes the nose too big, the face too narrow and the ears too small. At close range the cheek silhouette also moves forward and swallows the ears, adding to point-depth magnification. This fits Ward et al. 2018 (nasal base about 30% wider at 12 in than at 5 ft, tip about 7%; modelled, and a later letter argues part of the effect is perceptual) 📄 [1][2]
- **Focal–depth trade-off.** Near frontal, a closer camera and a deeper face give nearly the same image, so a wrongly fixed focal length becomes a depth error that a frontal overlay cannot reveal 🧠
- **Unsolved pitch** is the main cause of wrong ear height and nose length (Table B). Camera below: ears look low, nose short and upturned. Camera above: ears high, nose long 🧠
- **Projected textures hide shape errors:** a photo texture looks right from its own camera 🧠
- **Lighting.** One-light shading cannot fix depth scale (bas-relief ambiguity, Belhumeur, Kriegman & Yuille 1999). Different light on sculpt and photo makes correct forms look wrong; flat matcaps hide plane errors 🧠

## Numbers & reference tables

**Table A — Proportion checks for common mistakes** (adults, neutral face; mostly European-derived norms; approximate)

| Check | Typical adult value | Flag when | Badge |
|---|---|---|---|
| Iris diameter (HVID) | 11.7 ± 0.5 mm | iris / en–ex outside 0.34–0.44 | 🧠 |
| Fissure length en–ex | 28–33 mm | en–ex / ex–ex outside 0.29–0.36 | 🧠 |
| Fissure height, primary gaze | 8–11 mm | sclera visible above iris | 🧠 |
| MRD1 (pupil centre to upper lid) | 3.5–5 mm (mean 3.5 in one adult sample of mean age 58, falling with age; 4.0–4.5 in a ptosis trial protocol) [3][4] | < 2.5 or > 6 mm without photo support | ↔️ 3.5–5 mm |
| Lower lid vs inferior limbus | 0–1 mm scleral show | > 1.5 mm | ↔️ age, ancestry |
| Intercanthal en–en | 28–35 mm; wider in East Asian and African-descent samples | en–en / en–ex outside 0.9–1.3 | 🧠 |
| Canthal tilt (ex above en) | about +2° to +8° | sign differs from photo | ↔️ |
| Cornea ahead of lateral orbital rim (Hertel) | 12–20 mm; L–R ≤ 2 mm | outside range | ↔️ higher in African-descent samples |
| Alar width al–al | 31–40 mm; often > 40 mm in African-descent samples | al–al / en–en outside 0.9–1.4 | ↔️ |
| Tip projection (Goode ratio) | 0.55–0.60 | < 0.5 | 🧠 |
| Nasolabial angle | M ≈ 90–105°, F ≈ 95–115° | > 15° off the profile photo | 🧠 |
| Mouth width ch–ch | 46–58 mm; ch–ch / IPD 0.78–0.90 (IPD 63 ± 3.5 mm) | ch–ch / IPD ≥ 1.0 at rest | 🧠 |
| Vermilion height upper / lower | ≈ 6–9 / 8–12 mm; lower ≈ 1.1–1.5 × upper | lower ≤ upper | ↔️ |
| Lips vs E-line (prn–pog′) | upper ≈ −4, lower ≈ −2 mm (± 2) | anterior to the line | ↔️ ancestry, age |
| Ear length / width | means ≈ 57–63 / 29–33 mm | adult length < 52 mm | 🧠 |
| Ear axis tilt from vertical | 10–30° (≈ 20°) | < 5° | 🧠 |
| Ear protrusion, helix to mastoid | ≈ 15–20 mm | < 10 mm | ↔️ |
| Ear height | top ≈ brow to upper-lid level; lobe ≈ subnasale; tragion ≈ orbitale level (Frankfort) | tragion > 8 mm off | 🧠 |
| Head length g–op / breadth eu–eu | 175–205 / 140–160 mm; cephalic index ≈ 75–85 | g–op short vs profile | ↔️ |
| Whole-face RMSD vs mirror | ≈ 0.8 mm (sourced in `anatomy/facial-asymmetry.md`) | < 0.3 mm: over-symmetrised | 🧠 |

**Table B — Apparent error from unsolved head pose** (shift = depth lever × sin θ; assumed levers: outer canthi→nose tip 35–50 mm, outer canthi→tragion 65–80 mm; cosine term < 1.6% at 10°)

| Unsolved error | What moves | 3° | 5° | 10° | Badge |
|---|---|---|---|---|---|
| Roll | eye-height difference across 63 mm IPD | 3.3 mm | 5.5 mm | 10.9 mm | 🧠 |
| Yaw | nose tip sideways vs canthal midpoint | 1.8–2.6 mm | 3.1–4.4 mm | 6.1–8.7 mm | 🧠 |
| Pitch | nose tip vertically vs eye line (nose ≈ 50 mm) | 1.8–2.6 mm | 3.1–4.4 mm | 6.1–8.7 mm | 🧠 |
| Pitch | ears vertically vs eye line | 3.4–4.2 mm | 5.7–7.0 mm | 11.3–13.9 mm | 🧠 |

So 3° of roll or 5° of yaw creates more apparent asymmetry than a normal face has, and 5° of pitch moves the ears by about 10% of IPD. For distance, see Table 1 of `community/reddit-face-from-photos.md`: nose-to-ear magnification 1.33–1.40 at 0.3 m, 1.10–1.12 at 1 m, 1.03–1.04 at 3 m.

**Table C — Diagnostics: what each defeats and how to run it**

| Trick | Reveals | Mechanism | Blender | Engine counterpart | Badge |
|---|---|---|---|---|---|
| Flip | tilts, lopsided features, asymmetry on the wrong side | resets adaptation | background image "Flip X" (named "Flip Horizontally" in 2.7x; corrected in verification) [5]; flip a viewport render (head Scale X = −1 is valid only near frontal) | mirror-asymmetry map vs photo-derived asymmetry; mirrored-photo test | 📄 |
| Squint / blur | masses, values, proportions | removes detail | blurred photo and render, Gaussian σ ≈ 3–5% of face width (< 4–6 cycles per face) | coarse-to-fine fit; low-pass residuals | 🧠 |
| Thumbnail | overall likeness | identity survives low resolution | side by side, face 48–64 px wide | configural Procrustes score | 🧠 |
| Silhouette / profile | nose projection, brow, lips, chin, occiput, neck | lighting-independent | Workbench: Lighting Flat, Color Single black, white background, solved profile camera | `fit_silhouettes` chamfer in % IOD | 🧠 |
| Overlay | feature position and size | direct comparison | camera background image, opacity 0.3–0.5, Depth Front [5] | residual arrows; per-view RMS | 📄 |
| Difference / edges | small offsets | cancels shared content | compositor Difference; edge images | edge chamfer | 🧠 |
| Blink | subtle size and position changes | motion detection (blink comparator) | toggle background image at 2–3 Hz via `bpy.app.timers` | photo/render GIF | 🧠 |
| Grayscale | plane and value errors | hue masks form | desaturated photo copy; Solid mode; AgX "Greyscale" look if present | luminance-only comparison | 🧠 time-sensitive |
| Upside-down | spacing as abstract shape | disrupts holistic processing (Yin 1969) | rotate render 180° | none | ↔️ hides feature errors (Thatcher illusion, Thompson 1980) |
| Turntable / held-out view | depth errors, overfitting | an unused view | cycle solved cameras; hold one photo back | leave-one-view-out reprojection | 🧠 |
| Caricature slider | over-average result | undoes prior shrinkage | shape key from template mean | S(α) = M + α(S − M), try α = 1.1–1.3 | ↔️ |
| Familiar viewer | overall likeness | unadapted, stored average | show the sitter both orientations (Mita, Dermer & Knight 1977) | none | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Audit references first.** Estimate distance d ≈ f_px · 63 mm / IPD_px and note yaw, pitch and roll per photo. Reject filtered or mirrored images (check a parting or mole), smiles (expression use only) and other years. Keep ≥ 2 photos the solver never sees.
2. **Never judge likeness through an unmatched camera.** Solve one perspective camera per photo (`to_blender_camera`). For free sculpting, set the viewport Focal Length to 85–100 mm (sidebar → View) or use orthographic for proportion checks.
3. **Turn the projected texture off for shape reviews,** and judge from cameras ≥ 20–30° away from the projecting photo.
4. **Check order per pass, big to small:** profile and 3/4 silhouettes → thumbnail → overlay in every solved camera → blink → Table A ratios → flip → grayscale under one area light at the photo's key direction → held-out photo → caricature slider → a familiar viewer. Fix the first failing level first.
5. **Eyes.** Place globe spheres (r ≈ 12 mm) before lids. From a top view, check the cornea against the lateral orbital rim. Match MRD1 and lower-lid level to the frontal photo and give lids real margin thickness.
6. **Nose.** Set projection and nasolabial angle in the profile camera before width. Take al–al only from photos shot from ≥ 1 m or from the multi-view solve. Keep real tip or septal deviation.
7. **Mouth.** Take width from the neutral frontal photo and check volume against the E-line in profile. In 3/4, the far half must foreshorten strongly; if it reads nearly as wide as the near half, the barrel is too flat.
8. **Ears.** Place them only after pitch is solved: anchor tragion to the Frankfort plane, tilt the axis back, check protrusion from front and top.
9. **Asymmetry.** Block in with symmetry, then turn it off. Re-add asymmetry only where ≥ 2 solved views agree, never from one tilted photo (Table B).

**What goes wrong**

| Symptom | Likely cause | Fix |
|---|---|---|
| Matches the photo camera, wrong elsewhere | texture projection; one-view overfit | texture off; held-out view; profile silhouette |
| Ears too high or low in every view | photos mostly from above or below | solve pitch; add a level profile |
| Stare, surprised look | sclera above iris; globe too proud | lower the upper lid; push the globe back |
| "Cousin, not the person" | symmetry, idealisation, prior shrinkage | symmetry off; caricature slider; compare many photos |
| Right in front, too broad in 3/4 | face too flat; side planes turn late | sculpt the front-to-side break; check top view |
| Older or younger than the sitter | mixed-year references; folds smoothed | one capture period; restore folds and hooding |

## Algorithmic implications

- **Likeness lint.** Compute every Table A metric on the fitted mesh. For each, store the model value, the photo-derived value with σ (from `triangulate_points` spread or reprojection) and a population z. Flag only unsupported deviations: |model − photo| > 2σ_photo, or |z| > 2.5 where photos cannot see. Never pull a photo-supported feature toward the mean.
- **Perspective-error signature.** With a wrong distance and compensating focal, a landmark's radial residual ≈ ρ_i·δ_i·(1/d − 1/d′), with ρ_i its image distance from the face centre and δ_i its relative depth. Regress radial residuals from `BundleResult.per_view_residuals` on ρ_i·δ_i. A slope implying > 5% magnification error means: free focal or request a distant photo.
- **Pose before features.** Give ear landmarks weight 0 when |yaw| < 30° or until pitch is constrained by ≥ 2 views. Then use ear priors: tragion height vs orbitale σ ≈ 4 mm, axis 20° ± 7°, length 60 ± 4 mm, protrusion 17 ± 4 mm. Flag "suspicious asymmetry" when a pair's left–right difference correlates with one view's roll or yaw.
- **Eye priors.** Globe radius 12 ± 0.5 mm; cornea 16 ± 2.5 mm ahead of the lateral rim; iris 11.7 ± 0.5 mm; MRD1 4.5 ± 1 mm. Add a hinge penalty on sclera above the iris unless ≥ 2 views show it.
- **Symmetry.** Keep `Priors.sigma_sym = 2.0` mm and `sigma_mid = 1.5` mm (engine defaults). Warn "over-symmetric" if mirror RMSD < 0.3 mm on a face whose photos show asymmetry.
- **Shrinkage detector.** For k whitened shape coefficients with prior N(0, I), real faces give ‖c‖² ≈ χ²_k (mean k, SD √(2k)). A fit with ‖c‖² < k − 2√(2k) is prior-dominated: warn "pulled toward average" and ask for views. With per-landmark priors use Mahalanobis D² over 3N dimensions. This is only meaningful once σ is calibrated on real faces; the scalar default `sigma = 8.0` mm is not.
- **Caricature slider.** Shape key S(α) = M + α(S − M) from the template mean, excluding scale and pose; default 1.0, range 0.8–1.4, stored in metadata.
- **Diagnostic renders per solved camera,** made numpy-side so they do not depend on the Blender version: overlay (α = 0.5), difference, Canny edges, silhouette chamfer (% IOD), flipped, blurred (σ = 3% of face width), 64 px thumbnail and grayscale pairs, a 3 Hz blink GIF, a residual-arrow plot and leave-one-view-out reprojection RMS.
- **Identity embeddings** (`reconstruction/identity-embeddings.md`) are a relative score on textured, matched-light renders only; untextured renders score low whatever their shape.

## Disagreements, myths & open questions

- ↔️ **When to turn symmetry off:** right after block-in, or only for finishing.
- ↔️ **Caricature in realistic 3D:** robust in 2D, but whether +10–30% helps or reads as cartoon is unmeasured.
- ↔️ **Inversion** helps judge spacing but hides local feature errors (Thatcher illusion); pair it with an upright check.
- ↔️ **Which orientation to show the sitter:** sitters prefer their mirror image, friends the true one (Mita et al. 1977).
- **Myth: "eyes are the likeness."** Brows, configuration, hair and head shape all carry identity 🧠
- **Myth: canons as checks.** Fifths, thirds and "mouth corners under the pupils" fail most measured faces (`community/art-anatomy-books.md`) 🧠
- **Myth: "the ear is parallel to the nose."** It is usually more upright (`anatomy/ear.md`) 🧠
- **Myth: an "ideal" 1:1.6 or 1:2 lip ratio.** These are aesthetic preferences, not norms ↔️
- **Myth: "long lenses flatten faces."** Distance does; focal length only crops 🧠
- **Open questions:** which errors most often break 3D likeness; how many millimetres per feature destroy recognition for familiar viewers; whether embedding scores track human likeness judgements of sculpts.

## Sources

No harvested sources or earlier draft existed for this topic; the numbered sources below were added in verification. Cross-referenced library notes: `anatomy/facial-asymmetry.md`, `anatomy/ear.md`, `anatomy/mouth-lips-teeth.md`, `community/reddit-face-from-photos.md`, `community/art-anatomy-books.md`, `community/instagram-social-sculptors.md`.

**Numbered sources**
1. Ward, Ward, Fried & Paskhover, "Nasal Distortion in Short-Distance Photographs: The Selfie Effect", JAMA Facial Plast Surg 2018 — https://pmc.ncbi.nlm.nih.gov/articles/PMC5876805
2. Rutgers news release on the selfie study — https://www.rutgers.edu/news/selfies-drive-self-image-and-may-lead-many-seek-plastic-surgery
3. Adult eyelid measurements (MRD1 mean 3.5 mm, PFH mean 8.7 mm) — https://pmc.ncbi.nlm.nih.gov/articles/PMC10371930
4. LEV102 blepharoptosis trial protocol (normal MRD1 4.0–4.5 mm, PFH 7–12 mm) — https://cdn.clinicaltrials.gov/large-docs/46/NCT05715346/Prot_000.pdf
5. Blender 5.3 Manual, Cameras (background images: Opacity, Depth, Flip X/Flip Y) — https://docs.blender.org/manual/en/latest/render/cameras.html

**Further reading (by name, not yet linked)**
- Farkas, *Anthropometry of the Head and Face*, 1994
- Cohen & Bennett, "Why can't most people draw what they see?", *JEP:HPP*, 1997; Ostrofsky, Kozbelt & Seidel on perceptual constancies and drawing skill, 2012
- Carbon & Wirth, *Perception*, 2014 (eye placement in drawn faces)
- Webster & MacLin, face aftereffects, 1999; Leopold, O'Toole, Vetter & Blanz, *Nature Neuroscience*, 2001
- Rhodes, Brennan & Carey, *Cognitive Psychology*, 1987; Benson & Perrett, photographic caricatures, 1991
- Meissner & Brigham, own-race bias meta-analysis, 2001
- Jenkins, White, Van Montfort & Burton, "Variability in photos of the same face", *Cognition*, 2011
- Bruce et al., 1999; Burton, White & McNeill, Glasgow Face Matching Test, 2010
- Harmon, "The recognition of faces", *Scientific American*, 1973; Sinha et al., "Face recognition by humans: nineteen results…", *Proc. IEEE*, 2006
- Costen, Parker & Craw, 1996; Näsänen, 1999 (spatial frequencies for face identification)
- Sadr, Jarudi & Sinha, "The role of eyebrows in face recognition", *Perception*, 2003; Sinha & Poggio, *Nature*, 1996
- Yin, "Looking at upside-down faces", 1969; Thompson, "Margaret Thatcher: a new illusion", *Perception*, 1980
- Mita, Dermer & Knight, *JPSP*, 1977
- Belhumeur, Kriegman & Yuille, "The bas-relief ambiguity", *IJCV*, 1999
- Ward et al., selfie nasal distortion, *JAMA Facial Plastic Surgery*, 2018
- Ricketts, the esthetic (E-) line, 1968; Goode, nasal tip projection ratio

## Verification log (2026-11-20)

- **Hertel 12–20 mm, L–R ≤ 2 mm, higher in African-descent samples; engine prior 16 ± 2.5:** unconfirmed (stays ↔️). Search summaries reported US Black-adult means of about 17.5–18.5 mm versus 15.4–16.5 mm in Caucasians, but West African (14.8–15.3 mm) and Ethiopian (about 15.7 mm) samples were lower, so "higher in African-descent" depends on the sample; no result was tied to a specific URL, and the 12–20 mm range and ≤ 2 mm asymmetry were not found. Lead: https://eyewiki.aao.org/Exophthalmometry
- **MRD1 4–5 mm, lid covers 1–2 mm iris, lower lid at limbus, PFH 8–11 mm, iris 11.7 ± 0.5:** contested for MRD1 and PFH. MRD1 3.5 mm mean (older adults) vs 4.0–4.5 mm; PFH mean 8.7 mm, range 7–12 mm. Other sub-claims unconfirmed. Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC10371930 ; https://cdn.clinicaltrials.gov/large-docs/46/NCT05715346/Prot_000.pdf
- **Ward et al. 2018, nasal base about 30% wider at 12 in vs 5 ft:** confirmed (📄); the tip is about 7% wider, and the authors model rather than measure. Sources: https://pmc.ncbi.nlm.nih.gov/articles/PMC5876805 ; https://www.rutgers.edu/news/selfies-drive-self-image-and-may-lead-many-seek-plastic-surgery
- **E-line −4/−2 mm, vermilion 6–9/8–12 mm, lip ratios:** unconfirmed. Summaries mention Ricketts' classic −4/−2 mm and population differences (a 2025 Angle Orthodontist article says the norms need updating), but not tied to specific URLs; no vermilion height or ratio data found.

## Verification log, pass 2 (2026-11-20)

- **Canthal tilt +2° to +8°; al–al 31–40 mm (European) and often > 40 mm (African-descent); al–al/en–en 0.9–1.4:** unconfirmed (badges unchanged). The search returned no canthal-tilt norms and no numeric al–al comparison; only an African American female nose study giving an alar width to intercanthal ratio of 5:4 and a Chinese sample exceeding North American Caucasian norms. Leads: https://pubmed.ncbi.nlm.nih.gov/12560683/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC9029890
- **Blender camera background images (Flip, Opacity, Depth Front):** corrected for the flip label. The current manual lists "Flip X" / "Flip Y" (older 2.79 used "Flip Horizontally"); Opacity and Depth (Back/Front) confirmed. Source: https://docs.blender.org/manual/en/latest/render/cameras.html
- **Viewport default focal length 50 mm, AgX "Greyscale" look, compositor Difference blend:** unconfirmed (the search returned nothing on these); the Grayscale row stays 🧠 time-sensitive.
