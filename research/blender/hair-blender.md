# Hair in Blender for head reconstructions

> Hair hides the cranium and moves between shots, yet the hairline, parting, brows and lashes carry much of recognition. Since 3.3 Blender's tool is the *Curves* object: strands rooted on a surface mesh through its UV map and combed in Curves Sculpt mode. Since 3.5 they are shaped by bundled geometry-nodes hair assets and shaded with the Principled Hair BSDF (Chiang model, plus Huang from 4.0). For a photo→head tool the robust split is to fit skin and skull *under* the hair from priors, take only the envelope, hairline, parting, whorl and flow from the photos, and grow guides procedurally for the artist to comb; strand-accurate capture from photos is still research code, mostly under non-commercial licences. No harvest or earlier draft existed for this topic, so everything is expert knowledge awaiting verification. Version-specific API names were written against 3.3–4.x and are the riskiest items for 5.2 LTS and 5.3.
>
> Evidence status: 0 ✅ / 3 📄 / 91 🧠 / 30 ↔️ — 🧠 items remain unverified.

## Key facts

**Curves hair system (3.3+)**
- **Data model.** A `Curves` ID (`bpy.data.hair_curves`) stores everything as attributes: `position` and `radius` on points; `curve_type`, `resolution` and `surface_uv_coordinate` (float2) on curves. The object holds `surface` (a mesh object) and `surface_uv_map` (a name) [1][3]. The UV attribute is named `surface_uv_coordinate` in the manual but `surface_uv_coords` in the developer docs, so probe the name at runtime. ↔️
- **Roots attach by UV.** The hair region needs **non-overlapping, non-mirrored UVs**. Many head templates mirror their UVs, so add a dedicated "HairUV" map. 🧠
- **Deformation.** *Deform Curves on Surface* (in the modifier Add ▸ Curve ▸ Empty Hair creates) carries roots through shape keys and armatures. It needs the surface's **Add Rest Position** (`Object.add_rest_position_attribute`). Remeshing or re-UVing breaks attachment; re-snap with `curves.snap_curves_to_surface` (Nearest / Deform) 📄 [1]. `curves.surface_set` binds and parents. 🧠
- **Curves Sculpt brushes:** Selection Paint, Add, Delete, Density, Comb, Snake Hook, Grow/Shrink, Pinch, Puff, Smooth and Slide. Add interpolates length, shape and point count from neighbours, and X-symmetry exists. Brushes edit the *original* curves (the guides); children appear only in the evaluated result. 🧠
- **Edit mode** began as selection only and gained transform, duplicate, extrude, subdivide and draw tools across 4.x. The per-version list is unverified. 🧠
- **Legacy particle hair** survived through 4.x. `curves.convert_from_particle_system` / `convert_to_particle_system` convert either way. Its 5.x status is unverified. 🧠 ↔️
- **Python.** 4.x has `Curves.add_curves(sizes)` 📄 [2], `remove_curves`, `resize_curves`, `set_types` and bulk attribute access; the exact versions are unverified. In 3.x the dependable route is a polyline mesh → *Mesh to Curve* nodes → convert. Probe with `hasattr`. 🧠

**Geometry-nodes hair assets (Essentials library, 3.5+)**
- **About two dozen node groups.**
  - Deformation: Clump, Curl, Frizz, Noise, Roll, Rotate, Shrinkwrap, Smooth, Straighten, Trim, Displace.
  - Generation: Generate, Interpolate, Duplicate.
  - Guides: Create Guide Index Map.
  - Utility: Attach to Surface, Redistribute Points, Restore Segment Length, Set Hair Curve Profile, Braid, Blend, Curve Info/Root/Segment.

  Add ▸ Curve ▸ Fur and Quick Fur build stacks from them. 🧠 (names version-sensitive)
- **Canonical stack:**
  1. combed guides;
  2. Interpolate, with *Part by Mesh Islands* so children never cross a parting;
  3. Clump, using the Guide Index Map;
  4. Curl / Frizz / Noise;
  5. Trim;
  6. Shrinkwrap, which keeps strands out of the head and ears;
  7. Restore Segment Length;
  8. Set Hair Curve Profile.

  Clump before curling, or the curls de-correlate. 🧠

