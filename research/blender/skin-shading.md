# Realistic skin shading in Blender

> Since Blender 4.0, skin is a Principled BSDF with Subsurface Weight 1, Base Color as the diffuse albedo, and a per-channel scattering Radius × Scale that is a real distance, so it only works on a head at metric scale [1]. Subsurface IOR, Subsurface Anisotropy (the manual quotes a measured skin value of 0.8) and Random Walk (Skin) are Cycles-only, and random walk scatters through the true mesh volume, so the fitted head must be watertight, non-overlapping and finely subdivided at render time [1][2][5]. Most fake-looking skin comes from four errors: scale (wax), uniform low roughness with glass IOR (plastic), lighting baked into photo albedo (painted), and over-scaled pore displacement (orange peel). The physical starting values come from expert knowledge and are queued for checking: Jensen et al. 2001 diffuse mean free paths of about 3.7–4.8 mm (red) to 0.7–1.1 mm (blue), skin IOR ≈ 1.4, regional roughness and micro-displacement amplitudes. EEVEE Next only approximates SSS, in screen space.
>
> Evidence status: 2 ✅ / 15 📄 / 42 🧠 / 19 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Principled BSDF inputs (manual and developer notes)**
- **Subsurface Radius** is the average distance light scatters below the surface, set per RGB channel so red can go deeper than blue [1] 📄. **Subsurface Scale** multiplies it; the UI slider runs 0–50 cm (taken from a snippet) [1] 📄. Radius × Scale is a world-space length, so a head in normalized units or with unapplied object scale gets the wrong translucency 🧠.
- **Subsurface Anisotropy:** 0 means light scatters equally in all directions. The manual says skin has been measured at **0.8** [1] 📄. Tissue optics puts the anisotropy factor g of epidermis and dermis at about 0.8–0.95 in visible light (van Gemert 1989; Tuchin) 🧠.
- **Subsurface IOR** is Cycles-only. It applies to rays entering the subsurface component and can differ from the main IOR; the manual suggests this to imitate skin layers [1] 📄.
- **Main IOR:** most materials lie between 1.0 and 4.0, and the default of 1.5 is glass [1] 📄. Graphics convention for skin is ≈1.4 (F0 ≈ 0.028; d'Eon & Luebke) 🧠. Tissue data go up to about 1.55 for the stratum corneum ↔️.
- **Thin-wall mode** turns off Radius, Scale and Method [1] 📄. The 5.2 release notes list Thin Wall as a new boolean Principled BSDF input, so it is a 5.2 feature [12]; it is in the current manual [1].
- **Specular Anisotropy** is Cycles-only [1] 📄. Skin highlights are not anisotropic at portrait scale, so keep it at 0 🧠.
- **Principled v2 (4.0+):**
  - The Subsurface Color input is gone; Base Color is the subsurface albedo.
  - Weight blends diffuse with SSS and should normally be 0 or 1.
  - Specular IOR Level 0.5 means "use the F0 from IOR" (0 removes reflection, 1 roughly doubles F0).
  - Specular Tint is a colour and must stay white for skin.
  🧠
- **4.x defaults:** Weight 0, Radius (1.0, 0.2, 0.1), Scale 0.05 m, Subsurface IOR 1.4, Anisotropy 0. That gives an effective red radius of 50 mm, about 10–15× too large for a real head 🧠.

**Methods**
- **Random Walk (Skin)** is Cycles-only and tuned for skin. A manual snippet says its radius is adjusted automatically from the colour texture [2] 📄. A forum post says it lacks the Burley-matching scaling of the legacy random walk [7] ↔️.
- **How it enters the surface:** it randomly picks Lambertian diffuse transmission or GGX refraction with roughness fixed at 1. The diffuse part is there because pure random walk sends light too deep into skin [5]. Users confirm that entry-roughness control is lost [10][6] ✅ (developer source plus independent user reports).
- **Random walk needs clean geometry.** It scatters through the real volume, so holes, open meshes and overlapping faces cause errors [2] 📄. Because it follows true geometry rather than interpolated normals, a coarse smooth-shaded mesh shows facets in the SSS. This is the likely cause of the "flat-shaded artifacts" in [8]; that thread's own diagnosis was not captured 🧠.
- **Christensen-Burley** is a surface diffusion profile. It is cheaper and less noisy, but ignores thickness and concavity, so ear and nostril translucency come out wrong; fine for mid-distance shots 🧠. Random walk is slower and noisier, more so at high anisotropy 🧠.
- **Names change between versions.** Blender 3.0 added a colour-adaptive "Random Walk" with IOR and anisotropy and kept the old one as "Random Walk (Fixed Radius)" 🧠. The 3.6 manual uses older socket names [4][11] 📄. A forum post claims 5.2 splits random walk into legacy and new variants [7] ↔️.

**Engines**
- Cycles-only inputs: Subsurface IOR, Subsurface Anisotropy, Specular Anisotropy and Random Walk (Skin) [1][2] 📄 (one publisher).
- **EEVEE Next (4.2+):** subsurface scattering is done in screen space from Radius × Scale. Transmission through thin parts comes from shadow-map thickness. Method, Subsurface IOR and Anisotropy are ignored. It breaks at silhouettes and when the radius is large on screen. The 4.2 notes support only part of this: a new SSS implementation with arbitrary radii and a Thickness output that drives translucency [13]; screen space, shadow-map thickness and ignored Method/IOR/Anisotropy were not found there 🧠.
- **Displacement:**
  - **Cycles:** true displacement (Material ▸ Settings ▸ Displacement and Bump) plus adaptive subdivision. Adaptive subdivision has historically sat behind the Experimental feature set; its 5.x status needs checking.
  - **EEVEE:** bump. EEVEE Next adds vertex displacement on existing geometry, without adaptive dicing.
  🧠

**Physical skin and resources**
- **Jensen et al. 2001** measured diffuse mean free paths (Table B). These became Blender Internal's old Skin1/Skin2 SSS presets. Only a handful of light-skinned subjects were measured 🧠.
- **Specular:** skin reflects like an untinted dielectric (sebum over stratum corneum). Weyrich et al. 2006, on roughly 150 faces, found specular strength and roughness vary by region, with the oily T-zone sharper and stronger. Fits favour two lobes, one sharp and one broad 🧠.
- **Albedo:** high in red, a haemoglobin dip near 540–580 nm, and melanin suppressing short wavelengths (Anderson & Parrish 1981). Linear albedo runs from about 0.55–0.65 in red for very light skin down to ≤0.05 in blue for very dark skin ↔️.
- **Microgeometry:**
  - Pores and furrows stretch along tension lines (Langer's lines), more with age (sizes in Table D) ↔️.
  - Eyelid skin is the thinnest on the face, well under 1 mm.
  - Ear helix and nasal alae are thin over cartilage and show the most translucency 🧠.
- **Texture resources** (licences and prices change) 🧠:
  - TexturingXYZ: multichannel face displacement (RGB = secondary, tertiary and micro bands) and full-head "VFace" UDIM sets.
  - 3D Scan Store (Ten24): scanned heads.
  - Wikihuman / Digital Emily (USC ICT): check the licence.
  - MPFB2 / MakeHuman: assets largely CC0.
  - Human Generator: commercial add-on.
  - MetaHuman: licence reportedly widened in 2025; verify.
  - For likeness, albedo should come from the subject's own cross-polarized photos. Vendor maps supply microdetail only.

## Numbers & reference tables

**A. Principled BSDF values**

| Parameter | Value | Units | Basis | Source | Status |
|---|---|---|---|---|---|
| Subsurface Anisotropy, skin | 0.8 | — | "measured" per manual; study untraced | [1] | 📄 |
| Subsurface Scale slider | 0–50 | cm | UI range (snippet) | [1] | 📄 |
| IOR span / default | 1.0–4.0 / 1.5 | — | doc | [1] | 📄 |
| Random Walk (Skin) entry roughness | 1 (fixed) | GGX | implementation | [5][6][10] | ✅ |
| 4.x defaults: Radius / Scale / Subsurface IOR | (1, 0.2, 0.1) / 0.05 / 1.4 | — / m / — | UI defaults | — | 🧠 |

**B. Skin optics**

| Quantity | R | G | B | Units | Population | Status |
|---|---|---|---|---|---|---|
| Diffuse mfp, skin1 (Jensen 2001) | 3.67 | 1.37 | 0.68 | mm | few subjects, light skin | 🧠 |
| Diffuse mfp, skin2 (Jensen 2001) | 4.82 | 1.69 | 1.09 | mm | as above | 🧠 |
| Ratio to red (skin1 / skin2) | 1 | 0.37 / 0.35 | 0.19 / 0.23 | — | derived | 🧠 |
| Anisotropy g | 0.8–0.95 | | | — | tissue optics, visible light | ↔️ |
| IOR → F0 = ((n−1)/(n+1))² | n 1.35–1.55 → 0.022–0.047; n 1.4 → 0.028 | | | — | convention vs tissue data | ↔️ |

**C. Starting values and priors, Cycles skin material (Blender ≥4.0, metre units)**

| Input | Start | Plausible range | Prior σ | Status |
|---|---|---|---|---|
| Subsurface Weight | 1.0 | 0.8–1.0 | fixed | ↔️ |
| Method | Random Walk (Skin) | Random Walk / Burley | — | 🧠 |
| Radius | (3.67, 1.37, 0.68) | ratios ±0.05 | — | 🧠 |
| Scale (red mfp = 3.7 mm) | 0.001 | 0.0004–0.0013 | log-normal σ_ln ≈ 0.35 | ↔️ |
| Subsurface Anisotropy | 0.8 | 0.7–0.9 | 0.05 | 📄 [1] |
| Subsurface IOR | 1.4 | 1.33–1.45 | 0.03 | 🧠 |
| IOR | 1.4 | 1.36–1.55 | 0.04 | ↔️ |
| Specular IOR Level | 0.5 | 0.4–0.6 | 0.05 | 🧠 |
| Roughness, base (Blender perceptual) | 0.45 | 0.35–0.60 | 0.07 | ↔️ |
| Roughness offset: nose / forehead / chin | −0.12 / −0.08 / −0.05 | ±0.05 | 0.04 | 🧠 |
| Roughness offset: cheeks, neck, ears | +0.05 | 0 to +0.1 | 0.04 | 🧠 |
| Roughness offset: lips (moist) | −0.12 | −0.2 to 0 | 0.06 | 🧠 |
| Coat weight / roughness (oily lobe) | 0.05 / 0.25 | 0–0.25 / 0.15–0.35 | — | 🧠 |
| Sheen weight (vellus hair) | 0.1 | 0–0.3 | — | 🧠 |
| Metallic / Specular Tint | 0 / white | fixed | — | 🧠 |

**D. Microdetail and texel density**

| Item | Value | Units | Basis | Status |
|---|---|---|---|---|
| Pore opening diameter | 0.05–0.25 (≤0.5 enlarged) | mm | dermatology / profilometry | ↔️ |
| Microrelief furrow depth | 0.02–0.1 | mm | replica profilometry | ↔️ |
| Wrinkle depth, fine → coarse | 0.1 → >1 | mm | as above | ↔️ |
| Facial epidermis thickness | 0.05–0.15 | mm | histology | 🧠 |
| Head + neck surface | ≈0.15–0.17 | m² | rule of nines: 9% of 1.7–1.9 m² | 🧠 |
| Texel pitch, 4K / 8K whole head, 70% UV fill | ≈0.12 / ≈0.06 | mm | arithmetic | 🧠 |
| Texel pitch, face on its own 8K UDIM (face ≈0.04 m²) | ≈0.03 | mm | arithmetic, face area assumed | 🧠 |
| Multires level for ≈0.1 mm edges, 16k-quad base | 5 (≈16 M quads) | — | 16k × 4⁵ | 🧠 |
| Render subdivision for facet-free SSS, 16k-quad base | ≥2 (≈0.8 mm edges) | — | edge ≲ ¼ red mfp | 🧠 |

**E. Scale sanity checks**

| Measure | Adult value | Units | Reference | Status |
|---|---|---|---|---|
| Interpupillary distance | mean ≈63, most 55–72 | mm | Dodgson 2004 | 🧠 |
| Head breadth (eu–eu) | ≈140–160 | mm | Farkas 1994 | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Scale gate.** Apply transforms and keep Unit Scale at 1.0. Measure IPD and head breadth (Table E). If either is off by more than about 10%, fix scale first; SSS tuning done at the wrong scale is wasted.
2. **Geometry gate** [2]:
   - Cap the neck and close the mouth bag and nostrils.
   - Select All by Trait ▸ Non Manifold must return nothing.
   - Keep eyes, teeth and tongue as separate closed objects that do not intersect the skin.
   - Add render subdivision until face edges are ≲1 mm [8].
   - Never enable thin-wall [1].
3. **Albedo from the consenting subject:**
   - Flat light, RAW files, a colour chart in frame, locked white balance and exposure.
   - Ideally cross-polarize: film on the lights and the camera polarizer at 90°. This removes specular. The parallel minus cross-polarized pair isolates specular as a roughness reference.
   - Project through the matched cameras (see `portrait-lighting-compare.md`) and blend by visibility × cos(view angle).
   - Divide out low-frequency shading. Shadows or highlights left in Base Color get shaded twice and read as "painted".
4. **Shader:** use Table C.
   - Base Color is sRGB. Roughness, normal and displacement maps are Non-Color; a roughness map loaded as sRGB is a classic silent error.
   - Redness comes from the radius ratios, not from a redder albedo.
5. **Microdetail:**
   - Wrinkles and creases go in displacement (Displacement and Bump, adaptive or high subdivision). Pores and microrelief go in bump or normal maps.
   - For a 0–1 vendor map: Midlevel 0.5, Scale = peak-to-peak height in metres (0.0002–0.0005 for pores). For a signed EXR: Midlevel 0.
   - Above about 1 mm on pores you get orange peel.
   - Vary by region: largest pores on the nose and medial cheeks, almost none on the eyelids, vertical striations on the lips.
6. **Lookdev under three camera-matched lights** (soft frontal, 45° key, backlight). Check:
   - a narrow warm band at the terminator;
   - ears and alae glowing under backlight only;
   - highlight size and shape on the nose tip, forehead and lower lip matching the photos.
   Use AgX (Standard clips skin highlights to yellow). Inspect pores at 100% crop, because denoisers smear them.
7. **What looks fake** 🧠:

| Symptom | Usual cause | Fix |
|---|---|---|
| Wax, jade, gummy | radius too large (scale mismatch, default Scale 0.05) | fix scale, red mfp ≈ 2–4 mm; do not drop Weight |
| Plastic | uniform roughness < 0.35, IOR 1.5, no cavity breakup | roughness map, IOR 1.4, rougher in pores and creases |
| Clay or dead | Weight 0, roughness > 0.65, desaturated albedo | Weight 1, regional roughness, chart-checked albedo |
| Sunburnt terminator | red radius ≫ G and B, saturated Base Color | ratios ≈ 1 : 0.37 : 0.19; desaturate |
| Painted | lighting or specular baked into albedo | cross-polarize, de-light |
| Orange peel | uniform, over-scaled pores | regional masks, ≤0.5 mm, follow skin flow |
| Faceted SSS | coarse mesh under random walk | subdivide [8] |
| Tinted highlights | Specular Tint not white, or Metallic > 0 | white, 0 |

## Algorithmic implications

- **Output contract for the fitting engine** (hard constraints, not penalties):
  - metres, with IPD (prior 63 mm, σ ≈ 3.5 mm) and head breadth checked against Table E;
  - watertight skin with no self-intersections;
  - separate closed eye, teeth and tongue shells;
  - a recommended render subdivision level chosen so edge length ≤ ¼ × red mfp.
- **Region masks live on the template.** Topology and UVs are fixed, so T-zone, cheek, lip, eyelid, ear and neck masks are authored once and transfer to every fitted head. Roughness offsets, pore density and SSS tweaks become per-region parameters with the σ values in Table C.
- **Distortion-aware microdetail.** Compute per-face area ratio against the template. Above about 25% stretch, warn, or rescale the displacement so pores keep their physical size (🧠 heuristic).
- **Versioned writer:**
  - look up sockets by identifier, with fallbacks [4][11];
  - read the `subsurface_method` enum items at runtime [7];
  - store Blender version and engine in each preset;
  - mark Cycles-only inputs inert for EEVEE.
- **Store the radius as physical mfp in mm.** Write Radius = mfp_mm and Scale = 0.001 / `unit_settings.scale_length`, so presets survive any scene unit scale.
- **Photometric losses must model SSS.** Skin shading is low-pass filtered over millimetres (red ≫ blue). A Lambertian shading term will sharpen or flatten geometry to explain the softness. Use low frequencies or the green and blue channels only, mask specular pixels (bright and desaturated), and prefer cross-polarized input 🧠.
- **Highlights constrain normals.** With an on-axis flash, highlight centres sit where the normal faces the camera. Each one is a cheap normal constraint (σ ≈ 5–10°, 🧠 heuristic).
- **Synthetic validation.** Render fitted heads with Random Walk (Skin) and randomized radius (log-normal), roughness (±σ) and lighting, to stress the landmark detectors.

## Disagreements, myths & open questions

- **Random Walk (Skin) radius:** colour-driven adjustment [2] versus missing Burley-matching scaling [7]. These may describe different things ↔️.
- **5.x method names:** the claimed legacy/new split in 5.2 [7] is unconfirmed. Harvest notes also mention "Random Walk (Fixed Radius)" (3.4) and "Random Walk (Legacy)" (a non-English 4.x page) ↔️.
- **Myth: "SSS Weight 0.1–0.3 is realistic."** This is a holdover from Principled v1 and from scenes at the wrong scale. In v2, Weight 1 with a correct radius is the physical setting ↔️ (practitioners still disagree).
- **Measured versus tuned radius:** Jensen's values can look slightly too translucent, and artists often end at 40–100% of them ↔️.
- **Roughness:** converting measured Beckmann m (about 0.25–0.45 by region) to Blender's √α gives about 0.5–0.67, above the typical artist range of 0.35–0.5. A second, sharp lobe closes part of the gap ↔️.
- **Main realism lever (anisotropy versus radius and colour):** practitioner opinion only [6][7]. The claim that random walk is slower and noisier "per the docs" was not located in the docs.
- **Open:**
  - EEVEE Next SSS internals in 5.x;
  - whether adaptive subdivision has left Experimental;
  - pore density by region;
  - painted regional SSS maps versus thickness taken from geometry;
  - peach fuzz as Sheen versus real hair curves.

## Sources

[1] Principled BSDF — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html — official-docs — 2026
[2] Principled BSDF — Blender 4.3 Manual — https://docs.blender.org/manual/en/4.3/render/shader_nodes/shader/principled.html — official-docs — 2024
[3] Subsurface Scattering — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/sss.html — official-docs — 2026 (harvested; no claim extracted)
[4] Subsurface Scattering — Blender 3.6 Manual — https://docs.blender.org/manual/en/3.6/render/shader_nodes/shader/sss.html — official-docs — 2023
[5] Cycles: Tweak Principled BSDF Subsurface parameters (PR #110989) — https://projects.blender.org/blender/blender/pulls/110989 — repo — 2023
[6] Subsurface Scattering colour — Blender Artists — https://blenderartists.org/t/subsurface-scattering-colour/1502627 — forum — unknown
[7] Principled BSDF: Subsurface Anisotropy — Blender Artists — https://blenderartists.org/t/principled-bsdf-subsurface-anisotropy/1629688 — forum — unknown
[8] Subsurface Scattering is producing flat-shaded artifacts — Blender Artists — https://blenderartists.org/t/subsurface-scattering-is-producing-flat-shaded-artifacts/1594573 — forum — unknown
[9] Volumetric SSS — Blender Tests — Blender Artists — https://blenderartists.org/t/volumetric-sss/1102733 — forum — unknown (no claim extracted)
[10] This material? How to — Blender Artists — https://blenderartists.org/t/this-material-how-to/1233888 — forum — unknown
[11] Principled BSDF — Blender 3.6 Manual — https://docs.blender.org/manual/en/3.6/render/shader_nodes/shader/principled.html — official-docs — 2023
[12] Rendering - Blender 5.2 Release Notes — https://developer.blender.org/docs/release_notes/5.2/rendering/ — official-docs — 2026
[13] EEVEE - Blender 4.2 LTS Release Notes — https://developer.blender.org/docs/release_notes/4.2/eevee/ — official-docs — 2024

**Further reading (by name, not yet linked)**
- Jensen, Marschner, Levoy & Hanrahan, "A Practical Model for Subsurface Light Transport", SIGGRAPH 2001
- Donner & Jensen, "Light Diffusion in Multi-Layered Translucent Materials", SIGGRAPH 2005; "A Spectral BSSRDF for Shading Human Skin", EGSR 2006
- Weyrich et al., "Analysis of Human Faces using a Measurement-Based Skin Reflectance Model", SIGGRAPH 2006
- d'Eon & Luebke, "Advanced Techniques for Realistic Real-Time Skin Rendering", GPU Gems 3, 2007
- Christensen & Burley, "Approximate Reflectance Profiles for Efficient Subsurface Scattering", Pixar technical memo, 2015
- Jimenez et al., "Separable Subsurface Scattering", Computer Graphics Forum, 2015
- Ma et al., "Rapid Acquisition of Specular and Diffuse Normal Maps from Polarized Spherical Gradient Illumination", EGSR 2007
- Graham et al., "Measurement-Based Synthesis of Facial Microgeometry", Eurographics 2013
- Nagano et al., "Skin Microstructure Deformation with Displacement Map Convolution", SIGGRAPH 2015
- Anderson & Parrish, "The Optics of Human Skin", Journal of Investigative Dermatology, 1981
- van Gemert et al., "Skin Optics", IEEE Transactions on Biomedical Engineering, 1989
- Tuchin, *Tissue Optics*
- Dodgson, "Variation and Extrema of Human Interpupillary Distance", SPIE 2004
- Farkas, *Anthropometry of the Head and Face*, 1994
- Blender 3.0, 4.0 and 4.2 release notes (Cycles subsurface, Principled v2, EEVEE Next)

## Verification log (2026-11-20)

- **Jensen 2001 skin1/skin2 mean free paths (3.67, 1.37, 0.68 / 4.82, 1.69, 1.09 mm):** unconfirmed. Search found the paper (https://www.cs.cornell.edu/~srm/publications/SG01-subsurf-abstract.html, https://formaurbis.stanford.edu/papers/bssrdf/bssrdf.pdf) but returned no table values. Badges left at 🧠.
- **Blender 4.x/5.x Principled defaults and Subsurface Method enum:** unconfirmed (no source page returned the default values). Enum: the Python API page (https://docs.blender.org/api/current/bpy.types.ShaderNodeBsdfPrincipled.html) was summarised as listing only BURLEY and RANDOM_WALK, which does not settle Random Walk (Skin); left as is.
- **5.2 legacy/new random-walk split:** unconfirmed; the 5.2 notes (https://developer.blender.org/docs/release_notes/5.2/cycles/) mention only negative subsurface anisotropy support. Left ↔️.
- **Thin Wall version:** confirmed new in 5.2, https://developer.blender.org/docs/release_notes/5.2/rendering/ [12]. Note text updated.
- **Skin IOR 1.4 / F0 0.028 vs ~1.55 stratum corneum:** unconfirmed as a specific source; searches gave soft tissue 1.38-1.41, stratum corneum about 1.467, dry about 1.55, but not tied to a single URL reliably. Left ↔️.
- **EEVEE Next SSS:** partly confirmed (new SSS, Thickness output) at https://developer.blender.org/docs/release_notes/4.2/eevee/ [13]; screen space, shadow-map thickness, ignored inputs, vertex-only displacement and adaptive subdivision status unconfirmed. Left 🧠.
