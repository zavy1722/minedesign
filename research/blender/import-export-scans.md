# Importing scans and reconstructions into Blender

> Face scans (structured light, stereophotogrammetry, phone LiDAR or photogrammetry) and 3DMM outputs (FLAME, BFM, MediaPipe, DECA/MICA-style regressors) reach Blender in formats that disagree on units, axes, colour encoding and whether vertex order survives. Most likeness failures at this stage are silent ones: a ×10 to ×1000 unit error, a wrong axis or a mirror image, or broken vertex correspondence. Treat every import as an unknown similarity transform plus a possible reflection. Infer the units from one face measurement and the orientation from landmarks, and record the transform in a sidecar file. Clean and decimate the scan into a fitting target. Bring the template onto it with a landmark-anchored, coarse-to-fine non-rigid fit (Wrap/NICP style) rather than plain Shrinkwrap, and never pass the template that carries the likeness through anything that rebuilds topology. Clinical 3D surface imaging agrees with direct measurement to within about 2 mm [9][10], so a correctly imported scan is valid ground truth.
>
> Evidence status: 6 ✅ / 19 📄 / 57 🧠 / 5 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Importers and formats**
- OBJ, PLY and STL use C++ operators (`wm.obj_import`, `wm.ply_import`, `wm.stl_import`). The legacy Python OBJ and PLY add-ons (`import_scene.obj`, `import_mesh.ply`) were removed in 4.0, so older scripts fail [25] 📄. The legacy STL add-on (`import_mesh.stl`) was only marked legacy in 4.1, not removed in 4.0 [26] 📄 (corrected in verification). The C++ OBJ importer arrived in 3.3 [27] 📄, and the PLY and STL importers in 3.6 🧠.
- FBX (`import_scene.fbx`) and glTF 2.0 (Khronos glTF-Blender-IO) are still bundled Python add-ons. USD and Alembic are built in 🧠. COLLADA was removed in 5.0 🧠 (see `blender-version-status-2026.md`).
- **Vertex order:**
  - A single-mesh OBJ, PLY, FBX, USD or Alembic import keeps the file's vertex order, and template correspondence (FLAME, MPFB) depends on that 🧠.
  - **glTF does not.** Each vertex carries one attribute set, so every UV seam or hard edge duplicates vertices [28]. Enabling "Merge Vertices" on import [29] then renumbers them 📄.
  - OBJ "Split by Object/Group" also renumbers 🧠.
- **Colour:** OBJ import reads the unofficial `v x y z r g b` extension and ZBrush `#MRGB` (3.5+; one source suggests the support landed in 3.3 [30], unresolved) 🧠 (moderate); PLY import reads uchar `red/green/blue[/alpha]` 🧠.
- **Precision:** OBJ export writes 6 decimals (1 µm at 1 BU = 1 m) 🧠; binary formats keep float32; since 5.0 mathutils hands NumPy float32 views [14] 📄.

**Units and scale**
- OBJ, PLY and STL store no units. FBX stores a unit-scale factor (often cm). glTF mandates metres. USD carries `metersPerUnit` and `upAxis` 🧠.
- At Unit Scale 1.0, 1 BU = 1 m. Camera sensor and lens are always in mm [16] 📄.
- Voxel size, merge distance, Shrinkwrap offset/limit and bake ray distance are measured in the object's **local** units. An unapplied object scale of 0.001 silently multiplies them all by 1000 🧠.
- FLAME is in metres (5,023 vertices, 9,976 triangles) 🧠. MICA predicts a *metrical* FLAME shape [5] 📄. DECA-type regressors give unconstrained scale; in the MICA paper, scale optimisation alone cuts the average FLAME mesh's NoW error from 1.92 to 1.53 mm [5] 📄. Table 2 gives the other sources.
- FLAME must be downloaded separately under its own licence [24]. VHAP uses FLAME 2023 plus vertex masks [23] 📄.
- Adult intercanthal width spans only ≈31–41 mm across three populations [20][21][22] ✅, while unit errors are factors of 10 or more. One face measurement therefore settles the units.

