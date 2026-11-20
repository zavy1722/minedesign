# Cleaning scans and wrapping base topology

> VFX, game and Blender/ZBrush practice converges on one pipeline: keep the raw scan untouched as the bake source, clean a decimated, masked copy into a *fitting target*, wrap a known-topology base onto it (point pairs, then coarse-to-fine non-rigid fitting), recover detail by projection (Multires Reshape or ZBrush Project All), and bake colour, normal and displacement from the raw scan. R3DS Wrap/ZWrap (now sold as Faceform, to verify) is the community reference; Blender's Shrinkwrap, Surface Deform and Data Transfer are building blocks, not a wrap, because without landmark terms or a stiffness schedule correspondence slides and lips and lids fuse. Likeness lives in forms of 2 mm wavelength and up, so cleaning must never smooth or symmetrise at radii that move lid, lip, alar or jaw contours. This topic had no harvest or earlier draft: linked sources are borrowed from sibling harvests and the rest is expert knowledge.
>
> Evidence status: 4 ✅ / 9 📄 / 53 🧠 / 11 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Cleaning the scan**
- **Keep three objects:** `scan_raw` (locked bake source), `scan_target` (cleaned, decimated, weighted) and `base` (template). Cleaning is lossy, and baking from a cleaned copy bakes the cleaning in 🧠.
- **Order:** scale and orientation (`blender/import-export-scans.md`) → crop background, shoulders and plinth → delete islands → fix non-manifold and degenerate faces → fill only small holes → denoise selectively → decimate with features protected 🧠.
- **Defects that break wraps** (full list in `reconstruction/photogrammetry-heads.md`): the hair shell, noisy corneas, lips fused at the stomion, lash spikes and rim artefacts 🧠.
- **Do not invent surface you will fit to.** Leave large holes (under the chin, behind the ears, the crown) open and mask them out: a filled patch becomes a false target the wrap obeys 🧠. Random-walk SSS test renders need a closed mesh [12] 📄, so close a *copy*.
- **The scan must overhang the base.** Cut the base's neck shorter than the scan's, or base boundary vertices get dragged toward the scan rim 🧠.
- **Denoise by frequency.** Scan noise is ≈0.05–0.3 mm; likeness forms are ≥2 mm. Smooth at radius ≤1 mm on cheeks, forehead and neck only; mask lid margins, alar groove, philtrum, vermilion border and nasolabial fold. Use non-shrinking filters (Taubin or HC-Laplacian in MeshLab; Laplacian Smooth with Preserve Volume; Sculpt Mesh Filter → Surface Smooth with cavity auto-masking): plain Laplacian shrinks the nasal tip and chin 🧠.
- **Rebuild before wrapping:** replace scanned eyeballs with ≈12 mm-radius spheres placed from canthi and lid margins; cut the fused lip seam along the stomion; exclude the hair shell or sculpt a scalp inside it 🧠.
- **Tools:** Blender Select All by Trait (Non-Manifold, Loose), Clean Up (Delete Loose, Degenerate Dissolve, Fill Holes), Grid Fill, Face Sets → Fair Positions/Tangency; MeshLab Remove Isolated Pieces, Close Holes, Quadric Edge Collapse; ZBrush Decimation Master, Close Holes. Voxel remesh only *after* closing holes, or an open scan becomes a double-walled shell 🧠.

**Wrapping onto a known topology**
- **Wrap/ZWrap recipe** (node names at moderate confidence) 🧠:
  1. `RigidAlignment` from 3–12 point pairs.
  2. `SelectPolygons` to exclude the eyeballs, mouth bag, nostril interiors and scalp under hair.
  3. `Wrapping` with 20–60 control-point pairs, coarse-to-fine, with smoothness and control-point weight relaxing from initial to final values.
  4. `Subdivide` and re-wrap or project.
  5. `TransferTexture` for maps; `BlendShapes` for expression sets.