**Shading and rendering**
- **Principled Hair BSDF.** It uses the Chiang et al. 2016 model in Cycles and EEVEE. From 4.0 it adds the Huang et al. 2022 microfacet model, with an elliptical cross-section (*Aspect Ratio*, defined as minor/major axis; the manual recommends 0.8–1 Asian, 0.65–0.9 Caucasian, 0.5–0.65 African) [4] and per-lobe weights; Huang is Cycles-only. 🧠 ↔️
- **Parametrize by Melanin + Melanin Redness** (0 = eumelanin, 1 = pheomelanin; eumelanin = Melanin×(1−Redness), pheomelanin = Melanin×Redness) 📄 [4], not Direct Coloring, so colour stays coupled to scattering depth.
- **Lobes.** Keratin IOR is ≈1.55. Cuticle tilt (≈2–3°, the *Offset* input) shifts the white primary highlight (R) toward the root and the coloured secondary (TRT) toward the tip (Marschner et al. 2003). 🧠
- **Bounces.** Blond colour comes from multiple scattering, so light hair needs far more bounces than black, or it renders dark and grey. 🧠
- **Per-strand inputs.** Hair Info gives Intercept (0 at the root, 1 at the tip), Length, Thickness and Random. The Attribute node reads per-curve masks such as grey strands. 🧠
- **Cycles curve shapes.** *Rounded Ribbons* are camera-facing and cheap. *3D Curves* are true tubes, needed for lashes and close-ups. EEVEE strands alias, so raise samples. 🧠
- **Real-time hair means cards.** Cards are alpha strips carrying root–tip, ID, depth, flow (tangent) and AO maps baked from strands. In EEVEE 4.2+ the Dithered / Blended render method replaces the legacy blend modes. 🧠
- **Export.** glTF and FBX carry no curves, so real-time export means cards. Strands reach Unreal grooms via Alembic (attribute conventions unverified). 🧠
- **Commercial add-on.** *Hair Tool* (B. Styperek) converts curves to cards; check its price and licence. 🧠

**Anatomy that drives the groom**
- **Scalp hair.** There are ~100k–150k hairs in follicular units of 1–4. Shafts are 50–120 µm, roundest and thickest in East Asian hair and flattest in African hair (Table A). 🧠 ↔️
- **Emergence and flow.** Hairs leave the scalp at an acute angle, flattest at the hairline, temples and nape. Flow radiates from one crown whorl (sometimes two) behind the vertex. 🧠
- **The frontal hairline is a 3–10 mm transition zone** of single, finer, sparser hairs and vellus. A hard edge is the commonest "wig" tell. 🧠
- **Brows are direction-zoned.** They sit on mobile skin over the supraorbital rim. *Head* hairs point up; *body* hairs run laterally in upper and lower rows that meet on a herringbone ridge; *tail* hairs run lateral-down. All lie 5–20° from the skin. 🧠
- **Lashes.** Counts and lengths are as in `blender/eyes-modeling-blender.md`. Upper lashes curve up and out, lower lashes down and out. They clump 3–6 at the tips, are longest laterally, and are absent over the medial 5–7 mm. East Asian lashes are thicker, sparser and straighter (Na et al. 2006). 🧠 ↔️
- **Hair does heavy recognition work** (Sinha & Poggio 1996). A correct face under the wrong hairline or parting reads as someone else. 🧠

## Numbers & reference tables

**A. Scalp hair, adults** (recalled ranges from dermatology/trichology)

| Quantity | Typical | Range | Units | Population / note | Badge |
|---|---|---|---|---|---|
| Total scalp hairs | 100k–120k | 80k–150k | hairs | blond > brown/black > red | 🧠 ↔️ |
| Density, non-balding | ~200 | 120–300 | hairs/cm² | European high; East Asian, African lower; studies report 190 (African) vs 227 (Caucasian) [5] and median 330, range 113–660 in Nigeria [5] | ↔️ |
| Hairs per follicular unit | 2–2.5 | 1–4 | hairs | singles at hairline | 🧠 |
| Shaft diameter | 70–80 | 50–120 | µm | East Asian 80–120; European 60–90; fine blond 50–60 | 🧠 ↔️ |
| Cross-section min/max | — | 0.5–1.0 | ratio | Blender manual: East Asian 0.8–1; European 0.65–0.9; African 0.5–0.65 [4] | ↔️ |
| Emergence angle to skin | 30–45 | 15–60 | ° | flattest at hairline, temples, nape | 🧠 |
| Hairline transition zone | 5 | 3–10 | mm | non-balding | 🧠 |
| Trichion above glabella | 6 | 5–7 | cm | adults; more with recession | 🧠 ↔️ |