**Axes and handedness**
- **Blender** is right-handed and Z-up, and its front view looks along +Y, so a character faces −Y. **glTF** is Y-up with the asset's front toward +Z. **FLAME** is Y-up, with the face toward +Z and +X toward the subject's left 🧠.
- OBJ has no axis in its spec. Blender's OBJ defaults (Forward −Z, Up Y) map FLAME upright and facing −Y: (x, y, z) → (x, −z, y), a +90° rotation about X. Exporting with the same defaults inverts the map exactly 🧠.
- OBJ and PLY bake the axis change into the vertices. FBX usually puts the 90° rotation and the unit scale on the object instead 🧠 (moderate).
- Unreal (left-handed, Z-up, cm), Unity (left-handed, Y-up, m) and any axis swap without a sign flip all mirror the mesh 🧠. **A mirrored face still looks like a face** but transposes every asymmetry. Healthy faces deviate from their mirror image by 0.80 ± 0.24 mm RMS [12] 📄.
- The OpenCV camera (x right, y down, z forward) equals the Blender camera × diag(1, −1, −1) 🧠.

**Vertex colours**
- Since 3.2, Color Attributes have a domain (Point or Face Corner) and a type: Byte (8-bit, stored as sRGB) or Float (linear). Scanner PLY colour is 8-bit sRGB, and the shader's Color Attribute node returns linear values 🧠.
- Colour resolution equals vertex spacing, ≈1 mm on a 200k-vertex head, so bake to an image or transfer it to the template with Data Transfer 🧠.

**Cleaning and remeshing**
- Typical defects: an open neck cut; holes at nostrils, under the chin, ear canals and specular eyes; floating islands; lash and stubble spikes; and **hair captured as a shell over the scalp**, inflating cranial size by millimetres to centimetres 🧠.
- Random-walk SSS misbehaves on open or overlapping meshes [13] 📄, so renders for photo-matching need a closed mesh.
- Voxel remesh (OpenVDB) builds new watertight topology. On an open scan it makes a thin double-walled shell instead of filling the holes. It loses UVs; its toggles can preserve colour, face sets and masks 🧠.
- Sculpt → Edit Face Set → **Fair Positions / Fair Tangency** (2.93+) blends a filled hole in smoothly 🧠 (moderate).

**Template fitting inside Blender**
- **Shrinkwrap** (Nearest Surface Point, Project with a Limit, Nearest Vertex, Target Normal Project; snap modes, offset, vertex-group mask) projects each vertex independently with no regulariser: vertices slide off landmarks, lips and lids collapse onto one sheet, spacing bunches 🧠.
- **Surface Deform** binds a mesh to a target surface and passes on the target's later deformation. The target must have no edge shared by more than two faces and no concave polygons, and its vertex count must not change after binding. Falloff defaults to 4 🧠.
- **Laplacian Deform** (an anchor vertex group moved by hooks) and ARAP energies [2] keep detail while landmarks move 📄. TPS is a closed-form landmark warp; for noisy landmarks, regularise it with K + λI [3][4] ✅.
- **Non-rigid ICP** lowers stiffness step by step, from global to local deformation. Black-box optimisers fail on incomplete surfaces [1] 📄. Automatic template registration on optical face scans placed 53.1 % of landmarks within 2 mm and 84.4 % within 4 mm [7] 📄.
- **Multires → Reshape** copies positions from an object with the same topology into the current multires level. This puts scan detail onto a subdivided template without touching the base mesh 🧠.
- The commercial benchmark is R3DS Wrap, reportedly rebranded Faceform ↔️. Its workflow is point-pair rigid alignment, then coarse-to-fine wrapping with control points, then texture and blendshape transfer 🧠.
- The NoW benchmark aligns rigidly on 7 landmarks, then reports per-vertex scan-to-mesh error in mm [5][6] ✅. Reuse this protocol for internal validation.

## Numbers & reference tables

**Table 1 – Formats as imported by Blender 4.x–5.x**