- **ZWrap** runs the same solver inside ZBrush. Artists then subdivide one level at a time with **Project All** per level, masking the eyes and mouth and brushing bad spots back with Morph Target 🧠.
- **`OpticalFlowWrapping`** aligns pores and freckles across images. It matters for expression and 4D sets; a single neutral scan needs only a geometric wrap ↔️.
- **Annealing works; black boxes do not.**
  - Non-rigid ICP starts stiff and relaxes from global to local deformation [1]. Face-capture work also lowers the landmark weight over the stages [2][3] ✅.
  - A black-box optimiser has a tiny convergence basin and fails on incomplete scans [1] 📄. That is why everyone starts from point pairs.
- **Landmark warp first.** A thin-plate spline regularised with K + λI tolerates noisy picks [4][5] ✅. ARAP/Laplacian energies keep local detail rigid while landmarks move [6] 📄.
- **Place control points on contours, not flat skin:** canthi, mid lid margins, alar crease, subnasale, cheilion, vermilion peaks, stomion, pogonion, gonion, tragus, helix top, lobule. About two-thirds go on the eyes, nose and mouth 🧠.
- **Blender natives, honestly ranked** 🧠:
  - **Shrinkwrap** (Nearest Surface Point, Project, Nearest Vertex, Target Normal Project; Limit in Project mode; vertex-group mask) moves each vertex independently: a good final snap after a landmark warp, a bad first move. Corrective Smooth between two Shrinkwraps relaxes bunching.
  - **Laplacian Deform** (anchor group plus hooks on landmarks) is the nearest built-in landmark warp.
  - **Surface Deform** does not fit; it passes on a target's *later* deformation. Bind it once shapes match, to drive a dense mesh from a fitted cage or move shape keys across topologies.
  - **Data Transfer** moves UVs, colour attributes, vertex groups and normals between non-matching meshes, not shape keys.
  - **Geometry Nodes**: Sample Nearest Surface or Raycast, Blur Attribute (3.5+), iterated in a Repeat Zone (4.0+), gives a smoothness-regularised wrap with no landmark term.
- **Mesh to MetaHuman** solves an Identity from marker curves, conforms MetaHuman topology and runs a cloud autorig. Community reports agree it drifts at the nasal tip, vermilion and lid aperture (`blender/metahuman-cc-bridges.md`) ↔️. A single-image Blender add-on, MetahumanModeler, also outputs MetaHuman topology, with no accuracy data [13] 📄.
- **Measured accuracy:**
  - Automatic non-rigid template registration: 53.1 % of landmarks within 2 mm and 84.4 % within 4 mm; best in the midface, worst in the upper face [7] 📄.
  - Stereophotogrammetry vs calipers: about 0.2 mm mean difference, mostly within 2 mm [8][9] ✅.
  - A mobile-device scanner: about 1 mm [10] 📄.
- **Symmetric topology, asymmetric shape.** Healthy faces differ from their mirror image by 0.80 ± 0.24 mm RMS [11] 📄 (attribution inferred from excerpts), so never symmetrise the fitted shape.

**Detail, texture and blendshape transfer**
- **Multires Reshape** (the Blender analogue of stepwise Project All) 🧠:
  1. Duplicate the base and apply its Multires at level N.
  2. Shrinkwrap the duplicate to `scan_raw` (Project, both directions, Limit 1–2 mm) and apply.
  3. Select the duplicate, make the original active, and Reshape.
  4. Repeat per level.
- **Bake from Multires** (Normals or Displacement) skips the second object 🧠 (verify for 5.x).
- **Selected-to-Active bakes** (Cycles) from `scan_raw` to the base UVs 🧠:
  - Colour: use the **Emit trick** (scan texture or Color Attribute → Emission), or Diffuse with only Color contributing. Neither bakes in lighting.
  - Save with **Save as Render off**, or the view transform (AgX, the default since 4.0) is burned into the albedo.