**B. Brows and lashes, adults**

| Quantity | Value | Units | Badge |
|---|---|---|---|
| Hairs per brow | 250–350 typical; 200–600 reported | n | ↔️ |
| Brow hair length | 6–10 (4–15; long in older men) | mm | 🧠 |
| Brow density | 40–120 | hairs/cm² | ↔️ (one burn-study control: 134 ± 38 terminal hairs/cm² [6]) |
| Lift from skin | 5–20 | ° | 🧠 |
| Vertical height, head / tail | 10–15 / 3–5 | mm | 🧠 |
| Direction, head / body / tail | +60…+90 / 0…+20 (lower rows 0…−15) / −10…−40 | ° from horizontal | 🧠 |
| Position vs supraorbital rim | men on rim, flatter; women medial on rim, peak 5–10 mm above | mm | ↔️ |
| Peak position | lateral limbus (Westmore) to lateral canthus (later studies); most common in women between the two (58%) [7] | — | ↔️ |
| Upper / lower lashes | 90–160 at 8–12 / 50–80 at 6–8 | n at mm | 🧠 (as eyes note) |
| Lash base diameter; clump size | 0.06–0.12; 3–6 | mm; n | 🧠 |

**C. Blender starting values (practice, not measurement)**

| Setting | Start | Range | Badge |
|---|---|---|---|
| Guides, full scalp | 800 | 300–3000 | 🧠 |
| Rendered strands (portrait) | 60k | 30k–150k | 🧠 |
| Points per strand | 16 | 8 (short) – 64 (long/curly) | 🧠 |
| Root radius | 0.03 mm | 0.02–0.06 mm (inflate as count drops) | 🧠 |
| Tip/root radius | 0.2 | 0.05–0.4 | 🧠 |
| Brow strands per brow | 300 | 200–600 | 🧠 |
| Lash root radius | 0.04 mm | 0.03–0.06 mm | 🧠 |
| Shrinkwrap offset off skin | 1 mm | 0.5–3 mm | 🧠 |
| Cycles transparent bounces (cards) | 32 | 16–64 | 🧠 |
| Cycles max bounces, light hair | 16 | 12–32 | 🧠 |
| Hero cards: atlas / triangles | 4096² / 20k | 2048²–4096² / 10k–60k | 🧠 |

**D. Principled Hair BSDF (defaults as recalled; Huang inputs 4.0+)**

| Input | Default | Human range | Badge |
|---|---|---|---|
| IOR / Offset | 1.55 / 2° | 1.55 / 2–4° | 🧠 |
| Roughness | 0.3 | 0.15 (glossy) – 0.45 (dull, frizzy) | 🧠 |
| Radial Roughness | 0.3 | 0.3–0.6 | 🧠 |
| Coat | 0 | 0 (fur only) | 🧠 |
| Random Color / Roughness | 0 | 0.05–0.2 | 🧠 |
| Aspect Ratio (Huang) | 0.85 | 0.5–0.9 (Table A) | 🧠 ↔️ |
| Marschner R shift / width | — | −10…−5° / 5–10°; TT ≈ −½·R shift, TRT ≈ −1.5·R shift | 🧠 |
| Melanin / Redness: black | — | 0.92–1.0 / 0.1–0.4 | 🧠 ↔️ |
| Dark brown | — | 0.75–0.9 / 0.3–0.6 | 🧠 ↔️ |
| Light–medium brown | — | 0.5–0.75 / 0.4–0.7 | 🧠 ↔️ |
| Blond | — | 0.15–0.4 / 0.4–0.8 | 🧠 ↔️ |
| Red / auburn | — | 0.3–0.6 / 0.85–1.0 | 🧠 ↔️ |
| Grey / white | — | fraction p of strands at melanin 0–0.05 | 🧠 |

