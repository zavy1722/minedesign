# Bridges to MetaHuman, Character Creator, Daz

> MetaHuman, Character Creator (CC) and Daz Genesis are all fixed-template systems, so a Blender likeness can enter them through only two doors. One is a **vendor conform** that accepts any topology (Mesh to MetaHuman, the 5.6+ MetaHuman Creator "Conform", Reallusion Headshot mesh mode). The other is a **same-topology morph** that Blender has already wrapped onto the vendor's template, with identical vertex count and order (CC morph import, Daz Morph Loader Pro, MetaHuman template or DNA editing). The add-on should therefore export a topology-agnostic "bridge-ready neutral", plus optional per-template wraps computed locally against the user's own licensed template and never redistributed. Licences, not geometry, are the binding constraint: Epic widened MetaHuman use beyond Unreal with UE 5.6 (2025) [4][5][6], Reallusion and Daz forbid redistributing raw base meshes, and uploading a real face to a vendor cloud needs the subject's informed consent. This topic had no harvest and no earlier draft, so nearly everything here is expert knowledge awaiting verification; nothing after late 2025 is known to me.
Evidence status: 2 ✅ / 9 📄 / 60 🧠 / 12 ↔️ (after 2026-11-20 verification) — 🧠 items are queued for web verification.

## Key facts

### Shared mechanics
- **Every target is a template plus morphs.** Identity is stored as vertex positions or morph deltas on one vendor topology, and the expression rig assumes that topology 🧠.
- **"Same topology" means the same vertex count *and* order.** Index-matched importers (Daz Morph Loader Pro, CC morph/target import, DNA tools) do not fail loudly on a reordered mesh; they produce exploded faces 🧠.
- **Blender operations that reorder or recount vertices:** Join, Separate, Sort Mesh Elements, Remesh/Dyntopo/QuadriFlow, Decimate, applying Mirror or Weld, Symmetrize with merge, and exporting with "Apply Modifiers" while a Multires viewport level is above 0 🧠.
- **FBX and OBJ preserve the control-vertex list.** glTF splits vertices at UV seams and sharp normals, so it cannot carry index-matched round trips. On OBJ import, "split by object/group" breaks the mesh into pieces 🧠.
- **Units and axes** 🧠:
  - Blender: metres, Z-up, characters face −Y.
  - Unreal Engine: centimetres, Z-up, left-handed; skeletal meshes face +Y in mesh space.
  - Daz, Maya and MetaHuman DNA: centimetres, Y-up, characters face +Z.
  - Blender's default OBJ axes (Up Y, Forward −Z) already match Daz/Maya; only the ×100 scale differs.
- **Cloud processing:** the Mesh to MetaHuman autorig and MetaHuman Animator solves run partly on Epic servers and need an Epic login 🧠. A consent form should name this third-party processing. Face geometry used for identification is biometric data under the GDPR (Art. 9) and Illinois BIPA ↔️ (not legal advice).

### MetaHuman
- **Timeline** 🧠 (time-sensitive):
  - 2021: Creator launched as a cloud-streamed browser app.
  - UE 5.0 (2022): Mesh to MetaHuman arrived in the MetaHuman plugin.
  - 5.2 (2023): MetaHuman Animator, using iPhone depth or stereo head-mounted cameras.
  - 5.6 (mid-2025): Creator moved inside the engine, with parametric face and body models; the web Creator / Quixel Bridge path was retired.
  - UE 5.7 (Nov 2025) added Linux/macOS plugin support and more texture-resolution options in Creator [10] 📄.
  - MetaHuman 5.8 exists (UE 5.8 is described as the last planned major UE5 release): Mesh to MetaHuman gains full-body creation from any topology, and characters can be assembled without baked textures/materials [9] 📄 (corrected in verification: the note previously knew nothing after 5.7; the 5.8 release date was not found).
- **Mesh to MetaHuman flow** 🧠:
  1. Import a static mesh.
  2. Create a MetaHuman Identity and run "Components from Mesh".
  3. Promote a frontal neutral frame. Extra promoted angles are allowed.
  4. Track Markers. The tracker draws editable 2D curves for the brows, eyelids, lips, nose and face outline.
  5. Run the Identity Solve, which conforms the template.
  6. Optional: fit the teeth from a teeth pose.
  7. Choose a body.
  8. Run Mesh to MetaHuman, the cloud autorig that produces the DNA.
