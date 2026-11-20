# Face retopology and edge flow

> Animation-ready face topology is a quad cage whose edge loops lie where skin folds and stretches. It has concentric rings around the eyes (orbicularis oculi) and mouth (orbicularis oris), a nasolabial loop that carries the smile fold, and rings at the ala and nostrils. Its poles (vertices with 3 or 5+ edges) sit in low-deformation zones. For a photo→3D likeness tool, design one template topology once and fit it to each subject by landmarks and feature curves. Never retopologise the likeness mesh: remeshing destroys correspondence, shape keys, UVs and Multires. Auto-remeshers (QuadriFlow, Instant Meshes, Quad Remesher) make clean sculpt proxies but not dependable facial edge flow. Rig-grade topology comes from wrapping a known template or from manual retopology. No harvest or earlier draft existed for this topic, so every item here is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 5 📄 / 72 🧠 / 11 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Loop systems**
- **Eye rings (orbicularis oculi).** These are concentric loops from the lid margin outward:
  1. a lid-margin pair that forms the 1.5–2 mm flat margin (`blender/eyes-modeling-blender.md`);
  2. 1–2 tuck loops into the socket;
  3. 3–5 upper-lid loops up to the crease;
  4. 2–4 lower-lid loops down to the lid–cheek junction;
  5. 2–3 rings over the orbital rim.

  The rings' radial edges then fall along the crow's-feet lines. 🧠