**E. Hair envelope above the scalp (a prior for fitting under hair)**

| Hair class | Offset at crown | Badge |
|---|---|---|
| Bald / buzz (<5 mm) | 0–3 mm | 🧠 |
| Short (1–5 cm) | 5–20 mm | 🧠 |
| Medium (5–15 cm) | 10–40 mm | 🧠 |
| Long straight | 5–30 mm at crown, more at sides | 🧠 |
| Curly / coily, voluminous | 30–150 mm | 🧠 ↔️ |

**F. Curl Hair Curves starting values (practice)**

| Curl type | Radius | Period | Badge |
|---|---|---|---|
| Waves (2a–2c) | 5–15 mm | 30–60 mm | 🧠 ↔️ |
| Curls (3a–3c) | 3–10 mm | 10–30 mm | 🧠 ↔️ |
| Coils (4a–4c) | 1–3 mm | 2–8 mm | 🧠 ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Capture two sets in one session.**
   - Shape set: hair off the ears and hairline.
   - Groom set: hair as worn, plus top and back views for the whorl, parting and nape.

   Reject mirrored selfies, which flip the parting (`community/reddit-face-from-photos.md`). 🧠
2. **Fit the head under the hair.**
   - Mask hair and beard out of the skin terms; take the cranium from priors and the shape set.
   - Hair thickness per view = hair outline − fitted scalp outline; check it against Table E.
   - A scalp outside the hair outline means the skull is too big. An offset above the class range usually means the back of the head is too short. 🧠
3. **Measure on the solved cameras:**
   - the hairline and trichion, temporal recession, sideburn bottom vs tragus, and the nape line;
   - the parting (start, offset from the midline, end) and the whorl (position, handedness);
   - hair-tip landmarks (earlobe, jaw, chin, shoulder) and fringe coverage;
   - brow head, peak, tail and height, triangulated from the front and 3/4 views;
   - lash length and angle in profile. 🧠
4. **Build.**
   1. Scalp → HairUV → Add Rest Position → Empty Hair.
   2. Place hairline and parting guides first, then the crown.
   3. Interpolate with parting islands; clump; curl to the photo's period (Table F); trim to the tip landmarks; Shrinkwrap; profile.
   4. Camera-project the photos onto a dark scalp/root colour under thin areas. 🧠
5. **Check through every solved camera:**
   - the hair-mask silhouette;
   - the highlight band, which runs perpendicular to the strands, so a misplaced band means wrong flow or curvature;
   - the parting gap and scalp show-through.

   Use the lit-match rig from `blender/portrait-lighting-compare.md`. 🧠
6. **Colour.** Never eyedrop.
   - Sample linear colour at mid-length, away from highlights and roots.
   - Render a swatch under the matched rig and iterate Melanin and Redness.
   - Grey is a per-strand mix, densest at the temples. 🧠
7. **Brows.**
   - Project the frontal photo onto the brow skin and threshold it into a density vertex group.
   - Add strands per zone (Table B) and comb them nearly flat.
   - Sculpt the brow ridge from bone and soft tissue, never from the hair outline. Brows stand 1–3 mm proud in profile. 🧠
8. **Lashes.** Generate them in nodes from the lid-margin edge loop (rows, count, ±20 % length, curl, clump), never touching the cornea. 🧠
9. **Real-time.** Bake cards from the strands (ortho camera), layer 2–4 shells, and transfer normals from a smooth scalp-offset shell. 🧠

**What goes wrong** 🧠
- *Helmet hair*: uniform density, no clumps or flyaways, a hard hairline.
- *Spaghetti*: the root radius is too thick for the strand count.
- *See-through hair*: too few, too thin strands and no scalp colour.
- *Hair across the parting*: interpolation crossed the part.
- *Floating roots after a template warp*: no re-snap or rest position.
- *Flat brows*: a texture only.
- *Shrunken skull*: the hair mass was read as cranium.
- *Wrong colour*: highlights were sampled, or AgX desaturated the comparison.

## Algorithmic implications