- **Input conditions** 🧠 (recalled from docs and tutorials): neutral expression, eyes open looking ahead, lips closed, an unobscured brow and forehead, real size in cm, one combined mesh. A texture (even a projected photo) and eyeball geometry noticeably improve marker tracking.
- **Likeness ceiling** ↔️:
  - Before 5.6, autorigged heads regressed toward Epic's scan database. The nose, lip shape and eyelid aperture drifted.
  - Before 5.6, source textures were not carried over; skin came from presets.
  - 5.6 claims a wider parametric range and texture synthesis. How much likeness survives is unmeasured in this library.
- **5.6+ Creator** 📄 [7][8] (corrected in verification):
  - Conform from a custom mesh/Identity, from a DNA file (Import > From DNA, with Import Whole Rig), or from a template mesh exported from your DCC as FBX (Import > From Template, back to the MetaHuman A pose). Preserved vertex order is implied, not stated, in the docs.
  - Blend, Sculpt and Move face tools.
  - Cloud Auto-Rig with a joints-only or a joints-plus-blendshapes rig 🧠 (not confirmed by the sources found).
  - "Assemble" pipelines, including a DCC Export that is a zip of head DNA, body DNA and textures (.dna, .png, .json), not FBX [7] 📄. A separate Expression Editor export writes an FBX + DNA pair (Y-up or Z-up); that DNA cannot be re-imported into Creator [7] 📄.
- **DNA** 🧠: a binary format (from 3Lateral) holding four layers:
  - descriptor;
  - definition: joints, blendshape names, controls;
  - behaviour: RigLogic maps about 250 raw `CTRL_expressions_*` controls to joints, corrective blendshapes and wrinkle-map masks;
  - geometry: 8 head LODs (LOD0–7). The head-side meshes are `head`, `teeth`, `saliva`, `eyeLeft`, `eyeRight`, `eyeshell`, `eyelashes`, `eyeEdge` and `cartilage` (`*_lod0_mesh`). LOD0 head ≈24k vertices (recalled; verify).
- **Editing a DNA's neutral mesh without moving its joints breaks deformation** 🧠. Epic's MetaHuman DNA Calibration library (Python/C++) exposes the edit commands. A community Blender DNA tool (Poly Hammer) imports and exports DNA with RigLogic evaluation ↔️ (status and licence unverified).
- **ARKit drive:** Live Link Face's ARKit mode drives MetaHumans through a mapping pose asset (`mh_arkit_mapping_pose`) 🧠. ARKit blendshapes are named coefficients from 0 to 1 [2] 📄.
- **Licence** ✅ [4][5][6]: before June 2025, MetaHumans had to be rendered in Unreal. From UE 5.6 they fall under the UE EULA, allowing use in other engines and DCCs (Blender, Maya, Houdini, Unity, Godot) and sale on Fab. Treated as non-engine products, so no 5% engine royalty outside UE; studios above US$1M revenue need seats (reported US$1,850/yr) (corrected in verification: royalty/seat terms now known, per press coverage; read the EULA for edge cases). The uploader must hold the rights to the scan and likeness 🧠.
- **MetahumanModeler** builds a MetaHuman-topology mesh from one image in Blender. Its author says it was built from their understanding of FaceBuilder; no accuracy evidence was found [1] 📄.

### Character Creator (Reallusion)
- **Base mesh** 🧠: CC4 (2021–22) and CC5 (2025, ↔️ recalled) use the "CC3+" base, one body-and-head topology for all sexes. Eyes, teeth, tongue, eye-occlusion and tear-line meshes are separate. Sliders are morphs, with SubD on top.
- **Headshot** 🧠 (v1 2020 for CC3; Headshot 2 2023 for CC4):
  - **Image mode:** one frontal photo becomes a head morph plus a projected texture. Depth and profile are guessed.
  - **Mesh mode:** an arbitrary-topology mesh is fitted after you place or auto-detect alignment points. It fits the CC head, bakes the texture, attaches to a body and comes out rigged with the CC facial profile. This is the useful door for a Blender fit.