| Format | Units stored | Axes | Vertex colour | Shape keys | Vertex order kept | Badge |
|---|---|---|---|---|---|---|
| OBJ | none | none; Y-up by convention | `v xyz rgb`, MRGB | no | yes (single object) | 🧠 |
| PLY | none (scanners: mm) | none | uchar/float RGB(A) | no | yes | 🧠 |
| STL | none (de facto mm) | none | no | no | no (welded triangle soup) | 🧠 |
| FBX | unit-scale factor (often cm) | header metadata | yes | yes | usually | 🧠 |
| glTF/GLB | metres | Y-up, front +Z | COLOR_0 (linear) | morph targets | **no** (seams split) | 🧠 |
| USD/USDZ | `metersPerUnit` | `upAxis` | `displayColor` | partial | usually | ↔️ (changes fast in 4.x–5.x) |
| Alembic | none (assume m) | Y-up | yes | per-frame cache | yes | 🧠 |

**Table 2 – Native units of common inputs**

| Source | Units / frame | Factor to 1 BU = 1 m | Badge |
|---|---|---|---|
| FLAME 2020/2023 | m; Y-up, face +Z | 1, then +90° about X | 🧠 |
| MICA | metric FLAME | 1 | 📄 [5] |
| DECA-type regressors | FLAME space, free scale | solve | 🧠 |
| BFM 2009 / 2017 | 2009 .mat µm, 2009 .h5 mm; 2017 mm [31] | 1e-6 (.mat) or 1e-3 (.h5) / 1e-3 | ↔️ |
| MakeHuman / MPFB base mesh | dm | 0.1 | 🧠 |
| MediaPipe canonical/metric face | cm | 0.01 | ↔️ |
| ARKit face mesh (1,220 vertices) | m; Y-up | 1 | 🧠 |
| 3DDFA-style image-space mesh | pixels, y down | solve; flip y and z | 🧠 |
| Structured-light / clinical scanners | mm | 0.001 | 🧠 |
| SfM (COLMAP, Meshroom, Metashape, RealityCapture) | arbitrary unless scale bars or GCPs used; often y-down | solve | 🧠 |
| Phone LiDAR / ARKit-posed apps | ≈ m (glTF/USDZ) | 1 (check) | 🧠 |

**Table 3 – Unit sanity checks (adults)**

| Measure | Value | Badge |
|---|---|---|
| Intercanthal width (en–en) | 32.5/31.8 mm Kosovo-Albanian M/F [21]; 35.7/35.0 mm Malay [20]; 40.6/38.3 mm Hong Kong Chinese [22] | ✅ (range 31–41 mm) |
| Interpupillary distance | ≈54–74 mm, mean ≈63 mm | 🧠 |
| Biocular width (ex–ex) | ≈85–100 mm | 🧠 |
| How an IPD of 63 mm reads in each unit | 0.063 m, 0.63 dm, 6.3 cm, 63 mm, 63,000 µm | 🧠 (arithmetic) |

**Table 4 – Blender defaults vs suggested settings for a head (1 BU = 1 m)**

| Setting | Default | Suggested | Badge |
|---|---|---|---|
| Merge by Distance | 0.0001 m | 1e-5–5e-5 m, only for seam duplicates | 🧠 |
| Voxel remesh size | 0.1 m | 0.5–1.5 mm | 🧠 |
| Viewport clip start / end | 0.01 / 1000 m | 0.001 / 10 m | 🧠 |
| Shrinkwrap Project limit | 0 (off) | 2–5 mm, after the landmark warp | 🧠 |
| Bake extrusion / max ray distance | 0 / 0 | 1–3 mm / 5–10 mm | 🧠 |

**Table 5 – Mesh budgets and reference accuracy**