- **Map conventions** 🧠: normal maps are Tangent and Non-Color, OpenGL +Y in Blender; flip green for Unreal (DirectX). Displacement goes in a 32-bit float EXR at mid-level 0.
- **Texture the base from the photos.** Import the wrapped, UV'd base into Metashape ("Keep uv") or RealityCapture/RealityScan in the scan's frame and texture it from the photos directly. This skips one colour resampling ↔️.
- **Scan textures hold baked lighting.** Cross-polarised capture fixes it at the source. De-lighting tools (Agisoft De-Lighter, Metashape's remove-lighting, Unity's experimental tool) are partial, and their status is time-sensitive ↔️.
- **Blendshapes across topologies:** bind Surface Deform on the neutral, set each source key to 1, then "Save as Shape Key". The principled method is deformation transfer; the commercial one is Wrap's `BlendShapes` 🧠.
- **Bought detail packs** (e.g. Texturing.xyz multichannel faces) are wrapped onto your head and transferred in UV space. Their pores belong to someone else: they add realism, not likeness 🧠.

## Numbers & reference tables

**Table 1 — Mesh budgets and mean edge length** (adult head plus short neck ≈0.12 m²; edge ≈ √(area/faces); arithmetic)

| Stage | Size | Mean edge | Role | Badge |
|---|---|---|---|---|
| Raw photogrammetry mesh | 1–20 M tris | 0.1–0.4 mm | bake source | 🧠 |
| Fitting target | 50–200 k tris | 1–2 mm | wrap target | 🧠 |
| Base, level 0 | 10 k quads | ≈3.5 mm | likeness shape key | 🧠 |
| Multires L2 / L3 | 160 k / 640 k | 0.87 / 0.43 mm | forms; likeness complete | 🧠 |
| Multires L4 / L5 | 2.6 M / 10.5 M | 0.22 / 0.11 mm | pores (or use maps) | 🧠 |
| Texture 2K / 4K / 8K, 70 % packing | — | 0.20 / 0.10 / 0.05 mm per texel | 4K ≈ scan GSD of 0.05–0.1 mm | 🧠 |

**Table 2 — Suggested wrap schedule** (engine design defaults, consistent with sibling notes)

| Stage | Regulariser radius / stiffness α | Landmark weight β | Max correspondence | Normal gate | Iterations | Badge |
|---|---|---|---|---|---|---|
| Rigid (Umeyama) | — | pairs only | — | — | closed form | 🧠 |
| TPS | λ such that landmark residual ≈ σ_lm | — | — | — | closed form | 🧠 |
| NICP 1 | 15–20 mm / 100 | 1.0 | 10 mm | 60° | 5–10 | 🧠 |
| NICP 2 | 8–10 mm / 20–50 | 0.5 | 8 mm | 60° | 5 | 🧠 |
| NICP 3 | 4–5 mm / 5–10 | 0.2 | 5 mm | 45° | 5 | 🧠 |
| NICP 4 | per vertex / 1–2 | 0.05 | 3 mm | 45° | 3–5 | 🧠 |
| Snap + relax | tangential only | frozen | ray 1–2 mm | 45° | 1–3 | 🧠 |

**Table 3 — Region weights**

| Region | Data weight | Notes | Badge |
|---|---|---|---|
| Forehead, cheeks, nasal dorsum, chin | 1.0 | primary evidence | 🧠 |
| Lid margins | 0.5 | contour σ 0.5–1 mm; lashes corrupt the scan | 🧠 |
| Eyeballs, mouth interior, nostril interiors | 0 | rebuilt | 🧠 |
| Vermilion | 1.0 | stomion cut; contour σ ≈1 mm | 🧠 |
| Ears | 0.3–0.5 (backs 0) | backs from photos | 🧠 |
| Scalp under hair / beard | 0.1 / 0.2–0.5, one-sided | inward prior 5–15 mm (1–3 mm capped) | 🧠 |
| Scan boundary band, 2–3 mm | 0 | rim artefacts | 🧠 |

**Table 4 — Acceptance checks**