- **Facial profiles** 🧠: CC4 has Standard and Extended. Extended adds many expression morphs plus ARKit-compatible naming (counts unverified).
- **CC/iC Blender Tools** 🧠 (add-on plus a pipeline plug-in inside CC; open source, recalled as GPL-3, author "soupday"): imports CC FBX with skin, eye and hair shaders and wrinkle maps, converts to Rigify, round-trips mesh and morph edits back to CC, and in newer versions adds a live link.
- **Same-topology return** 🧠: export from CC at SubD 0, edit in Blender keeping vertex order, and re-import as a morph (OBJ or GoZ).
- **Licence** ↔️: the base mesh and morphs may not be redistributed as raw editable assets outside an end product. Engine-bound export of some content has needed an export licence or a higher edition.

### Daz
- **Figures** 🧠: Daz Studio is free. Genesis 8/8.1 date from 2017/2020; Genesis 9 (2022) is a unified, sex-neutral topology with eyes, mouth, lashes and tear as separate figures (recalled). Base counts ≈16.5k vertices (G8) and ≈25k (G9), recalled; verify.
- **Face Transfer** 🧠: free, single frontal photo to a face morph plus texture. It is recognisable but smooth and front-biased.
- **Morph return** 🧠: export the base figure at base resolution (SubD off, no morphs dialled, zero pose). Wrap it in Blender, then import with Morph Loader Pro: vertex count, order and scale preset must match, and "Reverse deformations" handles posed sculpts. HD morphs need separate tooling, so put fine detail in normal maps.
- **Blender bridges** 🧠: the official Daz to Blender Bridge (recalled as Apache-2.0) and the community Diffeomorphic DAZ Importer (Thomas Larsson, GPL), which reads `.duf` directly with morphs and drivers. Diffeomorphic support for Blender 5.x is unverified.
- **Licence** ↔️: the Standard licence covers renders and 2D. Games and other interactive use need an Interactive Licence per product. Base figures may not be redistributed. Recent EULAs add AI/ML-use clauses.

### Blender-native and third-party
- **Faceit** generates ARKit-style, Audio2Face, tongue and phoneme shape-key sets and bakes sculpt or pose deformation into keys [3] 📄. An MPFB2 or custom head with ARKit-named keys can be exported as FBX and driven in an engine by Live Link Face, with no vendor rig 🧠.
- **R3DS Wrap** (commercial) is the de facto topology-transfer tool, with community templates for MetaHuman, CC and Daz. KeenTools FaceBuilder heads are a common Mesh to MetaHuman input 🧠.

## Numbers & reference tables

**Table 1 — Bridge targets** (vertex counts recalled; the engine must recount at runtime)

| Target | Template | Head/base verts | Units, up | Any-topology door | Same-topology door | Cloud | Licence gist | Badge |
|---|---|---|---|---|---|---|---|---|
| MetaHuman (UE 5.6+) | DNA head, LOD0–7 | ≈24k (LOD0 head) | cm; Z-up in UE, Y-up in DNA | Mesh to MetaHuman / Conform | template conform, DNA edit | autorig | UE EULA; outside-UE since 5.6 | ↔️ |
| Character Creator 4/5 | CC3+ base | order 10⁴ | cm | Headshot mesh mode | morph import / GoZ | no | no raw redistribution | 🧠 |
| Daz Genesis 9 | unified G9 | ≈25k | cm, Y-up | none first-party | Morph Loader Pro | no | Standard vs Interactive | 🧠 |
| Daz Genesis 8/8.1 | G8 | ≈16.5k | cm, Y-up | Face Transfer (photo only) | Morph Loader Pro | no | Standard vs Interactive | 🧠 |
| MPFB2 (Blender) | hm08 | ≈13.4k body | m | own fitter | shape key / `.target` | no | GPL code, CC0 base | 🧠 |

**Table 2 — Converting from Blender (m, Z-up, faces −Y)**

| Target | Scale | Target (x, y, z) from Blender (x, y, z) | How | Badge |
|---|---|---|---|---|
| Daz / Maya / DNA | ×100 | (x, z, −y) | OBJ Up = Y, Forward = −Z, scale 100; or FBX | 🧠 |
| Unreal Engine | ×100 | (x, −y, z): a head facing −Y faces UE +Y | FBX, unit scale 1.0, transforms applied | 🧠 |
| Character Creator | ×100 | let FBX carry the axes | CC Blender Tools export presets | 🧠 |

**Table 3 — Post-import scale sanity checks** (adults, cm; anthropometric ranges, see `anatomy/` notes)