| Item | Value | Badge |
|---|---|---|
| Raw scan → sculpt reference → fitting target | 1–20 M → 0.2–1 M → 50–200k triangles | 🧠 |
| FLAME / BFM 2009 | 5,023 / 53,490 vertices | 🧠 |
| MediaPipe Face Mesh | 468 points; 478 with refinement [17][18] | ✅ |
| Stereophotogrammetry vs direct measurement | mean difference 0.21 mm (2D photogrammetry 0.30 mm) [9]; most differences < 2 mm [10] | ✅ |
| Mobile-device 3D scanner | ≈1 mm landmark error [8] | 📄 |
| CT vs 3dMD, gonion–gonion | CT reads 2.34 mm larger [11] | 📄 |
| Automatic template registration | 53.1 % of landmarks < 2 mm, 84.4 % < 4 mm [7] | 📄 |

## Applying this to photo→3D face sculpting in Blender

1. **Scene:** Metric, Unit Scale 1.0 and Length = Millimetres, so values display in mm while 1 BU stays 1 m. Set clip start to 1 mm. Use one LTS build per job; 5.2 LTS is supported until Jul 2028 [15].
2. **Import explicitly:** FLAME OBJ with default axes (assert 5,023 vertices); scanner OBJ/PLY with Scale 0.001; phone glTF/USDZ, then read dimensions; FBX, then inspect object rotation/scale (90°, 0.01, 100).
3. **Apply rotation and scale** with Ctrl+A at once, so the thresholds in Table 4 mean what they say.
4. **Measure:** intercanthal ≈30–42 mm, ex–ex ≈85–100 mm. Off by ~10×: wrong units. Off by 20–40 %: a non-metric SfM or regressor scale.
5. **Mirror check:** compare one obvious asymmetry (parting, a mole, deviation of the nasal tip) against an unflipped photo. Selfie previews are mirrored, and some phones save mirrored files 🧠.
6. **Clean on a copy:** lock `scan_raw`; on `scan_target` delete islands under ~1 % of vertices, run Degenerate Dissolve, find holes with Select Non-Manifold, Fill Holes for small ones, Grid Fill the neck, then Fair Tangency. Keep the hair cap but give it a low vertex-group weight.
7. **Decimate** with Collapse: triangulate, symmetry off, and use a vertex group to protect the lids, lips, alae and ears.
8. **Fit:**
   1. landmarks on both meshes;
   2. similarity Procrustes;
   3. landmark warp (TPS, or Laplacian Deform with hooks);
   4. masked NICP, or several Target Normal Project Shrinkwrap passes (Limit 2–5 mm) with Corrective Smooth between them;
   5. store the result as a shape key;
   6. add Multires at levels 2–3, then Reshape from a full-resolution shrinkwrapped duplicate;
   7. bake normal/displacement and colour from `scan_raw`.
9. **Export:** OBJ with the default axes, Apply Modifiers off, no triangulation. Re-import it and assert max |Δ| < 2 µm.

**What goes wrong:** mm read as metres (1000× head, endless remesh); a ×100 FBX scale hidden on the object; glTF adding seam vertices; a mirrored likeness unnoticed for weeks; the hair shell fitted as skull; Shrinkwrap fusing the lips; sRGB applied twice; dyntopo or remesh destroying shape keys.

## Algorithmic implications

- **ImportRecord sidecar** per mesh (never bake a transform silently): format and file hash, declared and inferred units, axis matrix, reflection flag, s/R/t, vertex count and an order checksum.
- **Own readers:** minimal NumPy OBJ and PLY parsers guarantee vertex order and let tests run without Blender. Inside Blender, read with `foreach_get` (float32) and solve in float64 [14].
- **Unit inference:** from a landmark distance d (en–en or ex–ex), pick u ∈ {1e-6, 1e-3, 1e-2, 1e-1, 1} minimising |log(d·u/d_ref)|. Accept if the result is within ±30 %, otherwise flag it. Candidate units are at least 10× apart, while populations spread ≈±15 % [20][21][22].
- **Orientation:**
  - build a head frame from the eyes, nose tip and chin;
  - run Umeyama with det(R) = +1, and again with reflection allowed;
  - if the reflected RMS is less than half the proper RMS, flag "mirrored source"; never auto-flip.
