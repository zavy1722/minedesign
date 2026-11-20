# Modeling and shading realistic eyes in Blender

> A believable eye is a small optical system, not a textured ball. It has a ~24 mm globe, a steeper corneal cap (anterior radius ~7.8 mm) that stands ~2.5 mm proud of the limbus, a near-planar iris ~3 mm behind the corneal apex that is always seen through refraction, and wet adnexa (tear meniscus, caruncle, a ~2 mm lid margin, lashes) that hide the lid–globe seam. In Blender the robust build is an opaque sclera/iris/pupil mesh inside a transparent cornea shell (single-surface IOR ~1.336–1.376) whose shadow is switched off or rendered as shadow caustics. For photo→3D likeness, the visible iris/corneal diameter (~11.8 mm, SD ~0.5–0.8) is the best metric ruler on the face and a strong gaze cue. Globe size should almost never be fitted, because "big eyes" come from the lids. Globe and cornea geometry is sourced. Adnexa numbers and Blender settings are expert knowledge awaiting verification.
>
> Evidence status: 5 ✅ / 19 📄 / 65 🧠 / 9 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Sourced geometry**
- **Globe:** emmetropic adults on CT measure ~24.2 mm transverse × 23.7 mm vertical × 22.0–24.8 mm axial, with no significant sex or age difference. The transverse diameter ranges 21–27 mm. Refractive error mainly changes axial length [8][9]. 📄 ([8] and [9] are one study.)
- **The cornea is horizontally oval** from the front: ~11–12 mm H × 9–11 mm V. The pooled mean diameter is 11.84 mm (SD 0.79) [10]. 📄
- **Corneal radii:** anterior ~7.8 mm (7.79–7.87, SD ~0.27), posterior ~6.4–6.5 mm. Both surfaces are flatter horizontally, and posterior asphericity changes with age [13][14][15][16]. ✅ The consensus is firm, but which number belongs to which paper was summary-level in the harvest.
- **The limbus** (cornea→sclera transition) is ~1–2 mm wide [12]. 📄
- **CG build:** two spheres, "Sclera" plus a slightly larger "Cornea" [3][4]. ✅ Mask the iris and push it inward, clear the pupil toward the eye centre, and push the cornea out into a convex dome [4]. 📄 Sculpt fibres radiating from the pupil [4]. 📄 Use Sphere falloff, or two nested balls [1]. 📄
- **Without refraction the iris–cornea gap reads as empty space.** Use a glass cornea [3]. 📄 A Blender video treats cornea, iris, caruncle and tear line as separate parts [5]. 📄