| Measure | Typical adult range | Badge |
|---|---|---|
| Interpupillary distance | 5.5–7.0 (mean ≈6.3); ≈0.063 or ≈630 means a ×100 error | 🧠 |
| Head height, vertex–menton | 21–25 | 🧠 |
| Head breadth, eu–eu | 14–16.5 | 🧠 |
| Bizygomatic width | 12–15 | 🧠 |
| Eyeball axial length | 2.2–2.5 (template eye radius ≈1.2) | 🧠 |
| Visible iris diameter | 1.1–1.25 (≈1.17) | 🧠 |

**Table 4 — Interchange formats and topology**

| Format | Vertex count/order | Shape keys | Unit/axis metadata | Use | Badge |
|---|---|---|---|---|---|
| OBJ | kept if modifiers are off or Multires is at 0, and no split on import | no | none; bake them | Morph Loader, CC morph, M2MH input | 🧠 |
| FBX | kept (control points) | yes | yes | CC, UE, Daz bridges, M2MH | 🧠 |
| glTF | split at UV seams and sharp edges | yes, on split vertices | m, Y-up | viewing only | 🧠 |
| USD | points kept | supported; DCC coverage uneven | metersPerUnit, upAxis | emerging | ↔️ |
| DNA | own layout per LOD | correctives | cm | MetaHuman DNA tools only | 🧠 |

**Table 5 — Suggested wrap and export defaults** (design choices, not measurements) 🧠

| Parameter | Default |
|---|---|
| Rigid alignment | Umeyama similarity on ≥8 anchors; reject scale outside 0.8–1.25 of the expected value |
| Anchor σ (canthi, cheilion, pronasale, subnasale, gnathion) | 1.0 mm |
| Contour σ (lid margins, vermilion border, brows) | 1.5–2 mm, points slide along the curve |
| NRICP stiffness schedule | 100 → 50 → 20 → 10 → 5 → 2 (relative to the data term) |
| Correspondence rejection | distance > 8 mm or normal angle > 60° |
| Protected-zone stiffness | ×5 on eyelids, lips, nostrils and ears |
| Eyeball radius prior | 12.0 ± 0.5 mm |
| Wrap acceptance | face RMS < 0.5 mm, scalp/neck < 1.5 mm; no flipped triangles or area ratio < 0.2 |
| Bridge texture | 4096² projected-photo albedo (for tracking, not final skin) |

## Applying this to photo→3D face sculpting in Blender

1. **Pick the destination before fitting.**
   - MetaHuman for the best facial rig.
   - CC for a fast full-body rig with Blender round-trips.
   - Daz for a render library.
   - Native (MPFB2 + Faceit ARKit keys [3]) to keep full likeness control and a clean licence.
2. **Build the bridge-ready neutral** 🧠:
   - Remove photo expression with the fitter's expression basis; even a slight smile becomes identity.
   - Lips closed, eyes open, gaze forward.
   - Sphere eyeballs (radius ≈12 mm) with an iris texture.
   - Keep the neck; remove hair cards and the hair bulk above the brow line.
   - One mesh with transforms applied, at real scale, checked against Table 3.
   - Baked projected-photo albedo.
3. **Mesh to MetaHuman** 🧠:
   - Export FBX (unit scale 1.0, no shape keys, modifiers off) and import it into UE as a combined static mesh.
   - Promote a frontal frame, plus a ¾ frame if the profile matters.
   - Inspect the eyelid and lip-line curves before solving. They are the usual failure, and a misplaced lid curve distorts every expression.
   - Solve, add the teeth pose if teeth are visible, pick the body, autorig.
4. **Audit the likeness.** Bring the head back with the 5.6+ DCC export, align it rigidly to your fit and colour-map the signed distance. Expect drift at the nasal tip and alae, the vermilion shape, the lid aperture and the jaw angle ↔️. Correct it in Creator or through step 5, never by editing the DNA mesh alone.
5. **Template-conform route** (5.6+, 📄 [8]): wrap your fit onto the exported MetaHuman LOD0 head, keeping vertex order. Re-import it and conform in Creator so the autorig rebuilds the joints and correctives.
6. **CC route** 🧠: run Headshot mesh mode on the same neutral, with alignment points on the canthi and mouth corners. Alternatively, export the CC base at SubD 0 through CC Blender Tools, wrap, and re-import as a morph.
7. **Daz route** 🧠: export the G9 base OBJ at base resolution with the Blender preset. Wrap in Blender, export the OBJ with Up Y and Forward −Z, then load it with Morph Loader Pro using the same preset.
8. **What goes wrong** 🧠:
   - a 100× scale error;
   - the head facing the wrong way in the Identity view;
   - eyes fused to the lids;
   - parted lips that the tracker reads as the lip line;
   - asymmetry flattened by a symmetric template;
   - vendor eyeballs deeper or shallower than the fitted lids;
   - a DNA neutral edited while the joints stay put;
   - a vendor head shipped in a public repo.