- **Scale prior** (log-normal) 🧠:

  | Source | σ |
  |---|---|
  | Clinical / structured light | 0.5–1 % |
  | Phone LiDAR | 2–3 % |
  | SfM | free |
  | Metrical regressor such as MICA [5] | ≈3 % |
  | Non-metric regressor, centred on the population mean | 5–7 % |

- **Rigid gate:** after 7-landmark alignment [5][6], an RMS of 2–5 mm is normal. Above 10 mm, suspect the landmarks or the axes 🧠.
- **NICP schedule** [1]: stiffness α ∈ {100, 50, 20, 10, 5, 2, 1}, normalised by mean edge length. Landmark weight β goes from 1 down to 0.05. Run 3–10 correspondence iterations per stage 🧠.
- **Rejection rules:** drop a pair if its distance exceeds max(3·MAD, 5 mm), if the normals differ by more than 60°, or if the target point lies on a scan boundary 🧠.
- **Region weights** (FLAME-style masks [23]) 🧠: eyeballs, mouth and nostril interiors 0; scalp under hair 0.1; ears 0.3–0.5; face 1.
- **Accuracy targets:** median distance to the scan over the face below 0.5 mm, and most landmarks within 2 mm [7]. Never claim better than the reference modality (≈0.2–1 mm [8][9]).
- **Queries:** use `mathutils.bvhtree.BVHTree` and `mathutils.kdtree`, since SciPy is not bundled. With 5k vertices × 50 iterations, the Python call overhead is about 1 s 🧠.
- **Output:** a "likeness" shape key (`from_mix=False`), plus colour as a linear Float attribute on the Point domain.
- **Licences:** MPFB code is GPL and its assets CC0/CC-BY [19]; FLAME files are downloaded separately [24]. Load user-supplied model files rather than bundling them 📄.

## Disagreements, myths & open questions

- **Unit Scale 0.001 vs 1 BU = 1 m** ↔️. 3D-printing users prefer mm units. Keep metres and display mm, because glTF, USD and the bake/physics defaults assume metres 🧠.
- **Myth: "Shrinkwrap is Wrap."** Shrinkwrap has no regulariser and no landmarks, so correspondence slides; NICP-style fitting adds stiffness and landmark terms [1].
- **Myth: "glTF round-trips a template."** Seam splits change the vertex count.
- **Myth: "Voxel remesh fills holes."** On open scans it makes a shell.
- **Symmetrising a scan** erases the ≈0.8 mm of real asymmetry [12]. Symmetrise the topology, never the likeness.
- **Contested or time-sensitive:** BFM and MediaPipe units; Wrap/Faceform naming, licence and price; 5.x USD unit handling; whether 5.x imports Gaussian-splat PLYs as more than point attributes.
- **Open questions:** Does the 5.x OBJ importer keep vertex order under every option? Does PLY import read custom vertex properties? Does Surface Deform stay interactive on 1 M+ triangle targets?

## Sources

All URLs come from sibling harvests in `research/_raw/harvests/` (named in parentheses), because this topic's own harvest did not exist.