**Expert knowledge**
- **Cornea:** central thickness is ~0.50–0.58 mm, rising to ~0.7 mm at the periphery. The anterior surface is prolate, with asphericity Q ≈ −0.25 (−0.1 to −0.4). 🧠
- **Indices** (Gullstrand/Le Grand): tear film ≈ aqueous ≈ vitreous 1.336, cornea 1.376, lens 1.386–1.406. The keratometric index 1.3375 gives whole-cornea power 337.5/R ≈ 43 D. 🧠
- **Anterior chamber depth** (epithelium→lens) is ~2.8–3.6 mm. The pupil margin rests on the lens, so the iris is near-planar, often *slightly convex forward*. A concave iris occurs (some myopes) but is atypical. 🧠
- **Iris:** the true diameter is ~12–13 mm, with the root hidden under the limbus. The stroma is 0.4–0.6 mm thick. The pupil is 2–4 mm in bright light and 4–8 mm in the dark, decentred ~0.1–0.4 mm nasally. The visible pupil is the *entrance* pupil, ~13 % larger and ~0.5 mm anterior to the real one. 🧠
- **Rotation centre:** ~13–14 mm behind the apex, ~1–1.5 mm behind mid-axial length. 🧠
- **Angle kappa/alpha ~+3–6°:** the pupillary axis points temporal to the line of sight. Eyes aimed exactly at a target therefore look faintly cross-eyed. 🧠
- **Placement:** the globe sits nearer the orbital roof and lateral wall. The corneal apex lies ~12–20 mm (typically 15–17 mm) ahead of the lateral orbital rim (Hertel), with L–R difference ≤ 2 mm. Norms vary by population. 🧠 ↔️
- **Lids in primary gaze:** the upper margin covers 1–2 mm of the superior limbus. The lower margin sits at, or up to ~1 mm below, the inferior limbus. MRD1 ≈ 4–5 mm and MRD2 ≈ 5 mm. The upper-lid peak lies slightly nasal to the pupil. 🧠
- **The lid margin is a 1.5–2 mm flat band.** Lashes sit at its anterior edge and the meibomian orifices behind them, while the posterior edge rides on the globe. Paper-thin lids are the commonest CG error. 🧠
- **Caruncle:** a pink, wet, ~3–5 mm nodule with fine hairs, in the lacrimal lake. The plica semilunaris fold lies lateral to it. The medial ~5–7 mm of each lid margin (the punctal part) has no lashes. 🧠
- **Tear meniscus:** the lower one is 0.2–0.5 mm high and forms the bright wet line in photos. 🧠
- **Lashes:** upper ~90–160 in 2–3 rows, 8–12 mm long; lower ~50–80 in 1–2 rows, 6–8 mm long. Base diameter is ~0.06–0.12 mm, tapering. They are longest in the central-to-lateral third, curve away from the eye, and clump. 🧠
- **The sclera is not white.** It is off-white under conjunctiva, with vessels denser toward the canthi and often a pinguecula in adults. The dark **limbal ring** fades with age. 🧠
- **Corneal Fresnel F0** is ≈ 2.1–2.5 % (n 1.336–1.376). The catchlight comes from the mirror-smooth tear film. 🧠
- **Cycles shadow rays stop at Glass/Transmission surfaces, so a refractive cornea darkens the iris.** Fixes:
  - Object › Visibility › Ray Visibility › Shadow off;
  - a Light Path *Is Shadow Ray* → Transparent mix;
  - MNEE shadow caustics (3.2+): cast on the cornea, receive on the iris/sclera, and enable on each light.

  🧠 (version-sensitive)
- **EEVEE refraction is approximate.** EEVEE Next (4.2+) uses *Raytraced Transmission* + Thickness, so iris parallax differs from Cycles. 🧠 (version-sensitive)
- **Lashes:** use hair *Curves* with the Geometry Nodes hair assets (Clump/Curl/Interpolate, 3.5+) and Principled Hair BSDF. 🧠 (version-sensitive)
- **Damped Track to a gaze target is a shortest-arc rotation from the primary position, which is Listing's law.** Track To with an up-axis adds false torsion at oblique gaze. 🧠

## Numbers & reference tables

**A. Globe and cornea (sourced)**

| Quantity | Value | Units | Population / basis | Src | Status |
|---|---|---|---|---|---|
| Globe transverse | 24.2 (21–27) | mm | healthy emmetropic adults, CT | [8][9] | 📄 |
| Globe vertical | 23.7 | mm | same | [8][9] | 📄 |
| Globe axial | 22.0–24.8 | mm | same | [8][9] | 📄 |
| Corneal diameter H × V | 11–12 × 9–11 | mm | review | [10] | 📄 |
| Corneal diameter, pooled | 11.84 ± 0.79 SD | mm | multi-study pool | [10] | 📄 |
| Anterior corneal radius | 7.79–7.87 (SD ~0.27) | mm | adults 18–65; 60–80 cohort (n=25) | [13][14][16] | ✅ |
| Posterior corneal radius | 6.40–6.53 (SD 0.25–0.31) | mm | adults; children 6–17: 6.42 (5.62–7.22) | [13][14][15][16] | ✅ |
| Limbus width | 1–2 | mm | review summary | [12] | 📄 |

**B. Anterior segment and optics (adults)**