## Algorithmic implications

- **Bridge profiles as data** 🧠: `{name, units_per_m: 100, up, forward, handedness, template_vcount, template_topology_hash, door: conform|same_topology, cloud, redistribute_template: false, commercial_ok}`. An unknown licence field blocks export by default.
- **Topology hash** 🧠: hash the user's template face-index arrays (not positions) and refuse write-back on mismatch.
- **Correspondence packs**: landmark → (triangle id, barycentric) per template, generated locally from the user's licensed copy. Ship the generator, not vendor indices or geometry ↔️ (whether index lists are protectable is unclear).
- **Wrap pipeline** (Table 5) 🧠:
  1. Umeyama similarity.
  2. Thin-plate-spline landmark warp.
  3. NRICP (Amberg 2007) with annealed stiffness and landmark terms.
  4. Normal-ray projection.
  5. Laplacian relaxation outside protected zones.
  Use a soft symmetry prior (σ ≈ 1–2 mm), never hard mirroring.
- **Eye-socket constraint** 🧠: place the vendor eyeball centre from the canthi and lid margins (radius 12 ± 0.5 mm). Penalise lid–globe gaps above 0.5 mm, because vendor rigs slide the lids on the globe.
- **Neutralise before export:** fit an ARKit-named expression basis (σ ≈ 0.3 on the 0–1 range [2]), then discard it, so only identity is exported 🧠.
- **Axes in code** 🧠: apply the Table 2 matrices for OBJ. For FBX, trust the metadata but check a test import against Table 3.
- **One likeness metric for every route** 🧠: landmark RMS in mm, per-region surface RMS and profile-silhouette error, logged before and after each vendor step to quantify drift.
- **Expressions for non-vendor heads** 🧠: generate ARKit keys by deformation transfer (Sumner & Popović 2004) from a rig you are licensed to use, or with Faceit [3].
- **Never train or ship priors on vendor meshes** 🧠: use MPFB2 (CC0 base) and MIT-licensed models only.

## Disagreements, myths & open questions

- **"Mesh to MetaHuman preserves the scan."** It conforms a template and then autorigs from a database. Community drift reports are consistent; 5.6's gains are unmeasured ↔️.
- **"MetaHumans cannot leave Unreal."** That was true before 2025. 5.6 allows other engines and DCCs under the UE EULA ✅ [4][5][6].
- **"Same vertex count is enough."** The order must match too 🧠.
- **"Headshot from one photo is a likeness."** Depth and profile are inferred; mesh mode fed by a multi-view fit is stronger 🧠.
- **"Free software means free base meshes."** Daz Studio is free, but Genesis redistribution is not; the same holds for CC ↔️.
- **Open questions:**
  - the 5.8 release date and whether Mesh to MetaHuman transfers source textures (unconfirmed);
  - the LOD0 head, CC3+ and G9 vertex counts;
  - the CC5 and Headshot versions;
  - Face Transfer status on G9;
  - the status and licence of Poly Hammer's DNA tool and of Diffeomorphic on Blender 5.x;
  - whether Mesh to MetaHuman now transfers source textures;
  - an mm-level likeness benchmark for any vendor route.

## Sources