| Check | Threshold | Badge |
|---|---|---|
| Face distance to scan: median / RMS / p95 | < 0.3 / < 0.5 / < 1.5 mm | 🧠 design |
| Landmark residual | most < 2 mm (automatic reference: 53.1 % < 2 mm, 84.4 % < 4 mm) | 📄 [7] |
| Face area ratio vs template; minimum angle | 0.2–5, no flipped faces; > 10–15° | 🧠 |
| Scan modality accuracy | ≈0.2 mm mean vs calipers; most < 2 mm | ✅ [8][9] |
| Natural asymmetry (keep it) | 0.80 ± 0.24 mm RMS | 📄 [11] |

**Table 5 — Tools**

| Tool | Keeps your topology | Landmarks + annealing | Cost | Badge |
|---|---|---|---|---|
| Faceform/R3DS Wrap | yes | yes | commercial, trial | ↔️ (licence and price) |
| ZWrap (ZBrush plug-in) | yes | yes | commercial | ↔️ |
| Shrinkwrap / Laplacian Deform / GN | yes | none / anchors / smoothing only | free | 🧠 |
| Mesh to MetaHuman | no | marker curves | UE EULA, Epic login | ↔️ |
| Reallusion Headshot (mesh mode) | no (CC3+) | alignment points | commercial | 🧠 |
| QuadriFlow / Instant Meshes / Quad Remesher | no (new each run) | none | free / free / paid | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Gate the import:** apply scale and rotation; check intercanthal width is ≈31–41 mm; check for mirroring (`blender/import-export-scans.md`).
2. **Duplicate:** hide and lock `scan_raw`; clean `scan_target`. Cut the neck below the thyroid cartilage, leaving 3–5 cm more neck than the base. Delete islands under ~1 % of the vertices.
3. **Rebuild:**
   - 12 mm eye spheres;
   - a lip-seam cut;
   - big holes left open;
   - a `fit_weight` vertex group painted from Table 3.
4. **Denoise** with Surface Smooth plus cavity masking (radius ≤1 mm, cheeks and forehead). Decimate to 100–200 k triangles with the lids, lips, alae and ears protected.
5. **Neutral check:** a smile or parted lips on the scan becomes identity, so neutralise first (`reconstruction/expression-neutralization.md`).
6. **Point pairs:** place 25–40 landmarks. Fit rigid, then TPS (engine) or Laplacian Deform with hooks (manual).
7. **Non-rigid:** run the engine schedule (Table 2), or by hand:
   1. Shrinkwrap (Project, no axis = along normals, Negative + Positive, Limit 3–5 mm, masked; Target Normal Project has, I believe, no Limit);
   2. Corrective Smooth (Length Weight, 5–20 repeats, Pin Boundaries);
   3. Shrinkwrap again at Limit 2 mm.

   Store the result as shape key `scan_fit`, never applied.
8. **QA:** colour the signed distance (Table 4). Then judge the lids, lip line, alar groove and jaw angle through the solved photo cameras, not the heat-map alone.
9. **Detail:** Reshape Multires L1–L3. Bake normal and displacement for L4+ with Extrusion 1–3 mm, Max Ray 5–10 mm and a 16 px margin at 4K (32 px at 8K).
10. **Colour:** Emit-bake from `scan_raw`, or retexture inside the photogrammetry tool. Then hand off via `blender/metahuman-cc-bridges.md`.

**What goes wrong:** welded lips (no stomion cut or mouth mask); lids glued to a noisy cornea (no eye spheres); a helmet cranium (hair fitted as skull); bunched nasolabial quads (Shrinkwrap without relaxation); a base rim rolled inward (scan shorter than base); smeared ear or nostril texture (extrusion too large); a tone-curved albedo (Save as Render on); lost likeness (symmetrised scan).

## Algorithmic implications