| Quantity | Value | Units | Basis | Status |
|---|---|---|---|---|
| Central corneal thickness | 0.50–0.58 | mm | clinical norms | 🧠 |
| Anterior asphericity Q | −0.1 to −0.4 | — | clinical norms | 🧠 |
| Corneal sag, 11.7 mm chord | 2.64 (sphere) / 2.49 (Q −0.25) | mm | computed, R 7.8 | 🧠 |
| Anterior chamber depth | 2.8–3.6 | mm | shallower with age | 🧠 |
| Iris diameter / stroma | 12–13 / 0.4–0.6 | mm | — | 🧠 |
| Pupil diameter | 2–4 bright, 4–8 dark | mm | — | 🧠 |
| Entrance-pupil magnification | ~1.13 | × | schematic eye | 🧠 |
| Rotation centre behind apex | 13–14 | mm | — | 🧠 |
| Angle kappa/alpha | +3 to +6 | deg | — | 🧠 |
| IOR aqueous / cornea / lens | 1.336 / 1.376 / 1.386–1.406 | — | schematic eye | 🧠 |
| Keratometric index | 1.3375 | — | clinical convention | 🧠 |
| Fresnel F0, cornea | 0.021–0.025 | fraction | computed | 🧠 |

**C. Lids, adnexa, lashes, placement (adults)**

| Quantity | Value | Units | Status |
|---|---|---|---|
| Upper-lid cover of superior limbus | 1–2 | mm | 🧠 |
| Lower lid vs inferior limbus | 0–1 below | mm | 🧠 |
| MRD1 / MRD2 | 4–5 / ~5 | mm | 🧠 |
| Palpebral fissure length × height | 27–32 × 9–11 | mm | 🧠 ↔️ population |
| Lid margin thickness | 1.5–2 | mm | 🧠 |
| Lash-free medial margin | 5–7 | mm | 🧠 |
| Caruncle size | ~3–5 | mm | 🧠 |
| Lower tear meniscus height (OCT) | 0.2–0.5 | mm | 🧠 |
| Tear film thickness | ~3–10 | µm | ↔️ method |
| Upper lashes: count / length | 90–160 / 8–12 | n / mm | 🧠 |
| Lower lashes: count / length | 50–80 / 6–8 | n / mm | 🧠 |
| Lash base diameter | 0.06–0.12 | mm | 🧠 |
| Apex ahead of lateral rim (Hertel) | 12–20; L–R ≤ 2 | mm | 🧠 ↔️ ethnicity |
| Far interpupillary distance | ≈63 (SD ~3.5–4) | mm | 🧠 |

**D. Blender starting values (practice, not measurement)** 🧠

| Element | Starting setting |
|---|---|
| Scene | metres; eyeball ⌀ 0.024 |
| Cornea shell | Principled, Transmission 1, Roughness 0–0.02, IOR 1.336–1.3375 (↔️ vs 1.376) |
| Sclera | Base sRGB 0.80–0.90 (linear 0.60–0.79), faintly warm; Subsurface Weight 0.1–0.3, red-biased radius ~1 mm |
| Iris | photo/painted texture, Roughness 0.4–0.6, limbal darkening over outer 10–15 % of radius |
| Pupil | 1–2 mm deep near-black cavity, not a flat disc |
| Tear line | IOR 1.333, Roughness 0–0.05, shadow off, strip 0.3–1.0 mm |
| Lashes | Principled Hair BSDF, melanin 0.8–1.0 (dark), root radius 0.03–0.05 mm |
| Cycles | Transmission and Transparent bounces ≥ 8; Filter Glossy 0.5–1 |

## Applying this to photo→3D face sculpting in Blender

**Build, in order** 🧠
1. **Model at true scale in metres.** Point the sphere pole along the gaze axis so that rings stay concentric with the limbus. Use 32–48 segments plus Subdivision 1–2.
2. **Inner eye:**
   - A scleral ellipsoid with semi-axes ≈12.1 × 11.85 × 11.45 mm.
   - An iris disc, 12–13 mm wide, set ~0.5–1 mm behind the limbus plane (≈3 mm behind the apex).
   - A pupil extruded into a 1–2 mm dark tube.

   The tutorial concave dish [4] should be shallow or absent when you render real refraction. ↔️