[1] Generating metahuman based on a single image blender ue5 tutorial (Blender Artists) — https://blenderartists.org/t/generating-metahuman-based-on-a-single-image-blender-ue5-tutorial/1531052 — forum — n.d. (from the blenderartists-forum harvest)
[2] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d. (from the facs-expressions harvest)
[3] Faceit: Facial Expressions and Performance Capture (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d. (from the blender-face-addons harvest)
[4] CG Channel, "You can now sell MetaHumans or use them in Unity or Godot" — https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/ — trade press — 2025-06-04
[5] Digital Production, "MetaHumans Graduate: Ready for Unity, Godot, and the Fab Cash Register" — https://digitalproduction.com/2025/06/05/metahumans-graduate-ready-for-unity-godot-and-the-fab-cash-register/ — trade press — 2025-06-05
[6] MetaHuman licence page — https://www.metahuman.com/license — official — n.d.
[7] Epic, MetaHuman Creator Export Tool / Saving and Exporting Data — https://dev.epicgames.com/documentation/metahuman/saving-and-exporting-data — official docs — n.d.
[8] Epic, MetaHuman Creator From Custom Mesh Tool — https://dev.epicgames.com/documentation/metahuman/metahuman-creator-from-custom-mesh-tool-in-unreal-engine — official docs — n.d.
[9] Epic, MetaHuman 5.8 release notes — https://dev.epicgames.com/documentation/metahuman/metahuman-5-8-release-notes-in-unreal-engine — official docs — 2026
[10] Epic, MetaHuman 5.7 release notes — https://dev.epicgames.com/documentation/metahuman/metahuman-5-7-release-notes — official docs — 2025

**Further reading (by name, not yet linked)**
- Epic Games, MetaHuman documentation (Mesh to MetaHuman, MetaHuman Identity, MetaHuman Creator in UE 5.6+) and the Unreal Engine EULA / MetaHuman licence FAQ
- Epic Games, MetaHuman DNA Calibration library (GitHub, EpicGames organisation)
- Reallusion, Character Creator 4 and Headshot 2 manuals; Reallusion EULA
- CC/iC Blender Tools and CC/iC Blender Pipeline (soupday, GitHub)
- Daz 3D, Daz Studio documentation (Morph Loader Pro, Face Transfer); Daz 3D EULA and Interactive License
- Daz to Blender Bridge (daz3d, GitHub); Diffeomorphic DAZ Importer documentation (Thomas Larsson)
- R3DS Wrap documentation
- Amberg, Romdhani, Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007
- Umeyama, "Least-Squares Estimation of Transformation Parameters Between Two Point Patterns", IEEE TPAMI 1991
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Bookstein, "Principal Warps: Thin-Plate Splines and the Decomposition of Deformations", IEEE TPAMI 1989
- Farkas, *Anthropometry of the Head and Face*, 2nd ed., 1994

## Verification log (2026-11-20)

- **MetaHuman licence from UE 5.6 (UE EULA, other engines/DCCs, Fab sales)**: confirmed (✅, two press sources plus Epic licence page). Added: no engine royalty as non-engine products; seats for studios over US$1M revenue (reported US$1,850/yr). Sources: https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/ ; https://digitalproduction.com/2025/06/05/metahumans-graduate-ready-for-unity-godot-and-the-fab-cash-register/ ; https://www.metahuman.com/license
- **Creator 5.6+ conform / DNA / auto-rig / DCC export**: corrected. Conform from DNA and from a DCC template mesh (From Template) confirmed; DCC Export is a zip of head DNA, body DNA and textures, not FBX (FBX + DNA is the Expression Editor export). Joints-only vs joints-plus-blendshapes auto-rig: unconfirmed. Vertex-order preservation implied, not stated. Sources: https://dev.epicgames.com/documentation/metahuman/saving-and-exporting-data ; https://dev.epicgames.com/documentation/metahuman/metahuman-creator-from-custom-mesh-tool-in-unreal-engine
- **Current UE/MetaHuman version after 5.7; Mesh to MetaHuman textures/likeness**: corrected/partly unconfirmed. MetaHuman 5.8 exists (last planned major UE5 release); Mesh to MetaHuman does full-body from any topology; no-baked-texture assembly. Source texture transfer by Mesh to MetaHuman and likeness retention: unconfirmed; release date of 5.8 not found. Sources: https://dev.epicgames.com/documentation/metahuman/metahuman-5-8-release-notes-in-unreal-engine ; https://dev.epicgames.com/documentation/metahuman/metahuman-5-7-release-notes
- **Template vertex counts (MetaHuman LOD0 head ~24k, G9 ~25k, G8 ~16.5k, CC3+)**: unconfirmed. Only forum posts of ~34.6k total vertices per MetaHuman (ambiguous, not head-only); nothing found for Daz or CC. Left as recalled (🧠).