- **Layers:** skin/skull S, hair envelope H (an offset field over the scalp), and strands. Hair, brow and beard pixels are excluded from the skin silhouette, photometric and contour terms. 🧠
- **Brow landmarks are hair features.** dlib 17–26 and the MediaPipe brow contours get σ 3–5 mm toward the skeletal fit and σ 1–2 mm only for brow placement. 🧠
- **Containment.** For each scalp vertex, the signed distance to the hair-mask visual hull must be ≤ −t_min (2 mm when hair is visible, 0 when bald). Use a hinge penalty weighted like the silhouette. The offset δ is log-normal per region, by user-chosen class (Table E). 🧠
- **Hairline.** Model it as a HairUV polyline: trichion plus 8–12 control points per side, and a nape curve.
  - Priors: trichion–glabella 6 cm (σ 1 cm); left–right mirror deviation σ 3 mm.
  - Observations: σ ≈ 2 px. 🧠
- **Flow field.** A per-vertex tangent field on the scalp, with these constraints:
  - hairline directions from the image orientation maps;
  - parting edges (cut the mesh into islands there, with flow perpendicular-away);
  - whorls as index +1 spiral singularities (spiral angle 20–45°, user-set handedness);
  - gravity for long hair.

  Solve for the smoothest field (Knöppel et al. 2013) or use harmonic interpolation in local frames. 🧠
- **Image orientation.**
  - A Gabor or steerable bank with 16–36 orientations and a 4–8 px wavelength; confidence = peak sharpness.
  - Back-project to surface tangents through the solved camera; weight by confidence × cos(view angle).
  - Resolve the 180° ambiguity by growing root→tip. 🧠
- **Guide growth.** RK2 with 2–3 mm steps.
  - Elevation prior: 10–20° at the hairline, 30–45° at the crown (σ 10°).
  - Project into H via its SDF, stop at the photo tip length, resample to N points. 🧠
- **Children.** Poisson-disc sampling at the Table C density × a painted mask; record the seed. 🧠
- **Brow generator.**
  - Zones head/body/tail at ≈0–15 / 15–70 / 70–100 % of brow length.
  - Angles from Table B (σ 10°), lift 5–20°, length 4–12 mm, curving toward the skin. 🧠
- **Lash generator.** Margin edge, a 5–7 mm punctal skip, rows, count, a length profile peaking lateral-central, curl 30–60°, clumps of 3–6, and ≥ 0.2 mm corneal clearance. 🧠
- **After any template warp:**
  1. `snap_curves_to_surface` (DEFORM);
  2. Restore Segment Length;
  3. Shrinkwrap.

  Never remesh a hair-bearing surface. 🧠
- **Sidecar JSON:** hairline, parting, whorls, envelope class, melanin/redness, grey fraction, curl parameters, counts and seeds. 🧠
- **Compatibility.** Probe `Curves.add_curves`, the asset names and the Huang inputs at runtime; fall back to mesh → Mesh to Curve. 🧠
- **ML strand reconstruction stays an optional plug-in.** It runs out of process and imports polylines, because the models' licences are mostly non-commercial. 🧠 ↔️

## Disagreements, myths & open questions

- **Strands vs cards.** Strands win offline. Cards remain standard in real time, though strand rendering (Unreal grooms) is spreading. ↔️
- **Brow hair count.** Values of roughly 200–600+ per brow circulate without good primary sources. ↔️
- **Ideal brow peak.** The Westmore canon puts it at the lateral limbus; later studies put it more laterally. Neither is a likeness constraint: measure it. ↔️
- **Melanin presets don't transfer.** Blender's 0–1 slider maps nonlinearly to concentration, so values are renderer-specific. ↔️
- **Myth: "more strands = realism."** Clumping, length variation and hairline irregularity matter more. 🧠
- **Myth: "particle hair is gone."** It remained through 4.x; 5.x is unverified. ↔️
- **Open questions:**
  1. 5.x changes to the Curves API, edit-mode tools and asset names.
  2. Huang model support in EEVEE.
  3. Alembic/USD groom attribute names.
  4. Population data on brow density, whorl handedness and lash angles.
  5. Current licences of hair parsers (CelebAMask-HQ-trained, MediaPipe) and of strand reconstruction code.

## Sources