3. **Cornea shell:**
   - Offset it +0.05–0.1 mm from the sclera.
   - Shape the cap to R 7.8 mm (Cast modifier, shape key or Sphere-falloff edit [1]), blended over 1–2 mm at the limbus [12].
   - An open shell behaves as a chamber filled with that IOR. ~1.336–1.3375 reproduces corneal power; 1.376 over-magnifies slightly.
4. **Fix the cornea's shadow** (see Key facts). Otherwise the iris renders dull.
5. **Lids:**
   - Model the full 1.5–2 mm margin, then turn 2–3 loops inward as conjunctiva.
   - Shrinkwrap (Nearest Surface Point, offset 0.1–0.3 mm) onto a proxy eye keeps the posterior margin seated and riding over the corneal bulge.
6. **Wet parts:** a tear-line strip in the lid–globe crease, a caruncle and plica, and (in EEVEE) a soft occlusion shell darkening the corners and the band under the upper lid.
7. **Lashes:**
   - Grow curves from the anterior margin, skipping the punctal part.
   - Clump and curl them, and vary length by ±20 %.
   - Lashes must never touch the cornea.
8. **Rig:** place a bone at the rotation centre (not the sphere centre) and Damped Track it to a target. Add ~4–5° temporal offset per eye to model kappa.

**Measure from each photo**
- **Limbus ellipse:** fit the medial and lateral arcs, because the lids hide the top and bottom. The minor/major ratio ≈ cos(gaze-to-camera angle). Refraction at the limbus is negligible. 🧠
- **Scale:** depth Z ≈ f_px × 11.8 mm / HVID_px. A SD of 0.5–0.8 mm gives ±4–7 % depth error [10]. 📄
- **Pupil:** the photo shows the entrance pupil. If you render refraction, model the true pupil as measured/1.13. 🧠
- **Lid coverage:** convert the upper-lid cover, lower-lid show, MRD1/2, canthi and tilt to mm using the HVID scale. 🧠
- **Catchlights:** they give the light direction and, with R 7.8, the corneal centre. Paint them out of any iris texture taken from photos. 🧠
- **Profile view:** check apex projection against the brow–cheek line and the Hertel prior, then lid thickness and lash angle. 🧠

**Failure modes** 🧠
- *Big or bug eyes* → the globe was scaled to the fissure or pushed forward.
- *Cross-eyed or wall-eyed* → no vergence to the camera and no kappa offset.
- *Sticker eyes* → no tear line, a thin lid margin, or lids intersecting the globe.
- *Doll eyes* → pure-white sclera without the lid/lash shadow band.
- *Dead iris* → the cornea is casting a shadow, or there is no limbal ring.
- *Swimming iris* → wrong chamber depth or IOR, or a deep concave iris *plus* refraction.
- *Fake lashes* → uniform comb, no clumps, no lower lashes, too thick.

## Algorithmic implications

**Eye sub-model:**
- Centre *c* is rigid in the head frame and shared across views.
- Gaze (yaw, pitch) is per view. Torsion follows Listing's law.
- Shape is per subject.
- Template warps move eyeballs **rigidly and never scale them**. Lid margins are re-projected onto the eye after every warp.

🧠

**Default geometry, from Tables A–B.** Put the apex at z = 0, with +z running backward.
- Cornea: a conic with R 7.8, Q −0.25, limbus radius 5.85, giving a sag of 2.49.
- Sclera: an ellipsoid with semi-axes 12.1 / 11.85 / 11.47, centred at z = 12.53. This gives an outer axial length of 24.0 and leaves the cornea ~1.1 mm proud of the ellipsoid.
- Iris: a plane at z ≈ 3.0–3.5.
- Rotation centre: z ≈ 13.3. The limbus-circle centre therefore sits ~10.7 mm in front of the rotation centre.

🧠 (arithmetic on sourced inputs)

**Priors**

