# Realistic skin shading in Blender

> Since Blender 4.0, skin is a Principled BSDF with Subsurface Weight 1, Base Color as the diffuse albedo, and a per-channel scattering Radius × Scale that is a real distance, so it only works on a head at metric scale [1]. Subsurface IOR, Subsurface Anisotropy (the manual quotes 0.8 as measured for skin) and the Random Walk (Skin) method are Cycles-only, and random walk scatters through the true mesh volume, so the fitted head must be watertight, non-overlapping and finely subdivided at render time [1][2][5]. Most fake-looking skin comes from four mistakes: wrong scale (wax), uniform low roughness with glass IOR (plastic), lighting baked into photo albedo (painted), and over-scaled pore displacement (orange peel). The physical starting values used here come from expert knowledge and are queued for checking: Jensen et al. 2001 diffuse mean free paths of roughly 3.7–4.8 mm (red) to 0.7–1.1 mm (blue), skin IOR ≈ 1.4, regional roughness, and micro-displacement amplitudes. EEVEE Next only approximates SSS, in screen space.
>
> Evidence status: 1 ✅ / 11 📄 / 33 🧠 / 11 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Principled BSDF inputs (manual and developer notes)**
- **Subsurface Radius** is the average distance light scatters below the surface, set per RGB channel so red can go deeper than blue [1] 📄. **Subsurface Scale** multiplies it. The UI slider runs 0–50 cm (taken from a search snippet) [1] 📄. Radius × Scale is a world-space length: a head scaled to normalized units gets the wrong translucency, and so does any object scale left unapplied 🧠.
- **Subsurface Anisotropy:** 0 means light scatters equally in all directions. The manual says skin has been measured at **0.8** [1] 📄. Tissue-optics literature puts the anisotropy factor g of epidermis and dermis at about 0.8–0.95 in visible light (van Gemert et al. 1989; Tuchin) 🧠.
- **Subsurface IOR** is Cycles-only. It applies to rays entering the subsurface component and can differ from the main IOR; the manual suggests this to imitate skin layers [1] 📄.
- **Main IOR:** most materials fall between 1.0 and 4.0. The default of 1.5 is glass [1] 📄. Graphics convention uses ≈1.4 for skin (F0 ≈ 0.028, as in d'Eon & Luebke, GPU Gems 3) 🧠. Tissue optics reports up to about 1.55 for the stratum corneum ↔️.
- **Thin-wall mode** turns off Radius, Scale and Method [1] 📄. It is in the current manual; the version that introduced it was not captured.
- **Specular Anisotropy** is Cycles-only [1] 📄. Skin highlights are not anisotropic at portrait scale, so keep it at 0 🧠.
- **Principled v2 (4.0+):** the Subsurface Color input is gone, so Base Color drives the subsurface albedo. Subsurface Weight blends diffuse with SSS and should normally be 0 or 1. Specular IOR Level 0.5 means "use the F0 from IOR" (0 removes reflection, 1 roughly doubles F0). Specular Tint is a colour and must stay white for skin 🧠.
- **4.x defaults:** Weight 0, Radius (1.0, 0.2, 0.1), Scale 0.05 m, Subsurface IOR 1.4, Anisotropy 0. That gives an effective red radius of 50 mm, roughly 10–15× too large for a real-scale head 🧠.

**Methods**
- **Random Walk (Skin)** is a Cycles-only method tuned for skin. A manual snippet says its radius is adjusted automatically from the colour texture [2] 📄. A forum post says it lacks the Burley-matching scaling of the legacy random walk [7] ↔️.
- **How it enters the surface:** at each entry it randomly picks Lambertian diffuse transmission or GGX refraction with roughness fixed at 1. Diffuse is mixed in because pure random walk sends light too deep into skin [5]. Users confirm that you lose control of the entry roughness [10][6] ✅ (developer source plus independent user reports).
- **Random walk needs clean geometry:** it scatters through the actual volume, so holes, open meshes and overlapping faces cause errors [2] 📄. It follows true geometry, not interpolated shading normals, so a coarse smooth-shaded mesh shows facets in the SSS. That is the likely cause of the reported "flat-shaded artifacts" [8], though the thread's own diagnosis was not captured 🧠.
- **Christensen-Burley** is a surface diffusion-profile approximation. It is cheaper and less noisy, but it ignores thickness and concavity, so ear and nostril translucency come out wrong. It is fine for mid-distance shots 🧠. Random walk is slower and noisier, more so at high anisotropy 🧠 (a forum attributes this to the docs; not located).
- **Names change between versions.** Blender 3.0 introduced a colour-adaptive "Random Walk" with IOR and anisotropy, and kept the old behaviour as "Random Walk (Fixed Radius)" 🧠. The 3.6 manual uses older socket names [4][11] 📄. A forum post claims 5.2 splits random walk into legacy and new variants [7] ↔️ (unconfirmed).

**Engines**
- Cycles-only inputs: Subsurface IOR, Subsurface Anisotropy, Specular Anisotropy and Random Walk (Skin) [1][2] 📄 (one publisher).
- **EEVEE Next (4.2+)** does subsurface scattering in screen space from Radius × Scale. It estimates transmission through thin parts from shadow-map thickness and ignores Method, Subsurface IOR and Anisotropy. It breaks at silhouettes and when the radius is large on screen 🧠.
- **Displacement:** Cycles has true displacement (Material ▸ Settings ▸ Displacement and Bump) plus adaptive subdivision, historically behind the Experimental feature set; its 5.x status needs checking. EEVEE uses bump, and EEVEE Next adds vertex displacement on existing geometry without adaptive dicing 🧠.

**Physical skin**
- **Measured scattering (Jensen et al. 2001):** diffuse mean free path (R, G, B) is about (3.67, 1.37, 0.68) mm for "skin1" and (4.82, 1.69, 1.09) mm for "skin2". These are the values behind Blender Internal's old Skin1/Skin2 SSS presets. The sample was a handful of subjects 🧠.
- **Specular:** skin reflects like an untinted dielectric (sebum on stratum corneum). Weyrich et al. 2006 measured roughly 150 faces and found specular strength and roughness vary by region; the oily T-zone (forehead, nose, chin) is sharper and stronger 🧠. Measured BRDF fits favour two lobes, one sharp and one broad 🧠.
- **Albedo:** reflectance is high in red, dips near 540–580 nm from haemoglobin, and is suppressed at short wavelengths by melanin (Anderson & Parrish 1981). Linear diffuse albedo ranges from about 0.55–0.65 in red for very light skin down to ≤0.05 in blue for very dark skin ↔️.
- **Microgeometry:** pore openings are about 0.05–0.25 mm (enlarged pores up to about 0.5 mm). Microrelief furrows are about 20–100 µm deep and wrinkles about 0.1 mm to over 1 mm. Pores and furrows stretch along tension lines (Langer's lines) and more so with age ↔️.
- **Thin regions:** eyelid skin is the thinnest on the face (well under 1 mm). Ear helix and nasal alae are thin over cartilage and show the most translucency 🧠.

**Texture resources (prices and licences change; check before use)** 🧠
- **Commercial scans:** TexturingXYZ sells multichannel face displacement maps (RGB = secondary, tertiary and micro bands) and full-head "VFace" UDIM sets. 3D Scan Store (Ten24) sells scanned heads with albedo and displacement.
- **Research and open data:** Wikihuman / Digital Emily (USC ICT); check the licence.
- **Open-source Blender tools:** the MPFB2/MakeHuman ecosystem (assets largely CC0).
- **Commercial Blender add-on:** Human Generator.
- **MetaHuman:** licence terms reportedly widened in 2025; check them.
- **Best albedo for a likeness:** the subject's own cross-polarized photos. Vendor maps are for microdetail, not identity.

## Numbers & reference tables

**A. Principled BSDF values (metre scene)**

| Parameter | Value | Units | Basis | Source | Status |
|---|---|---|---|---|---|
| Subsurface Anisotropy, skin | 0.8 | — | "measured" per manual; study untraced | [1] | 📄 |
| Subsurface Scale slider | 0–50 | cm | UI range (snippet) | [1] | 📄 |
| IOR typical span / default | 1.0–4.0 / 1.5 | — | doc | [1] | 📄 |
| Random Walk (Skin) entry roughness | 1 (fixed) | GGX | implementation | [5][6][10] | ✅ |
| 4.x defaults: Radius / Scale / SS-IOR | (1, 0.2, 0.1) / 0.05 / 1.4 | — / m / — | UI defaults | — | 🧠 |

**B. Skin optics**

| Quantity | R | G | B | Units | Population | Status |
|---|---|---|---|---|---|---|
| Diffuse mfp, skin1 (Jensen 2001) | 3.67 | 1.37 | 0.68 | mm | few subjects, light skin | 🧠 |
| Diffuse mfp, skin2 (Jensen 2001) | 4.82 | 1.69 | 1.09 | mm | as above | 🧠 |
| Ratio to red (skin1 / skin2) | 1 | 0.37 / 0.35 | 0.19 / 0.23 | — | derived | 🧠 |
| Anisotropy g | 0.8–0.95 | | | — | tissue optics, visible | ↔️ |
| Skin IOR → F0 = ((n−1)/(n+1))² | n 1.35–1.55 → F0 0.022–0.047; n 1.4 → 0.028 | | | — | convention vs tissue data | ↔️ |

**C. Starting values and priors for a Cycles skin material (Blender ≥4.0, metre units)**

| Input | Start | Plausible range | Prior σ | Status |
|---|---|---|---|---|
| Subsurface Weight | 1.0 | 0.8–1.0 | fixed | ↔️ |
| Method | Random Walk (Skin) | Random Walk / Burley | — | 🧠 |
| Radius | (3.67, 1.37, 0.68) | ratios ±0.05 | — | 🧠 |
| Scale (so red mfp = 3.7 mm) | 0.001 | 0.0004–0.0013 | log-normal, σ_ln ≈ 0.35 | ↔️ |
| Subsurface Anisotropy | 0.8 | 0.7–0.9 | 0.05 | 📄 [1] |
| Subsurface IOR | 1.4 | 1.33–1.45 | 0.03 | 🧠 |
| IOR | 1.4 | 1.36–1.55 | 0.04 | ↔️ |
| Specular IOR Level | 0.5 | 0.4–0.6 | 0.05 | 🧠 |
| Roughness, base (Blender perceptual) | 0.45 | 0.35–0.60 | 0.07 | ↔️ |
| Roughness offset: nose / forehead / chin | −0.12 / −0.08 / −0.05 | ±0.05 | 0.04 | 🧠 |
| Roughness offset: cheeks / neck / ears | +0.05 | 0 to +0.1 | 0.04 | 🧠 |
| Roughness offset: lips (moist) | −0.12 | −0.2 to 0 | 0.06 | 🧠 |
| Coat weight / roughness (oily second lobe) | 0.05 / 0.25 | 0–0.25 / 0.15–0.35 | — | 🧠 |
| Sheen weight (vellus hair) | 0.1 | 0–0.3 | — | 🧠 |
| Metallic / Specular Tint | 0 / white | fixed | — | 🧠 |

**D. Microdetail and texel density**

| Item | Value | Units | Basis | Status |
|---|---|---|---|---|
| Pore opening diameter | 0.05–0.25 (≤0.5 enlarged) | mm | dermatology / profilometry | ↔️ |
| Microrelief furrow depth | 0.02–0.1 | mm | replica profilometry | ↔️ |
| Wrinkle depth, fine → coarse | 0.1 → >1 | mm | as above | ↔️ |
| Facial epidermis thickness | 0.05–0.15 | mm | histology | 🧠 |
| Head + neck surface | ≈0.15–0.17 | m² | rule of nines, 9% of 1.7–1.9 m² | 🧠 |
| Texel pitch: 4K / 8K whole head, 70% UV fill | ≈0.12 / ≈0.06 | mm | arithmetic | 🧠 |
| Texel pitch: face on own 8K UDIM (face ≈0.04 m²) | ≈0.03 | mm | arithmetic, face area assumed | 🧠 |
| Multires level for ≈0.1 mm edges, 16k-quad base | 5 (≈16 M quads) | — | 16k × 4⁵ | 🧠 |
| Render subdivision for facet-free SSS, 16k base | ≥2 (≈0.8 mm edges) | — | edge ≲ ¼ red mfp | 🧠 |

**E. Scale sanity checks for the fitted head**

| Measure | Adult value | Units | Source | Status |
|---|---|---|---|---|
| Interpupillary distance | mean ≈63, most 55–72 | mm | Dodgson 2004 | 🧠 |
| Head breadth (eu–eu) | ≈140–160 | mm | Farkas 1994 | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Scale gate.** Apply all transforms and keep Unit Scale at 1.0. Measure IPD and head breadth in the viewport (Table E). If they are off by more than about 10%, fix scale before touching the shader; any SSS tuning done at the wrong scale is wasted.
2. **Geometry gate** [2]:
   - Cap the neck and close the mouth bag and nostrils.
   - Select ▸ Select All by Trait ▸ Non Manifold must return nothing.
   - Keep eyes, teeth and tongue as separate closed objects that do not intersect the skin.
   - Add render-level subdivision so face edges are ≲1 mm. This removes the SSS faceting [8].
   - Never enable thin-wall on the head [1].
3. **Albedo capture from the consenting subject:**
   - Flat, diffuse light; RAW files; a colour chart in frame; locked white balance and exposure.
   - Ideally cross-polarize: linear film on the lights, camera polarizer at 90°. This strips the specular, so what remains is close to diffuse albedo. A parallel-polarized pair minus the cross-polarized one isolates specular for a roughness and specular reference.
   - Project the photos through the matched cameras (see `portrait-lighting-compare.md`) and blend by visibility and cos(view angle).
   - De-light residual shading by dividing out a low-frequency shading estimate. Any shadow or highlight left in Base Color is shaded a second time and reads as "painted".
4. **Shader (Cycles):** use Table C. Base Color sRGB; Roughness, Normal and Displacement maps Non-Color (a roughness map loaded as sRGB is a classic silent error). Leave the radius alone in Base Color: tint comes from colour, depth from Radius.
5. **Microdetail:**
   - Secondary forms (wrinkles, creases) go in displacement with Displacement and Bump mode and adaptive or high subdivision. Pores and microrelief go in bump or normal maps.
   - For a 0–1 vendor map, set Displacement node Midlevel 0.5 and Scale equal to the peak-to-peak height in metres (0.0002–0.0005 for pores and microrelief).
   - For a signed 32-bit EXR, Midlevel 0.
   - Above about 1 mm peak-to-peak on pores you get orange peel.
   - Vary pore size by region: largest on the nose and medial cheeks, almost none on the eyelids, vertical striations on the lips.
6. **Lookdev under three lights, camera-matched to the subject's photos:** soft frontal, 45° key, and a rim or backlight. Check:
   - the shadow terminator shows a narrow warm (red-orange) band;
   - ears and alae glow a little under backlight but not under frontal light;
   - highlight size and shape on the nose tip, forehead and lower lip match the photos.
   Use the AgX view transform; Standard clips skin highlights to yellow. Keep denoising albedo and normal passes on, and check pores at 100% crop, because denoisers smear them.
7. **What looks fake (diagnosis)** 🧠:

| Symptom | Usual cause | Fix |
|---|---|---|
| Wax, jade, gummy | radius too large (scale mismatch, 4.x default Scale 0.05) | fix scale, red mfp ≈ 2–4 mm; do not drop Weight |
| Plastic | uniform roughness < 0.35, IOR 1.5, no cavity breakup | roughness map, IOR 1.4, raise roughness in pores and creases |
| Clay or dead | Weight 0, roughness > 0.65, desaturated albedo | Weight 1, regional roughness, check albedo against chart |
| Sunburnt, orange terminator | red radius ≫ G/B or saturated Base Color | ratios near 1 : 0.37 : 0.19; desaturate albedo |
| Painted | lighting or specular baked into albedo | cross-polarized capture, de-lighting |
| Orange peel or reptile | uniform, over-scaled pore displacement | regional masks, ≤0.5 mm amplitude, follow skin flow |
| Faceted SSS | low render subdivision under random walk | subdivide [8] |
| Tinted highlights | Specular Tint not white, or Metallic > 0 | white, 0 |

## Algorithmic implications

- **Output contract for the fitting engine** (hard constraints, not penalties):
  - metric units (metres), with IPD and head-breadth checks against Table E (IPD prior mean 63 mm, σ ≈ 3.5 mm);
  - watertight skin with no self-intersections;
  - separate closed eye, teeth and tongue shells;
  - a recommended render subdivision level, computed so that edge length ≤ ¼ × red mfp.
- **Region masks live on the template.** The template has fixed topology and UVs, so T-zone, cheek, lip, eyelid, ear and neck masks are authored once (vertex groups or a UV mask) and carry over to every fitted head for free. Roughness offsets, pore density and SSS tweaks are then per-region parameters (Table C σ values).
- **Distortion-aware microdetail:** compute per-face area ratio against the template. Where stretch exceeds about 25%, warn, or re-tile or rescale the displacement so pores keep their physical size (🧠 threshold heuristic).
- **Versioned material writer:**
  - read `bpy.app.version` and look sockets up by identifier with fallbacks [4][11];
  - read the `subsurface_method` enum items at runtime instead of hard-coding them [7];
  - store Blender version and engine in each preset;
  - flag Cycles-only inputs as inert when the target is EEVEE.
- **Store radius as physical mfp in mm, plus ratios.** Write Radius = mfp_mm and Scale = 0.001 / `unit_settings.scale_length`. That keeps presets independent of the scene's unit scale.
- **Photometric losses must model SSS.** Skin shading is low-pass filtered over a few millimetres (red ≫ blue). A Lambertian shape-from-shading term will sharpen or flatten geometry to explain the softness. Restrict shading terms to low frequencies or use the blue or green channel; mask specular pixels (bright, desaturated); prefer cross-polarized captures 🧠.
- **Specular highlights constrain normals.** With an on-axis flash, highlight centres sit where the surface normal points back at the camera. Each highlight is a cheap normal constraint at that pixel (σ about 5–10°, 🧠 heuristic).
- **Synthetic validation:** render fitted heads in Cycles with Random Walk (Skin) while randomizing radius (log-normal), roughness (±σ) and lighting, to test landmark-detector robustness against the photographic domain.

## Disagreements, myths & open questions

- **What Random Walk (Skin) does to the radius:** colour-driven adjustment [2] versus missing Burley-matching scale [7]. These may describe different things ↔️.
- **Blender 5.x method names:** the claimed legacy/new split in 5.2 [7] is unconfirmed. Harvest notes also mention "Random Walk (Fixed Radius)" in a 3.4 manual page and "Random Walk (Legacy)" in a non-English 4.x page ↔️.
- **Myth: "SSS weight 0.1–0.3 is realistic."** This is a carry-over from Principled v1, where Subsurface mixed in a separate Subsurface Color, and from wrong scale. In v2, Weight 1 with a correct radius is physical. Practitioners still disagree ↔️.
- **Myth: "Subsurface colour should be red."** In v2, redness at the terminator comes from the R > G > B radius ratio, not from a redder albedo 🧠.
- **Measured versus tuned radius:** Jensen's values often look slightly too translucent in practice, and artists end at 40–100% of them ↔️.
- **Skin IOR** 1.4 versus up to 1.55; F0 0.028 versus 0.047 ↔️.
- **Roughness:** converting measured Beckmann m (about 0.25–0.45 by region) to Blender's perceptual roughness (√α) gives about 0.5–0.67, above typical artist values of 0.35–0.5. The gap is partly closed by the second, sharper lobe ↔️.
- **Anisotropy versus radius and colour as the main realism lever** is practitioner opinion [6][7].
- **Unconfirmed:** that random walk costs more time and noise in dense media "per the docs".
- **Open:** EEVEE Next SSS internals in 5.x; whether adaptive subdivision has left Experimental; pore density by region; regional SSS maps versus geometry-driven thickness; peach fuzz as Sheen versus real curves.

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

**Further reading (by name, not yet linked)**
- Jensen, Marschner, Levoy & Hanrahan, "A Practical Model for Subsurface Light Transport", SIGGRAPH 2001
- Donner & Jensen, "Light Diffusion in Multi-Layered Translucent Materials", SIGGRAPH 2005; "A Spectral BSSRDF for Shading Human Skin", EGSR 2006
- Weyrich et al., "Analysis of Human Faces using a Measurement-Based Skin Reflectance Model", SIGGRAPH 2006
- d'Eon & Luebke, "Advanced Techniques for Realistic Real-Time Skin Rendering", GPU Gems 3, 2007
- Christensen & Burley, "Approximate Reflectance Profiles for Efficient Subsurface Scattering", Pixar technical memo, 2015
- Jimenez et al., "Separable Subsurface Scattering", Computer Graphics Forum, 2015
- Burley, "Physically-Based Shading at Disney", SIGGRAPH 2012 course notes
- Debevec et al., "Acquiring the Reflectance Field of a Human Face", SIGGRAPH 2000
- Ma et al., "Rapid Acquisition of Specular and Diffuse Normal Maps from Polarized Spherical Gradient Illumination", EGSR 2007
- Graham et al., "Measurement-Based Synthesis of Facial Microgeometry", Eurographics 2013
- Nagano et al., "Skin Microstructure Deformation with Displacement Map Convolution", SIGGRAPH 2015
- Igarashi, Nishino & Nayar, "The Appearance of Human Skin: A Survey", Foundations and Trends in Computer Graphics and Vision, 2007
- Anderson & Parrish, "The Optics of Human Skin", Journal of Investigative Dermatology, 1981
- van Gemert et al., "Skin Optics", IEEE Transactions on Biomedical Engineering, 1989
- Tuchin, *Tissue Optics*
- Dodgson, "Variation and Extrema of Human Interpupillary Distance", SPIE 2004
- Farkas, *Anthropometry of the Head and Face*, 1994
- Blender 3.0, 4.0 and 4.2 release notes (Cycles subsurface, Principled v2, EEVEE Next)