1. Curves Operators, Blender Python API. https://docs.blender.org/api/current/bpy.ops.curves.html
2. Curves(ID), Blender Python API. https://docs.blender.org/api/current/bpy.types.Curves.html
3. Deform Curves on Surface Node, Blender 5.2 LTS Manual. https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/curve/operations/deform_curves_on_surface.html
4. Principled Hair BSDF, Blender 5.3 Manual. https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/hair_principled.html
5. Hair density in different ethnicities (PMC6219221) https://pmc.ncbi.nlm.nih.gov/articles/PMC6219221/ ; Nigerian trichoscopy https://pubmed.ncbi.nlm.nih.gov/40231658/
6. Eyebrow restoration in deep facial burn. https://pmc.ncbi.nlm.nih.gov/articles/PMC10567046/
7. Determinative factors in surgical planning of eyebrow surgery. https://pmc.ncbi.nlm.nih.gov/articles/PMC5533483/

**Further reading (by name, not yet linked)**
- Blender Manual: Curves, Curves Sculpt, Hair node-group assets, Principled Hair BSDF, Hair Info; release notes 3.3, 3.5, 4.0
- Marschner et al., "Light Scattering from Human Hair Fibers", SIGGRAPH 2003
- Chiang, Bitterli, Tappan & Burley, "A Practical and Controllable Hair and Fur Model for Production Path Tracing", EGSR 2016
- Huang, Hullin & Hanika, "A Microfacet-based Hair Scattering Model", EGSR 2022
- Zinke et al., "Dual Scattering Approximation for Fast Multiple Scattering in Hair", SIGGRAPH 2008
- Paris, Briceño & Sillion, "Capture of Hair Geometry from Multiple Images", SIGGRAPH 2004
- Hu et al., "Single-View Hair Modeling Using a Hairstyle Database", SIGGRAPH 2015 (USC-HairSalon)
- Sklyarova et al., "Neural Haircut", ICCV 2023
- Zheng et al., "HairStep", CVPR 2023
- Wu et al., "MonoHair", CVPR 2024
- Zakharov et al., "Human Hair Reconstruction with Strand-Aligned 3D Gaussians", ECCV 2024
- He et al., "Perm", ICLR 2025
- Rosu et al., "DiffLocks", CVPR 2025
- Lee et al., "MaskGAN" (CelebAMask-HQ), CVPR 2020
- Knöppel et al., "Globally Optimal Direction Fields", SIGGRAPH 2013
- Sinha & Poggio, "I think I know that face…", Nature 1996
- De La Mettrie et al., "Shape variability and classification of human hair: a worldwide approach", Human Biology 2007
- Na et al., "Ethnic characteristics of eyelashes", Br J Dermatol 2006
- Gunter & Antrobus, "Aesthetic analysis of the eyebrows", Plast Reconstr Surg 1997
- Farkas, *Anthropometry of the Head and Face*, 1994

## Verification log (2026-11-20)

- Curves API (add_curves, snap_curves_to_surface NEAREST/DEFORM, surface_uv_map): partly confirmed; `snap_curves_to_surface` and `add_curves` exist in the current API. UV attribute name contested (`surface_uv_coordinate` manual vs `surface_uv_coords` dev docs). remove/resize_curves, rest-position operator name and 5.0-5.3 changes unconfirmed. https://docs.blender.org/api/current/bpy.ops.curves.html ; https://docs.blender.org/api/current/bpy.types.Curves.html ; https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/curve/operations/deform_curves_on_surface.html
- Principled Hair BSDF: Melanin/Redness definition confirmed; Aspect Ratio recommended values differ slightly from the note (Asian 0.8-1, Caucasian 0.65-0.9), marked contested; Huang in 4.0, Cycles-only, and the default values unconfirmed. https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/hair_principled.html
- Scalp density/diameter/total count: contested (190 vs 227 /cm2; Nigerian median 330, range 113-660); total count and diameters unconfirmed. https://pmc.ncbi.nlm.nih.gov/articles/PMC6219221/ ; https://pubmed.ncbi.nlm.nih.gov/40231658/
- Brows: peak between lateral limbus and canthus supported in women (58%); density contested (134 +/- 38 terminal/cm2 in one control group); hair count and 5-10 mm female peak height unconfirmed. https://pmc.ncbi.nlm.nih.gov/articles/PMC5533483/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC10567046/