| Parameter | μ | σ | Bounds | Basis |
|---|---|---|---|---|
| Globe transverse / vertical | 24.2 / 23.7 mm | 0.9 | 21–27 | [8] 📄 |
| Outer axial length (unobservable; fix it) | 24.0 mm | 1.0 | 21–30 | [8] 📄 |
| R anterior / posterior | 7.8 / 6.45 mm | 0.27 / 0.30 | 7.0–8.7 / 5.6–7.3 | ✅ |
| Q anterior | −0.25 | 0.12 | −0.6 to 0.1 | 🧠 |
| HVID | 11.8 mm | 0.6 | 10.5–13.0 | [10] 📄 |
| Corneal V diameter | HVID − 1.0 | 0.5 | 9–11 | [10] 📄 |
| Limbus centre → rotation centre | 10.7 mm | 0.6 | 9–12.5 | 🧠 |
| Iris plane behind limbus plane | 0.6 mm | 0.3 | 0–1.2 | 🧠 |
| True pupil (per view) | measured / 1.13 | — | 1.5–8.5 mm | 🧠 |
| Kappa (temporal) | 5° | 2° | 0–10° | 🧠 |
| L–R shape difference | 0 | 0.3 mm | — | 🧠 |
| Apex ahead of lateral orbital rim | 16 mm | 2.5 | 10–24 | 🧠 |
| Upper-lid cover / lower-lid show | 1.5 / 0.3 mm | 1.0 / 0.7 | — | 🧠 |
| Far IPD | 63 mm | 3.8 | 50–78 | 🧠 |

**Residuals and constraints**
- **Limbus:** use point-to-projected-circle distance on the medial and lateral arcs. MediaPipe's refined iris points (468–477; see `blender/blender-face-addons.md`) are only a low-weight initialiser.
- **Vergence:** each visual axis passes through that view's fixation point, by default the camera centre. Gaze is per view if the subject followed each camera.
- **Lids:** the posterior-margin signed distance to the eye surface (cornea included) must lie in [0, 0.3] mm. Enforce it as a hard projection. Lash roots need ≥ 0.2 mm clearance from the cornea.
- **Catchlight residual (optional):** reflection point = corneal centre + 7.8 mm × half-vector.
- **Refraction:** ignore it for the limbus. For the pupil, apply it, or use the 1.13× / 0.5 mm-forward shortcut.
- **Output:** closed objects Eye_L/R, Cornea_L/R, TearLine_L/R and Lashes (curves). Materials are written per Blender version, with sockets looked up by identifier (see `blender/skin-shading.md`).
- **Privacy:** an iris texture of the subject is a biometric identifier. Keep it local, opt-in and deletable, even with consent.

🧠

## Disagreements, myths & open questions

- **Iris shape:** tutorial concave dish [4][1] vs anatomy's near-planar or slightly convex iris. The dish fakes depth when there is no refraction. ↔️
- **Cornea IOR:** 1.376 (tissue) vs 1.336–1.3375 (single-surface effective) vs 1.4–1.5 "glass" presets [3]. ↔️
- **"Two-sided refraction" [3]** is not a Cycles option. It likely refers to EEVEE Legacy screen-space refraction or another renderer. ↔️
- **Myth: big-eyed people have big globes.** Globe width varies only ~±1 mm [8]. Aperture and lid position dominate, and myopia mostly lengthens the eye. 🧠
- **The "one eye-width between the eyes" canon** is a weak average. Never use it as a constraint. 🧠
- **Open questions:**
  - primary sources for caruncle size, lash counts and meniscus height;
  - Hertel and fissure norms by population;
  - whether Cycles 5.x has nested-dielectric priority (touching cornea/aqueous shells);
  - current MNEE limits and EEVEE Next option names;
  - measured sclera albedo;
  - licences of public eye-shape models (e.g., Bérard et al.).

## Sources