[1] Amberg, Romdhani, Vetter, Optimal Step Nonrigid ICP Algorithms for Surface Registration (CVPR 2007) — https://shapemodelling.cs.unibas.ch/gravis-literature/publications/2007/CVPR07_Amberg.pdf — paper — 2007 (deformation-fitting-math)
[2] Sorkine & Alexa, As-Rigid-As-Possible Surface Modeling (SGP 2007) — https://diglib.eg.org/handle/10.2312/SGP.SGP07.109-116 — paper — 2007 (deformation-fitting-math)
[3] Bookstein, Principal Warps: thin-plate splines and the decomposition of deformations — https://members.cbio.mines-paristech.fr/~jvert/svn/bibli/local/Bookstein1989Principal.pdf — paper — 1989 (deformation-fitting-math)
[4] BrainMorph: A Foundational Keypoint Model for Robust and Flexible Brain MRI Registration (TPS usage) — https://arxiv.org/pdf/2405.14019 — paper — 2024 (deformation-fitting-math)
[5] Towards Metrical Reconstruction of Human Faces (MICA) — https://ar5iv.labs.arxiv.org/html/2204.06607 — paper — 2022 (single-image-regression)
[6] Towards Realistic Generative 3D Face Models — https://arxiv.org/pdf/2304.12483 — paper — 2023 (single-image-regression)
[7] Comparison Study of Extraction Accuracy of 3D Facial Anatomical Landmarks Based on Non-Rigid Registration of Face Template — https://pmc.ncbi.nlm.nih.gov/articles/PMC10047049/ — paper — n.d. (craniometric-landmarks)
[8] Accuracy of Facial Digitization Using a New Mobile Device-Compatible 3D Scanner for Malocclusion — https://pmc.ncbi.nlm.nih.gov/articles/PMC13117559/ — paper — n.d. (craniometric-landmarks)
[9] Accuracy and reliability of 3D stereophotogrammetry: a comparison to direct anthropometry and 2D photogrammetry — https://pubmed.ncbi.nlm.nih.gov/26267357 — paper — 2015 (anthropometric-norms)
[10] Reproducibility and Accuracy of Facial Soft Tissue Landmarks Across 3D Face Scanning Modalities: Systematic Review — https://pmc.ncbi.nlm.nih.gov/articles/PMC13180338/ — paper — n.d. (anthropometric-norms)
[11] Three-Dimensional Anthropometric Facial Analysis and Fitting Discrepancies Between Stereophotogrammetry and CT — https://pubmed.ncbi.nlm.nih.gov/38896864 — paper — 2024 (anthropometric-norms)
[12] Facial asymmetry assessment in adults using three-dimensional surface imaging — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4614853/ — paper — 2015 (facial-asymmetry)
[13] Principled BSDF – Blender 4.3 Manual — https://docs.blender.org/manual/en/4.3/render/shader_nodes/shader/principled.html — official-docs — 2024 (skin-shading)
[14] Blender 5.0: Python API — https://developer.blender.org/docs/release_notes/5.0/python_api/ — official-docs — 2025 (blender-version-status-2026)
[15] 5.2 LTS — Blender — https://www.blender.org/download/releases/5-2/ — official-docs — 2026 (blender-version-status-2026)
[16] Cameras – Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/cameras.html — official-docs — 2026 (reference-camera-setup)
[17] MediaPipe Face Mesh (legacy docs) — https://mediapipe.readthedocs.io/en/latest/solutions/face_mesh.html — official-docs — n.d. (blender-face-addons)
[18] MediaPipe Face Mesh: All 478 Landmark Points (DEV Community) — https://dev.to/metsander/mediapipe-face-mesh-all-478-landmark-points-5ec8 — blog — n.d. (blender-face-addons)
[19] MPFB, Blender Extensions listing — https://extensions.blender.org/add-ons/mpfb/ — official listing — n.d. (blender-face-addons)
[20] Anthropometric Study of Three-Dimensional Facial Morphology in Malay Adults — https://pmc.ncbi.nlm.nih.gov/articles/PMC5051712/ — paper — n.d. (anthropometric-norms)
[21] Facial Anthropometric Norms among Kosovo-Albanian Adults — https://pmc.ncbi.nlm.nih.gov/articles/PMC5708327/ — paper — 2017 (anthropometric-norms)
[22] Normative Findings for Periocular Anthropometric Measurements among Chinese Young Adults in Hong Kong — https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3730197/ — paper — n.d. (anthropometric-norms)
[23] VHAP (Versatile Head Alignment with Adaptive Appearance Priors) — https://github.com/ShenhanQian/VHAP — repo — n.d. (multi-view-fitting)
[24] PeizhiYan flame-head-tracker — https://github.com/peizhiyan/flame-head-tracker — repo — 2025 (multi-view-fitting)
[25] Blender 4.0: Python API (release notes) — https://wiki.blender.org/release_notes/4.0/python_api/ — official-docs — 2023 (verification)
[26] Pipeline, Assets & I/O, Blender 4.1 release notes — https://developer.blender.org/docs/release_notes/4.1/pipeline_assets_io/ — official-docs — 2024 (verification)
[27] Pipeline, Assets & I/O, Blender 3.3 release notes — https://developer.blender.org/docs/release_notes/3.3/pipeline_assets_io/ — official-docs — 2022 (verification)
[28] Blender 3.1 manual, glTF 2.0 add-on — https://docs.blender.org/manual/en/3.1/addons/import_export/scene_gltf2.html — official-docs — 2022 (verification)
[29] glTF importer: add option to glue pieces of a mesh together — https://developer.blender.org/rBAc7eda7cb49f706040cb04048b24c6db57501889e — commit — 2020 (verification)
[30] obj: vertex colors support in importer and exporter — https://developer.blender.org/rB1b4f35f6a58 — commit — 2022 (verification)
[31] Basel Face Model 2019 Point Coordinates (Scalismo forum; user report, not official) — https://groups.google.com/g/scalismo-faces/c/FJym8ubvMBI — forum — n.d. (verification)