- **API:** `prepare_target(scan, masks)` → weights and boundary band; `wrap(template, target, pairs, schedule)` → per-vertex displacement stored as a shape key; `qa()` → per-region statistics and a heat-map attribute. Never change vertex order; check a topology hash 🧠.
- **Energy:** E = Σ wᵢ ρ(point-to-plane / σ_data) + Σ ‖landmark residual‖² / σ_lm² + α E_reg + constraints, ρ = Huber at 1.5 σ_data. σ_data: 0.3–0.5 mm (rigs), 0.5–1 mm (single camera, central face), 2–3 mm (ears, hairline, under the chin) 🧠.
- **Regulariser:** an embedded deformation graph whose node radius follows Table 2, or per-vertex affine NICP [1]. Either mimics Wrap's coarse-to-fine control nodes 🧠.
- **Correspondence** 🧠:
  - Add a reverse (scan→template) term at weight 0.3–0.5, so the alar crease and nasolabial fold are pulled in.
  - Reject pairs beyond max(3·MAD, the stage cap), beyond the normal gate, or inside the boundary band.
- **Landmark σ:** points 1 mm; sliding contours (lid margins, vermilion, brows) 1.5–2 mm as point-to-curve distances; ears and detector landmarks on renders 2–3 mm 🧠.
- **Constraints** 🧠:
  - lid-margin vertices on the eyeball sphere + 0–0.5 mm (σ 0.3 mm);
  - no upper/lower lip interpenetration (hinge, margin 0–0.2 mm);
  - edge-length log-ratio to the template σ ≈ 0.3;
  - hair regions penalised only when the template lies outside;
  - symmetry σ ≥ 3–5 mm, only to fill unseen regions.
- **Final pass** 🧠: snap along normals (limit 1–2 mm), then 3–10 tangential Laplacian iterations (λ 0.3–0.5) with re-projection. This removes bunching without changing shape.
- **Detail split** 🧠: d = signed distance from the Catmull-Clark L2 surface to `scan_raw`, clamped to ±3 mm. A face median |d| above 0.3 mm flags a wrap failure, not detail.
- **Texture** 🧠:
  - Per texel, cast a normal ray to `scan_raw` and sample by barycentrics.
  - Fill misses by push-pull, then dilate 16 px.
  - Photo fallback: weight solved views by cos^k θ (k = 2–4), cut off at 70–75°, depth-test, and solve per-camera gains on the overlaps.
  - Work in linear float; write sRGB only on save.
- **Benchmark:** rigid-then-per-vertex errors in mm, with landmark rates comparable to [7]. Never claim more accuracy than the scan modality (≈0.2–1 mm [8][10]).

## Disagreements, myths & open questions

- **"Shrinkwrap is a wrap."** It has no landmarks and no stiffness, so correspondence slides [1]. It is fine as the last snap.
- **Clean first or wrap first?** ↔️ The traditional VFX order fills and smooths the scan, then wraps. A growing practice wraps onto a lightly cleaned, masked target and cleans topology-aware on the base, because filled holes are invented data.
- **"Auto-retopo is enough."** ↔️ It is fine for prints. Rigging, cross-subject comparison and vendor bridges need stable loops and correspondence.
- **"More texture resolution means more likeness."** No: likeness is complete by Multires L2–L3 🧠.
- **"Symmetrise the scan to clean it."** That erases ≈0.8 mm of real asymmetry [11].
- **Open questions:**
  - Mesh to MetaHuman fidelity and texture transfer after 5.6 ↔️.
  - Faceform's current licences and prices, and ZWrap support for current ZBrush ↔️.
  - Whether Bake from Multires and Reshape are unchanged in 5.x.
  - Whether any maintained open-source Wrap-grade tool exists for Blender (none known to me).
  - Whether statistical, shape-model-regularised NICP [14] beats smoothness-only regularisers on partial scans.

## Sources

No harvest existed for this topic. Every URL is borrowed from a sibling harvest in `research/_raw/harvests/` (named in parentheses).