- **Mouth rings (orbicularis oris).** Each vermilion gets 3–5 loops, plus a support loop just outside the border (the "white roll") and 3–6 skin rings. Inside, 2–4 loops turn into a mouth bag; a sculpt-only likeness needs just a 3–5 mm tuck. 🧠 At least two loops must converge at the commissure so the corner can stretch for a smile (AU12) and bunch for a pucker (AU18/22). 🧠
- **Nasolabial loop.** It follows the crease from the alar–cheek junction to past the lateral commissure, with a support loop on each side. 🧠 It is often the outermost mouth ring carried over the nasal bridge, forming a "mask" loop ↔️. If the fold is not on a loop, the smile creases zig-zag. 🧠
- **Nose.** Loops follow the alar rim and the alar crease. Each nostril (a blind sac) gets 2–3 loops, the columella 2–4 edges across, and the tip and domes their own loops. After the lids and lips, the nostrils are the densest feature. 🧠
- **Forehead.**
  - Horizontal loops carry the frontalis lines (AU1/2).
  - Vertical edges between the brows carry the corrugator lines (AU4).
  - A horizontal edge at the nasal root carries the procerus line.

  🧠 Wrinkles run perpendicular to fibre pull. Sphincter rings therefore follow the fibres, and their radial edges carry the radial wrinkles (crow's feet, vertical lip lines). 🧠
- **Jaw, neck and ear.** A loop follows the mandibular border (the jaw silhouette), and the neck is built from rings. Each ear is its own ring system joined by a root ring, with density-reducing poles behind it (`anatomy/ear.md`). 🧠
- **Midline.** A row of vertices sits exactly at x = 0 so that Mirror Clipping and the symmetry maps work. The shape may be asymmetric, but the topology is symmetric. 🧠

**Poles**
- **Poles cannot be removed, only placed.** On a closed genus-0 all-quad surface, Σ(4 − valence) = 8. With one open boundary, such as an open neck, the interior terms (4 − val) plus the boundary terms (3 − val) sum to 4. Any additional poles come in 3/5 pairs. 🧠
- **Sites:**
  - the cheek (malar), where the eye rings meet the mouth system;
  - the temple, lateral to the outer canthus;
  - the glabella or nasal root;
  - the alar crease, at the top of the nasolabial loop;
  - the sides of the chin;
  - the jaw angle, behind the ear and the crown, where they reduce density.

  🧠
- **Keep poles at least 2 rings away** from the lid margins, canthi, vermilion border, commissure and alar rim. Catmull–Clark leaves a faint dimple at irregular vertices that shows in specular, and a pole on a crease line distorts the fold. 🧠 Whether a 5-pole may sit at the modiolus is disputed ↔️.

**Tools**
- **Native Blender.**
  - Snapping: Face Project projects along the view, Face Nearest goes to the closest point (also reaches occluded geometry); Project Individual Elements applies with Face Project 📄 [4]; turn on Backface Culling (unconfirmed).
  - The Retopology overlay, Poly Build, Grid Fill and Bridge Edge Loops.
  - Modifiers: Mirror (Clipping) and Shrinkwrap (On Cage + Edit Mode).
  - LoopTools (Relax, Circle, Space), an extension since 4.2.

  🧠 Snap option names were reorganised during 3.x–4.x, so check them against the 5.x manual ↔️.
- **QuadriFlow** (Remesh panel, built in since about 2.81) targets a face count, edge length or ratio, with symmetry and preserve-sharp options. It needs manifold input and produces even quads but no facial loops. 🧠
- **Instant Meshes** (Jakob et al. 2015, BSD-style licence, standalone) does field-aligned remeshing. Its comb and edge-constraint strokes can coax eye and mouth loops, but it has been largely unmaintained. 🧠
- **Quad Remesher** (Exoside, by ZRemesher's author; paid; has a Blender bridge) offers target count, adaptive size, symmetry, hard edges, material groups as boundaries and painted density. It gives the best automatic face when the eyes and mouth are split into separate groups, but riggers still fix its loops. 🧠 Price, licence and 5.x support are time-sensitive ↔️; Exoside lists Pro perpetual at $109.90 (single host) or $139.90 (all hosts) and Blender as supported [5].
- **RetopoFlow** (CG Cookie, now Orange Turbine) has GPL source and is sold for updates on Superhive, formerly Blender Market. 📄 [1][2][3]
  - RF3 tools: Contours (neck, ear rim), PolyStrips (eye and mouth loops), PolyPen, Strokes, Patches, Loops, Tweak, Relax.
  - RF4 is a rewrite inside Blender's edit mode (4.0 released 20 Oct 2025). Its 5.x status: Superhive lists support for Blender 4.2–5.2 (v4.1.9, 25 Jun 2026, added 5.2) (corrected in verification). 📄 [1][3]
- **Other add-ons:** PolyQuilt (free), Speedretopo (paid), Bsurfaces, F2. 🧠
- **Wrapping beats retopology for heads.** Options are R3DS Wrap (now sold under the Faceform name; "reference commercial tool" status unconfirmed) 📄 [7], Mesh to MetaHuman, CC Headshot, FaceBuilder, or the library's template plus NICP (`blender/import-export-scans.md`). 🧠

## Numbers & reference tables

**Table 1 – Budgets by use (head incl. neck and ears unless noted)**

| Use | Element | Range | Typical | Badge |
|---|---|---|---|---|
| Sculpt base under Multires | quads | 2k–25k | 6–12k; L4 ≈ 1.5–3M | 🧠 |
| Fitting template | vertices | 2k–15k | ≈5k | 🧠 |
| Mobile/VR real-time head | triangles | 1.5k–8k | — | ↔️ |
| PC/console hero head, LOD0 | triangles | 10k–50k | — | ↔️ |
| Film/VFX subdivision cage | quads | 5k–30k | render at subdiv 2–3 (×16–×64) | 🧠 |
| Final sculpt / print | polygons | 1M–20M | topology irrelevant | 🧠 |
| One ear, base level | quads | 300–1,000 | ≈500 | 🧠 |

**Table 2 – Reference topologies (recalled, as elsewhere in this library)**

| Mesh | Vertices | Faces | Coverage | Badge |
|---|---|---|---|---|
| MediaPipe canonical | 468 | triangles | face | 🧠 |
| ARKit face mesh | 1,220 | triangles | face | 🧠 |
| FLAME | 5,023 | 9,976 triangles | head, neck, eyeballs | 🧠 |
| MakeHuman hm08 (MPFB2) | ≈13.4k | quads | full body | 🧠 |
| MetaHuman LOD0 head | ≈24k (Epic's LOD table lists 24,000 head vertices as a guideline) | mixed | head | 📄 [6] |
| BFM 2009 | 53,490 | triangles | face | 🧠 |

**Table 3 – Loop counts on a mid-density head (8k–15k quads)**

| Feature | Loops across | Edges around ring | Badge |
|---|---|---|---|
| Eye: lid margin → beyond orbital rim | 6–10 | 16–28 | 🧠 |
| Upper lid: margin → crease | 3–5 | — | 🧠 |
| Lower lid: margin → lid–cheek junction | 2–4 | — | 🧠 |
| Lid-margin band | 2 (+1–2 tuck) | — | 🧠 |
| Mouth: wet line → outermost ring | 8–14 | 20–36, even | 🧠 |
| Each vermilion | 3–5 | — | 🧠 |
| Nasolabial fold | 1 + 1–2 support per side | — | 🧠 |
| Nostril interior | 2–3 | 8–12 | 🧠 |
| Forehead | 4–8 horizontal | — | 🧠 |
| Neck | — | 32–64 | 🧠 |

**Table 4 – Target edge length at real scale (8k–15k-quad head).** These are derived from a head-plus-neck area of about 0.13 m², which gives a mean edge of about 3.6 mm at 10k quads. They are consistent with the 2–4 mm in `blender/blender-sculpt-features-5x.md`.

| Region | Across loops (mm) | Along loops (mm) | Badge |
|---|---|---|---|
| Lid margin, canthi | 1–2 | 2–4 | 🧠 |
| Lips (vermilion, border) | 1.5–3 | 3–5 | 🧠 |
| Nose, nostrils, alar crease | 1.5–3 | 2–4 | 🧠 |
| Nasolabial, perioral skin | 3–5 | 3–5 | 🧠 |
| Cheek, forehead, chin | 4–7 | 4–7 | 🧠 |
| Scalp, back of head, neck | 6–12 | 6–12 | 🧠 |

**Table 5 – Template QA thresholds**

| Metric | Threshold | Badge |
|---|---|---|
| Non-quads in deforming zones | 0 | 🧠 |
| Non-quads elsewhere (subdivision cage) | ≤ 0.5–1 %, hidden areas only | 🧠 |
| Pole distance from lid margin, vermilion, commissure, alar rim, canthi | ≥ 2 rings | 🧠 |
| Pole count, head with ears | ≈20–80; net Σ(4−val) = 8 closed, 4 with an open neck | 🧠 |
| Quad interior angle | target 60–120°; warn outside 45–135° | 🧠 |
| Quad aspect ratio | ≤ 2; ≤ 3–4 along lid and lip loops | 🧠 |
| Edge-length CV within a region | ≤ 0.25–0.35 | 🧠 |
| Catmull–Clark inward shrink, convex curve | ≈ e²/(6R): 0.1–0.4 mm at e = 2–5 mm on lips, nose tip, chin | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Choose the delivery topology before fitting** (`community/blenderartists-forum.md`). Put landmarks on loop junctions, and store the named loops as vertex-index lists in the template sidecar. 🧠
   - en and ex at the lid-margin corners;
   - ch where the mouth loops converge;
   - sto on the midline lip contact;
   - sn at the junction of columella and lip;
   - prn on the tip loop;
   - al on the alar rim loop;
   - pg′ and me′ on the midline chin.
2. **Wrap scans and AI meshes; do not retopologise them.** The sequence is landmark similarity, then warp, then coarse-to-fine NICP, then limited projection, then Multires Reshape (`blender/import-export-scans.md`). 🧠
3. **Manual retopology setup.** 🧠
   - **Reference:** work at real scale on a decimated reference (0.2–1M triangles) set unselectable.
   - **Modifier stack:** Mirror (X, Clipping), then Shrinkwrap (Nearest Surface Point, offset 0–0.1 mm, On Cage + Edit Mode), then a Subdivision modifier at viewport level 1, added late.
   - **Snapping:** Face Project with Project Individual Elements and Backface Culling, plus the Retopology overlay.
   - **Build order:** eye rings, then mouth rings, then the nasolabial/mask loop, then the nose, then the cheek (place the pole here), then forehead, jaw, neck, ear and scalp.
   - **Before Grid Fill:** count the edges on opposite sides of each patch. A mismatch needs a 3/5 pole pair placed away from features.
4. **Inspect.** 🧠
   - Turn on the Statistics overlay.
   - Find non-quads with Select All by Trait → Faces by Sides ≠ 4.
   - Find poles with Select Similar → Amount of Connecting Edges, starting from a valence-4 vertex, then invert the selection.
   - Check the Mesh Analysis → Distortion overlay.
   - Use a glossy matcap at Subdivision 2 to spot dimples.
5. **Deformation tests** (quick shape keys or proportional edits; see `anatomy/facs-expressions.md`). 🧠
   - **Blink:** the upper lid travels about 8–12 mm over the cornea and must not intersect it.
   - **Jaw open:** at 20–40 mm the lip loops must not collapse.
   - **Smile:** the fold should form on the nasolabial loop.
   - **Also test** a pucker, brow raise, frown and sneer.
6. **Transfer the likeness.**
   1. Subdivide a copy and Shrinkwrap it: Target Normal Project, limit 2–5 mm, masked off the lips, lids and nostrils.
   2. Add Multires to the base and Reshape from the copy.
   3. Apply Base so the cage moves outward and compensates for subdivision shrink.

   🧠
7. **Add-on default.** Use about 8–12k quads for head, neck and ears, including the mouth bag and sockets. That is about 2–3M quads at Multires L4. 🧠

**What goes wrong** 🧠
- Spiral mouth rings that never close cannot be selected as loops and deform unevenly.
- Poles on the lid margin or vermilion notch after subdivision.
- With too few upper-lid loops, the lid cuts through the cornea on a blink.
- A vermilion border without a support loop looks rubbery. An edge crease helps only where Multires "Use Creases" is on.
- A nasolabial loop off the fold makes the smile crease zig-zag.
- Uniform density wastes polygons on the scalp and leaves the lids coarse.
- Remeshing the likeness loses keys, UVs and landmarks and rounds off sharp features.
- An unmasked Shrinkwrap fuses the lips and lids.
- An unapplied object scale distorts offsets and limits.

## Algorithmic implications

- **Template sidecar.** The template's data travels with it in a sidecar file:
  - `loops`: named, ordered vertex-index lists with a closed or open flag, such as `lid_margin_upper.L`, `vermilion_upper`, `nasolabial.L` and `alar_rim.L`;
  - `poles`;
  - `feature_curves`, mapping loops to 2D contours;
  - `regions`;
  - `symmetry_map`;
  - `midline`.

  After every operation, assert that the vertex count and order are unchanged, the loops are still closed, and no pole sits in a forbidden zone. 🧠
- **Curve terms, not just points.** Feature loops get a point-to-curve residual: a small σ normal to the curve, free sliding along it, and a spacing regulariser. 🧠 This agrees with `anatomy/craniometric-landmarks.md`. Suggested σ normal to the curve:
  - lid margin and vermilion border: 0.5–1.0 mm;
  - alar rim: 1–1.5 mm;
  - nasolabial fold: 2–3 mm, down-weighted on neutral photos;
  - jaw silhouette: 1.5–2.5 mm.
- **Terms that preserve edge flow.** 🧠
  - ARAP or Laplacian against the template, with σ at 5–15 % of rest edge length;
  - a second-difference term along each named loop, σ ≈ 0.2–0.5 mm per vertex;
  - tangential relaxation projected to the surface, excluding the feature loops;
  - barriers on quad angles below 30° or above 150°, on aspect ratios above 4, and on normal flips.
- **Fit the limit surface.** If the delivery mesh will be subdivided, compute residuals on S·V, where S holds the sparse Catmull–Clark limit stencils; Blender's evaluated level 2 is a cheap approximation. The uniform-curve limit point (p₋ + 4p + p₊)/6 pulls the surface inward by ≈ e²/(6R), which thins lips, lids and the nose tip. 🧠
- **Pole QA.** Forbidden zones are geodesic rings of at least 2 around the feature loops. Report each violation and the net Σ(4 − valence). 🧠
- **Inputs for auto-retopology of arbitrary meshes.** Export the Table 4 density as vertex colour, which Quad Remesher reads. Export the feature loops as edge constraints for Instant Meshes, or as group boundaries. 🧠
- **Cross-topology map.** Embed the quad delivery template barycentrically in the fitting template (for example FLAME) once, after a careful wrap. Map each subject's fit through that embedding plus a normal offset. Retopology then happens once per template, never once per subject. 🧠
- **Symmetry.** The topology is exactly symmetric. Shape asymmetry gets a prior σ of 1.5–3 mm and is never forced to zero (`anatomy/facial-asymmetry.md`). 🧠

## Disagreements, myths & open questions

- **Muscle-led or fold-led loops** ↔️. The two coincide for the sphincters. They diverge at the cheek and nasolabial region, where the fold is a fat–ligament boundary (`anatomy/smas-ligaments.md`). Deformation-led placement is the safer rule.
- **A closed mask loop around nose and mouth, or open loops ending in poles near the ala and chin** ↔️. Both ship in production heads.
- **A modiolus 5-pole, or one further out on the cheek** ↔️. A pole at the modiolus concentrates the smile's stretch.
- **Vendor auto-retopology as production-ready** ↔️. It is fine for statics, prints and sculpt proxies, but riggers reject it (`community/ai-assisted-sculpting.md`).
- **Myth: triangles are always bad.** They are fine in non-deforming game LODs and harmful in subdivision cages near features. 🧠
- **Myth: more loops make better animation.** Over-dense cages make blendshapes and weights lumpy. Density should follow the frequency of deformation. 🧠
- **Myth: retopology at the end is harmless.** It resamples the likeness, softens edges and drops landmarks, keys and Multires. 🧠
- **Myth: good topology has no poles.** Euler's formula forbids that. 🧠
- **Open questions:**
  - how 2024–2026 learned quad remeshers perform on faces;
  - whether RetopoFlow, Quad Remesher and LoopTools work on 5.x;
  - whether 5.x has added native retopology tools;
  - whether any quantitative study compares face topologies by deformation error (none known);
  - the delivery-template licence: FLAME is non-commercial, hm08 is CC0 ↔️.

## Sources

1. Superhive, RetopoFlow 4 product/versions: https://superhivemarket.com/products/retopoflow/versions
2. RetopoFlow source (GPL): https://github.com/CGCookie/retopoflow
3. CG Channel, Orange Turbine releases Retopoflow 4: https://www.cgchannel.com/2026/04/orange-turbine-releases-retopoflow-4-for-blender/
4. Blender 5.2 LTS Manual, Snapping: https://docs.blender.org/manual/en/latest/editors/3dview/controls/snapping.html
5. Exoside, Buy Quad Remesher: https://exoside.com/quadremesher/quadremesher-buy/
6. Epic Games, Platform support and LOD specifications for MetaHumans: https://dev.epicgames.com/documentation/en-us/metahuman/platform-support-and-lod-specifications-for-metahumans
7. CG Channel, Faceform releases Wrap 2025.11 and Wrap4D 2025.11: https://www.cgchannel.com/2025/12/faceform-releases-wrap-2025-11-and-wrap4d-2025-11/

Library cross-references are given inline as file paths.

**Further reading (by name, not yet linked)**
- Catmull & Clark, "Recursively generated B-spline surfaces on arbitrary topological meshes", Computer-Aided Design, 1978
- Stam, "Exact Evaluation of Catmull–Clark Subdivision Surfaces at Arbitrary Parameter Values", SIGGRAPH 1998
- Bommes et al., "Quad-Mesh Generation and Processing: A Survey", Computer Graphics Forum, 2013
- Bommes, Zimmer, Kobbelt, "Mixed-Integer Quadrangulation", SIGGRAPH 2009
- Jakob, Tarini, Panozzo, Sorkine-Hornung, "Instant Field-Aligned Meshes", SIGGRAPH Asia 2015
- Huang et al., "QuadriFlow: A Scalable and Robust Method for Quadrangulation", SGP 2018
- Sorkine & Alexa, "As-Rigid-As-Possible Surface Modeling", SGP 2007
- Amberg, Romdhani, Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007
- Lewis et al., "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Li et al., "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017
- Osipa, "Stop Staring: Facial Modeling and Animation Done Right", Sybex, 3rd ed. 2010
- Pixar OpenSubdiv documentation (limit stencils)
- Blender Manual: Snapping, Retopology overlay, Poly Build, Mirror, Shrinkwrap, Remesh, Multires, Mesh Analysis
- RetopoFlow and Exoside Quad Remesher documentation; Polycount wiki topology pages

## Verification log (2026-11-20)

- Default density spec (8-12k quads, edge lengths, loop counts): unconfirmed. Searches found no source for these numbers (only a dated Softimage ~2,000-polygon cage guide). Stays unconfirmed.
- RetopoFlow GPL source, Superhive sale, Orange Turbine: confirmed [1][2][3]. RF4 5.x status: corrected, Superhive lists Blender 4.2-5.2 [1]. https://superhivemarket.com/products/retopoflow/versions
- Quad Remesher: paid and Blender supported confirmed, prices added [5] https://exoside.com/quadremesher/quadremesher-buy/; vertex-colour density, material-group boundaries, bridge details: unconfirmed.
- Snapping: Face Project, Face Nearest, Project Individual Elements confirmed [4] https://docs.blender.org/manual/en/latest/editors/3dview/controls/snapping.html; Backface Culling, Retopology overlay (3.6), QuadriFlow since 2.81, LoopTools extension since 4.2: unconfirmed.

## Verification log, pass 2 (2026-11-20)

- MetaHuman LOD0 head about 24k vertices: confirmed (one source), Epic's LOD table lists 24,000 head vertices as a guideline, not exact per character [6] https://dev.epicgames.com/documentation/en-us/metahuman/platform-support-and-lod-specifications-for-metahumans
- Mobile/VR 1.5k-8k and PC/console LOD0 10k-50k triangle budgets: unconfirmed (no official triangle figure found; a forum anecdote reports about 60k tris for a character face mesh, not a spec). Stay contested.
- ARKit face mesh 1,220 vertices: unconfirmed (search returned nothing).
- R3DS Wrap sold under the Faceform name: confirmed (one source) [7] https://www.cgchannel.com/2025/12/faceform-releases-wrap-2025-11-and-wrap4d-2025-11/ ; latest version Wrap 2025.11. "Remains the reference commercial wrapping tool": unconfirmed (judgement).