**Further reading (by name, not yet linked)**
- Blender Manual: Import/Export (OBJ, PLY, STL, FBX, glTF 2.0, USD, Alembic); the Shrinkwrap, Surface Deform, Laplacian Deform, Data Transfer, Multires, Remesh and Decimate pages; Cycles baking
- Khronos, glTF 2.0 Specification (coordinate system, units, mesh attributes)
- Pixar, Universal Scene Description documentation (`metersPerUnit`, `upAxis`)
- Li, Bolkart, Black, Li, Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017
- Paysan et al., "A 3D Face Model for Pose and Illumination Invariant Face Recognition" (BFM), 2009; Gerig et al., "Morphable Face Models – An Open Framework" (BFM 2017), 2018
- Umeyama, "Least-squares estimation of transformation parameters between two point patterns", IEEE TPAMI 1991
- Besl & McKay, "A Method for Registration of 3-D Shapes", 1992
- Garland & Heckbert, "Surface Simplification Using Quadric Error Metrics", SIGGRAPH 1997
- Museth, "VDB: High-resolution sparse volumes with dynamic topology", 2013
- Dodgson, "Variation and extrema of human interpupillary distance", 2004
- Farkas, *Anthropometry of the Head and Face*, 1994
- R3DS/Faceform Wrap user documentation

## Verification log (2026-11-20)

- FLAME units, axes, 5,023 vertices / 9,976 triangles: unconfirmed. Search confirmed only the 5,023 vertex count in papers (e.g. https://arxiv.org/pdf/1905.06817); no source stated metres, Y-up or +Z facing. Left 🧠.
- Vertex order kept by OBJ/PLY, glTF seam splitting: partly confirmed. glTF seam/hard-edge vertex splitting and the Merge Vertices option are documented (https://docs.blender.org/manual/en/3.1/addons/import_export/scene_gltf2.html, https://developer.blender.org/rBAc7eda7cb49f706040cb04048b24c6db57501889e), badge 📄. OBJ/PLY order preservation and "Split by Object/Group" renumbering: unconfirmed, left 🧠.
- BFM/MakeHuman/MediaPipe units: contested for BFM 2009 (.mat in µm, .h5 in mm per a user report at https://groups.google.com/g/scalismo-faces/c/FJym8ubvMBI; no official statement); BFM 2017/2019 mm per the same thread. MakeHuman (dm) and MediaPipe (cm) unconfirmed, left as is.
- Legacy importers: confirmed that the Python OBJ and PLY add-ons were removed in 4.0 (https://wiki.blender.org/release_notes/4.0/python_api/). Corrected: the STL add-on was only marked legacy in 4.1 (https://developer.blender.org/docs/release_notes/4.1/pipeline_assets_io/). C++ OBJ importer in 3.3 confirmed (https://developer.blender.org/docs/release_notes/3.3/pipeline_assets_io/). PLY/STL importers in 3.6, COLLADA removed in 5.0: unconfirmed. OBJ vertex-colour/MRGB support: a commit (https://developer.blender.org/rB1b4f35f6a58) and search summary place it in 3.3, versus the note's 3.5+; unresolved, left 🧠.