1. Blender 3D: Noob to Pro – Realistic Eyes In Blender (Wikibooks) — https://en.wikibooks.org/wiki/Blender_3D:_Noob_to_Pro/Realistic_Eyes_In_Blender — wiki tutorial — n.d.
2. Blender 3D: Noob to Pro – Procedural Eyeball (Wikibooks) — https://en.wikibooks.org/wiki/Blender_3D:_Noob_to_Pro/Procedural_Eyeball — wiki tutorial — n.d. (no claim used)
3. Sculpting the eye in Blender (BlenderNation) — https://www.blendernation.com/2023/05/18/sculpting-the-eye-in-blender/ — blog — 2023
4. How to sculpt convincing eyes in ZBrush (Creative Bloq) — https://creativebloq.com/how-to/sculpt-convincing-eyes-in-zbrush — blog — n.d.
5. How I make CG eyes in Blender (Class Central listing of a YouTube video) — https://classcentral.com/course/youtube-how-i-make-cg-eyes-in-blender-127450 — video listing — n.d.
6. Tutorial: Creating Realistic Digital Eyes 3.0 (ArtStation) — https://www.artstation.com/marketplace/p/GOVgy/tutorial-creating-a-realistic-eye — commercial — n.d. (no claim used)
7. Learning Blender – Creating an Eyeball (O'Reilly) — https://www.oreilly.com/library/view/learning-blender-a/9780133886283/ch07lev2sec6.html — textbook — 2013 (no claim used)
8. Variations in Eyeball Diameters of the Healthy Adults — https://pmc.ncbi.nlm.nih.gov/articles/PMC4238270/ — paper — 2014
9. Same study, PubMed record — https://pubmed.ncbi.nlm.nih.gov/25431659/ — paper — 2014
10. Mean human corneal diameter and palpebral fissure lengths as scales for forensic analysis of photographed faces — https://pmc.ncbi.nlm.nih.gov/articles/PMC13161299/ — review — n.d.
11. Evaluation of the relationship between corneal diameter and lens diameter — https://pubmed.ncbi.nlm.nih.gov/18299075 — paper — 2008 (no claim used)
12. Anatomy of cornea and ocular surface — https://pmc.ncbi.nlm.nih.gov/articles/PMC5819093/ — review — 2017
13. Radius and asphericity of the posterior corneal surface determined by corrected Scheimpflug photography — https://pubmed.ncbi.nlm.nih.gov/12190779/ — paper — 2002
14. Curvature analyses of the corneal front and back surface — https://pubmed.ncbi.nlm.nih.gov/23841132/ — paper — 2013
15. Radius of curvature of the posterior surface of the cornea — https://pubmed.ncbi.nlm.nih.gov/9293516/ — paper — 1997
16. The shape of the anterior and posterior surface of the aging human cornea — https://pubmed.ncbi.nlm.nih.gov/16266736/ — paper — 2005

**Further reading (by name, not yet linked)**
- Bérard et al. — "High-Quality Capture of Eyes" (SIGGRAPH Asia 2014); "Lightweight Eye Capture Using a Parametric Model" (SIGGRAPH 2016); "Practical Person-Specific Eye Rigging" (Eurographics 2019)
- Wood et al. — "Rendering of Eyes for Eye-Shape Registration and Gaze Estimation" (ICCV 2015); "A 3D Morphable Eye Region Model for Gaze Estimation" (ECCV 2016)
- Pamplona, Oliveira, Baranoski — "Photorealistic Models for Pupil Light Reflex and Iridal Pattern Deformation" (ACM TOG 2009)
- Lefohn et al. — "An Ocularist's Approach to Human Iris Synthesis" (IEEE CG&A 2003)
- Nishino & Nayar — "Eyes for Relighting" (SIGGRAPH 2004)
- Hanika, Droske, Fascione — "Manifold Next Event Estimation" (EGSR 2015)
- Atchison & Smith — *Optics of the Human Eye* (2000); Liou & Brennan — finite model eye (JOSA A 1997)
- *Wolff's Anatomy of the Eye and Orbit*; Snell & Lemp — *Clinical Anatomy of the Eye*
- Farkas — *Anthropometry of the Head and Face* (1994); Dodgson — "Variation and extrema of human interpupillary distance" (SPIE 2004)
- Peshek et al. — limbal ring and attractiveness (*Evolutionary Psychology* 2011)
- MediaPipe Iris (Google, 2020; Ablavatski et al.)
- Blender Manual: Principled BSDF, Light Paths, Visibility, Shadow Caustics; 3.2 and 3.5 release notes