[1] Amberg, Romdhani, Vetter, Optimal Step Nonrigid ICP Algorithms for Surface Registration (CVPR 2007) — https://shapemodelling.cs.unibas.ch/gravis-literature/publications/2007/CVPR07_Amberg.pdf — paper — 2007 (deformation-fitting-math)
[2] Densely tracking sequences of 3D face scans — https://arxiv.org/pdf/1709.04295 — paper — 2017 (deformation-fitting-math)
[3] Face-capture paper with decreasing stiffness and landmark weights (title not recorded in the harvest) — https://arxiv.org/pdf/2003.08583 — paper — 2020 (deformation-fitting-math)
[4] Bookstein, Principal Warps: thin-plate splines and the decomposition of deformations — https://members.cbio.mines-paristech.fr/~jvert/svn/bibli/local/Bookstein1989Principal.pdf — paper — 1989 (deformation-fitting-math)
[5] BrainMorph: A Foundational Keypoint Model for Robust and Flexible Brain MRI Registration (TPS usage) — https://arxiv.org/pdf/2405.14019 — paper — 2024 (deformation-fitting-math)
[6] Sorkine & Alexa, As-Rigid-As-Possible Surface Modeling (SGP 2007) — https://diglib.eg.org/handle/10.2312/SGP.SGP07.109-116 — paper — 2007 (deformation-fitting-math)
[7] Comparison Study of Extraction Accuracy of 3D Facial Anatomical Landmarks Based on Non-Rigid Registration of Face Template — https://pmc.ncbi.nlm.nih.gov/articles/PMC10047049/ — paper — n.d. (craniometric-landmarks)
[8] Accuracy and reliability of 3D stereophotogrammetry: a comparison to direct anthropometry and 2D photogrammetry (figures from a search snippet) — https://pubmed.ncbi.nlm.nih.gov/26267357 — paper — 2015 (anthropometric-norms)
[9] Reproducibility and Accuracy of Facial Soft Tissue Landmarks Across 3D Face Scanning Modalities: Systematic Review — https://pmc.ncbi.nlm.nih.gov/articles/PMC13180338/ — paper — n.d. (anthropometric-norms)
[10] Accuracy of Facial Digitization Using a New Mobile Device-Compatible 3D Scanner for Malocclusion — https://pmc.ncbi.nlm.nih.gov/articles/PMC13117559/ — paper — n.d. (craniometric-landmarks)
[11] Facial asymmetry assessment in adults using three-dimensional surface imaging — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4614853/ — paper — 2015 (facial-asymmetry)
[12] Principled BSDF – Blender 4.3 Manual — https://docs.blender.org/manual/en/4.3/render/shader_nodes/shader/principled.html — official docs — 2024 (skin-shading)
[13] Generating metahuman based on a single image (Blender Artists) — https://blenderartists.org/t/generating-metahuman-based-on-a-single-image-blender-ue5-tutorial/1531052 — forum — n.d. (blenderartists-forum)
[14] Statistical non-rigid ICP (ibug) — https://ibug.doc.ic.ac.uk/media/uploads/documents/statistical_non_rigid_icp.pdf — paper — n.d. (deformation-fitting-math; listed, contents not harvested)

**Further reading (by name, not yet linked)**
- Faceform (R3DS) Wrap and ZWrap documentation (RigidAlignment, Wrapping, OpticalFlowWrapping, TransferTexture, BlendShapes)
- Epic Games, MetaHuman documentation (Mesh to MetaHuman, MetaHuman Identity)
- ZBrush documentation: Project All, Decimation Master, Morph Target
- Blender Manual: Shrinkwrap, Surface Deform, Laplacian Deform, Corrective Smooth, Data Transfer, Multiresolution, Geometry Nodes, Render Baking
- Allen, Curless & Popović, "The space of human body shapes", SIGGRAPH 2003
- Sumner, Schmid & Pauly, "Embedded Deformation for Shape Manipulation", SIGGRAPH 2007
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Li, Sumner & Pauly, "Global Correspondence Optimization for Non-Rigid Registration of Depth Scans", SGP 2008
- Taubin, "A Signal Processing Approach to Fair Surface Design", SIGGRAPH 1995
- Vollmer, Mencl & Müller, "Improved Laplacian Smoothing of Noisy Surface Meshes", Eurographics 1999
- Jakob et al., "Instant Field-Aligned Meshes", SIGGRAPH Asia 2015
- Huang et al., "QuadriFlow: A Scalable and Robust Method for Quadrangulation", SGP 2018
