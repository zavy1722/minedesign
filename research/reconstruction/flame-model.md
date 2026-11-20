# FLAME head model in depth

> FLAME (Li, Bolkart, Black, Li and Romero, SIGGRAPH Asia 2017) is an articulated head-and-neck model with 5,023 vertices and 9,976 triangles: a mean template plus linear identity, expression and pose-corrective blendshapes, driven by linear blend skinning (LBS) over a root and four joints (neck, jaw, two eyeballs). Nearly every open photo→3D face method from 2019 to 2026 targets it, so trackers and regressors usually emit FLAME *parameters* rather than meshes. For this project it is a fitting cage and interchange format, not a likeness: its identity space comes mostly from about 3,800 North American and European adults (CAESAR), so ears, the nose tip and asymmetry are under-modelled, and it has no mouth interior, teeth or hair. Its licence decides what can ship, and the reported CC BY 4.0 "FLAME 2023 Open" release is the fact most worth verifying. In Blender, protect three things: metres, the Y-up frame and vertex order.
> Evidence status: 0 ✅ / 0 📄 / 61 🧠 / 9 ↔️ — 🧠 items are queued for web verification. This step had no harvest file and no earlier draft, so no URL is cited. Where a sibling note already cites a related fact, it is named inline as (lib: path).

## Key facts

**Structure and maths**
- **Mesh:** 5,023 vertices and 9,976 triangles, all triangles. One head-and-neck surface plus two separate eyeball shells. The neck base is open. There is no mouth cavity, teeth, tongue or eyelid thickness, and the ears are low-resolution. 🧠 (lib: blender/import-export-scans.md and reconstruction/multi-view-fitting.md agree)
- **Eyeballs:** in the releases I know, the eyeballs are the last ≈1,092 vertices, ≈546 each. Read the indices from `FLAME_masks.pkl` rather than hard-coding them. 🧠
- **Model equation:** M(β, θ, ψ) = W(T_P, J(β), θ, 𝒲), with T_P = T̄ + B_S(β) + B_E(ψ) + B_P(θ) (β shape, ψ expression, θ pose, 𝒲 skinning weights): SMPL's formulation transplanted to the head. 🧠
- **Kinematic tree:** joint 0 is the root (global rotation). Joint 1 is the neck, and joints 2–4 are the jaw, left eye and right eye. Parents are [−1, 0, 1, 1, 1]. θ ∈ ℝ¹⁵ in axis-angle: global 3, neck 3, jaw 3, eyes 3 + 3. 🧠
- **Joint regression:** J = 𝒥·(T̄ + B_S·β). The reference PyTorch layer concatenates shape and expression into one 400-column `shapedirs` before regressing joints, so expression moves the joints slightly. A re-implementation must copy this or its output will differ. 🧠
- **Pose correctives:** the input features are vec(R_k − I) for the four non-root joints, giving 4 × 9 = 36 features, so `posedirs` is 5,023 × 3 × 36. The root is excluded, so global rotation never deforms the mesh. 🧠
- **Skinning:** plain LBS with dense 5,023 × 5 weights, not dual-quaternion skinning. 🧠
- **Basis scaling:** shape and expression bases are scaled so that β, ψ ≈ N(0, 1) per component. The FLAME 2017 and 2020 releases ship 300 shape and 100 expression components. 🧠 (lib: reconstruction/multi-view-fitting.md)
- **Frame and units:** coordinates are in **metres**, Y is up, the face looks toward +Z, and +X points to the subject's left. The origin is not an anatomical landmark. 🧠 (lib: blender/import-export-scans.md)
- **Training data:** identity from roughly 3,800 CAESAR scans (adults scanned around 1998–2000 in North America and Europe); expression and pose from D3DFACS plus the authors' own 4D captures, with expression PCA learnt after removing identity and pose. Tens of thousands of registered frames in all. 🧠
- **Variants:** female, male and generic models. Almost all regressors use `generic_model.pkl`. 🧠

**Versions and licence**
- **Topology is constant across 2017, 2020 and 2023,** so masks, landmark embeddings and UVs carry over between them. **Coefficients do not:** the bases differ, so β fitted on 2020 is meaningless on 2023. 🧠 ↔️ (Confirm that the 2023 topology is identical.)
- **FLAME 2020** ("fixed mouth, improved expressions, more data", as I recall the download page) is the file DECA, EMOCA, MICA, SMIRK and SPECTRE expect. 🧠
- **FLAME 2023** revises the eye and eyelid region and the expression space. VHAP and GaussianAvatars-family code ask for it, reportedly the "with jaw rotation" variant. ↔️ (lib: reconstruction/multi-view-fitting.md)
- **FLAME 2023 Open** is reportedly released under CC BY 4.0. Its exact contents are not established: the full 300/100 bases, which training data, and whether it includes masks and UVs. This is the single most consequential fact for a shippable tool, and it is unverified. ↔️
- **Standard licence:** free for non-commercial scientific research after registration on the FLAME website, with no redistribution, so code repositories make you download the files yourself (lib: reconstruction/multi-view-fitting.md). Commercial licences go through MPI or Meshcapade. Treat fitted meshes as derived from the model, and read the prohibited-use clauses: they cover more than commercial use. 🧠 ↔️

**Texture spaces.** The core model has no albedo.
- **MPI FLAME texture space** (`FLAME_texture.npz`): a PCA built from FLAME fits to FFHQ, on the order of 200 components at 512² in FLAME UV. Its lighting is baked in. 🧠
- **BFM→FLAME albedo** (`FLAME_albedo_from_BFM.npz`): built locally with the BFM_to_FLAME converter. It inherits BFM's licence. DECA uses 50 of its components. 🧠 (lib: reconstruction/albedo-lighting-inverse-rendering.md)
- **AlbedoMM** (Smith et al., CVPR 2020) has a FLAME-topology version with diffuse and specular albedo in linear colour. 🧠
- **UV layout:** the FLAME 2020 layout (DECA's `head_template.obj`) is the de-facto standard. Whether FLAME 2023 changed it is unconfirmed. ↔️

**Ecosystem**
- **FLAME-Universe** is a curated GitHub list of FLAME-based papers, code and datasets, maintained by the FLAME authors (Bolkart). It is the best index of the ecosystem. 🧠
- **Official and near-official code:** TF_FLAME (TensorFlow: sampling, landmark and scan fitting, texture), `flame-fitting` (chumpy), FLAME_PyTorch (a differentiable layer plus landmark embeddings), BFM_to_FLAME, and `photometric_optimization`. 🧠
- **Landmark embeddings:** a static set of 51 inner iBUG-68 points stored as barycentric coordinates on triangles. A dynamic 17-point jaw contour is tabulated over 79 yaw bins (−39° to +39°, from RingNet and DECA). MICA ships a MediaPipe embedding of about 105 points. 🧠
- **`FLAME_masks.pkl`:** vertex-index masks for face, forehead, nose, lips, the left and right eye regions, both eyeballs, both ears, scalp, neck and boundary. 🧠
- **SMPL-X's head is FLAME-compatible.** A 5,023-entry vertex correspondence file maps FLAME into SMPL-X, the route for body integration. 🧠
- **Blender add-on:** MPI distributes a FLAME Blender add-on from the FLAME website after registration; it bundles model data, so it carries the model licence. It loads FLAME as a mesh with shape and expression shape keys, a neck/jaw/eye armature, pose-corrective keys, random/reset buttons and OBJ export. Feature list, component count and supported Blender versions are time-sensitive. 🧠 ↔️

## Numbers & reference tables

**Table 1: arrays in a FLAME `.pkl`.** The file is a chumpy pickle, so open it with `encoding='latin1'`. 🧠

| Array | Shape | Meaning | Status |
|---|---|---|---|
| `v_template` | 5023 × 3 | mean head, m | 🧠 |
| `f` | 9976 × 3 | triangle indices | 🧠 |
| `shapedirs` | 5023 × 3 × 400 | 300 shape + 100 expression columns | 🧠 |
| `posedirs` | 5023 × 3 × 36 | pose correctives, 4 joints × 9 | 🧠 |
| `J_regressor` | 5 × 5023 (sparse) | joint locations from vertices | 🧠 |
| `weights` | 5023 × 5 | LBS weights | 🧠 |
| `kintree_table` | 2 × 5 | parents [−1, 0, 1, 1, 1] | 🧠 |

**Table 2: parameters, units and plausible ranges.** Ranges are suggested design defaults, not published limits.

| Parameter | Dims | Unit | Plausible range | Status |
|---|---|---|---|---|
| β, shape | 300 | SD | \|β_i\| ≲ 3 | 🧠 |
| ψ, expression | 100 | SD | \|ψ_i\| ≲ 3; neutral ≲ 0.5 | 🧠 |
| global rotation | 3 | rad | free (or carried by the camera) | 🧠 |
| neck | 3 | rad | ±0.6 | 🧠 |
| jaw | 3 | rad | x ≈ −0.05 to 0.5 (+x opens: confirm the sign); y, z ±0.1 | 🧠 |
| each eye | 3 | rad | ±0.5 | 🧠 |
| translation | 3 | m | free | 🧠 |

**Table 3: versions.**

| Release | Shape / expression | What downstream code uses | Licence | Status |
|---|---|---|---|---|
| 2017 (initial) | 300 / 100 | legacy (TF_FLAME era) | research, non-commercial | 🧠 |
| 2020 | 300 / 100 | DECA, EMOCA, MICA, SMIRK, SPECTRE | research, non-commercial | 🧠 |
| 2023 | 300 / 100 (assumed) | VHAP, GaussianAvatars family | research, non-commercial | ↔️ |
| 2023 Open | unknown | — | CC BY 4.0 (reported) | ↔️ |

**Table 4: how many components common tools use.** Population: method defaults as I recall them.

| Method | Shape | Expression | Extras | Status |
|---|---|---|---|---|
| DECA / EMOCA | 100 | 50 | global + jaw (6), weak-perspective camera (3), albedo 50, SH 27 | 🧠 (lib: single-image-regression.md) |
| MICA | 300 | — | metric neutral identity | 🧠 |
| SMIRK | (from MICA or DECA) | 50 | 2 eyelid blendshapes, jaw | 🧠 |
| metrical-tracker / VHAP | 300 | 100 | per-frame pose, eyes, intrinsics | 🧠 |

**Table 5: Multires on FLAME.** Arithmetic: one subdivision turns each triangle into 3 quads, then each level multiplies faces by 4. Edge lengths are for the face region. (lib: reconstruction/sota-2025-2026.md)

| Level | Faces | Typical edge | Status |
|---|---|---|---|
| 0 | 9,976 tris | ≈3–6 mm | 🧠 |
| 1 | 29,928 | ≈1.5–3 mm | 🧠 |
| 2 | 119,712 | ≈0.75–1.5 mm | 🧠 |
| 3 | 478,848 | ≈0.4–0.75 mm | 🧠 |
| 4 | 1,915,392 | ≈0.2–0.4 mm | 🧠 |

**Context.** On NoW, a correctly scaled *average* FLAME scores about 1.5 mm mean error, and MICA about 1.1 mm. FLAME's identity space therefore carries roughly 0.4 mm of mean-error improvement over the mean face. The rest of the likeness lives in offsets and sculpting. 🧠 (lib: reconstruction/single-image-regression.md, Table 1)

## Applying this to photo→3D face sculpting in Blender

1. **Decide the licence route first.** For research or private study, FLAME 2020 or 2023 is fine. For commercial or shipped output, use the MPFB base (lib: blender/blender-face-addons.md), a Meshcapade licence, or FLAME 2023 Open once its terms and contents are verified. 🧠
2. **Download a matched set:** the model `.pkl` in the version your tracker expects, `FLAME_masks.pkl`, the landmark embeddings, the UV template OBJ and, optionally, a texture space. Keep all of it outside the project repository. 🧠
3. **Convert once, outside Blender.** chumpy is unmaintained and fails on modern NumPy and Python, and Blender 4.x and 5.x bundle Python 3.11 or later. Unpickle in a throwaway venv, or with a stub `chumpy` module, then save a plain `.npz`. The `.npz` is still licensed data, so never commit it. 🧠
4. **Choose an import path:** (a) the MPI add-on, for slider exploration; (b) an OBJ written by a numpy evaluator, imported as Wavefront with the defaults (Forward −Z, Up Y, which stands the head upright facing −Y) and "split by object/group" off; or (c) a bpy builder: mesh from `v_template`/`f`, a Basis key plus one key per component (`foreach_set("co", …)`, slider range −3 to 3, inside the API limit of ±10), five vertex groups from `weights`, and a five-bone armature whose Armature modifier has Preserve Volume **off**. 🧠
5. **Assert on import.** The vertex count must be 5,023. Head breadth should be ≈0.14–0.17 m in Blender units at unit scale 1.0. Check that normals face outward (Face Orientation overlay) and that the nose points −Y. If the breadth reads ≈150, you have millimetre data. 🧠
6. **Recompute joints after any identity change.** Bones left at template joint positions make the jaw hinge about the wrong pivot. The add-on calls this "update joint locations"; in the bpy builder, re-run J = 𝒥·v_shaped. 🧠
7. **Freeze the fit.** Write the neutral identity (ψ = 0, jaw = eyes = neck = 0) to a shape key named `flame_identity`, and keep an untouched FLAME object for re-fitting. Sculpt on a *copy* with the key applied, then add Multires. Mixing shape keys with Multires is fragile. 🧠
8. **Mind absolute sizes in metres:** a 0.5 mm voxel remesh is 0.0005, and Dyntopo constant detail works the same way. Voxel remesh, Dyntopo and Decimate destroy FLAME correspondence; use them only on throwaway sculpt copies. 🧠
9. **Fix FLAME-specific defects by sculpting:** the shallow nostrils, the slit mouth with no lip roll into a cavity, thin ears, eyelids with no thickness, and the flared neck boundary. Replace the eyeballs with a proper eye asset positioned at FLAME's eyeball centres (lib: blender/eyes-modeling-blender.md). 🧠
10. **Watch for interpenetration at high |β|.** Beyond about 2.5–3 SD, eyelids can cut into the eyeballs and lips can cross. Check every fit under MatCap from low and three-quarter angles. 🧠
11. **Round-trip back to FLAME:** export the OBJ with the same axes. If topology is untouched, project the sculpt onto FLAME space with β̂ = argmin ‖B_S·β − (V − T̄)‖² + λ‖β‖². The residual V − (T̄ + B_S·β̂) is the part FLAME cannot express, which is your likeness work. 🧠

**What goes wrong:** coefficients loaded into the wrong version or into gendered bases; a ×1000 unit error from millimetre demo output (lib: reconstruction/single-image-regression.md flags MICA's demo) ↔️; Join, Separate or Sort Elements silently reordering vertices; texture-space output treated as albedo; derived meshes shipped under a non-commercial licence. 🧠

## Algorithmic implications

- **A plain numpy model object:** `FlameModel{v_template, S (5023 × 3 × K_β), E (5023 × 3 × K_ψ), posedirs, J_regressor (dense 5 × 5023 is fine), weights, parents, version, basis_sha256}`. Evaluate in float64, internally in mm (×1000) to match the engine (`Priors.sigma_sym`, etc.). 🧠
- **Neutral fits are linear.** With every joint rotation at identity, LBS is the identity map, so v = T̄ + S·β + E·ψ exactly. Let the camera extrinsics carry head pose, fix global rotation and neck to 0, and the 3DMM layer is linear inside each `levenberg_marquardt` / `bundle_adjust` step, with an analytic Jacobian ∂v/∂β = S. Run full LBS only when jaw or eyes are free. 🧠
- **Precompute landmark-restricted bases.** Interpolate S and E at the landmark barycentrics (an L × 3 × K array), so the cost of a fit does not depend on the 5,023 vertices. Implement the dynamic jaw contour either as the yaw-binned table or as points that slide along the silhouette normal. 🧠
- **Gauge.** Global rotation and translation duplicate the camera extrinsics: fix one set. Overall size is inside β, so do not add a free scale when a metric anchor exists. Without one, add s with σ_log ≈ 0.05–0.1 and label the result "proportions only". 🧠
- **Component schedule:** sparse landmarks (68–105 points) use K_β = 20 → 50 → (100). Use all 300 only with dense correspondences, silhouettes or photometric terms. Expression gets K_ψ = 10–20 per view. 🧠

**Table 6: suggested priors** (FLAME parameters in SD units; tune on held-out views). (lib: reconstruction/multi-view-fitting.md, Table 5)

| Term | Prior / σ | Notes | Status |
|---|---|---|---|
| β | N(0, 1); flag \|β_i\| > 3 | shared across views | 🧠 |
| ψ, neutral-tagged view | N(0, 0.3²) | zeroed at hand-off | 🧠 |
| ψ, expressive view | N(0, 1) | per view | 🧠 |
| jaw, neutral view | σ ≈ 0.035–0.05 rad (2–3°); box x ∈ [−0.05, 0.6] | per view | 🧠 |
| eyes | exclude from landmark residual, or σ 0.3 rad | fit to iris points only | 🧠 |
| neck (stills) | fixed at 0 | absorbed by the camera | 🧠 |
| neck (video) | σ 0.1–0.2 rad, plus temporal smoothness | — | 🧠 |
| per-vertex offsets after β | Laplacian-regularised, ≲3–5 mm | holds the likeness residual | 🧠 |
| region weights | face 1; ears 0.3–0.5; scalp 0.1; neck 0.1–0.2; eyeballs, boundary and mouth interior 0 | taken from `FLAME_masks.pkl` | 🧠 |

- **Version safety.** Every saved coefficient vector carries `{model, version, basis_sha256, K_β, K_ψ}`. The loader refuses mismatches and never zero-pads silently between versions. 🧠
- **Licence as data.** `commercial_ok = false` for FLAME 2017, 2020 and 2023, and "unknown" for 2023 Open until verified. Export refuses unless the user overrides with an explicit research flag. Load models only from a user-supplied path. 🧠
- **Delivery topology.** Embed the project's quad template in FLAME once (barycentric) and push every subject through that map. 🧠

## Disagreements, myths & open questions

- **"FLAME is free."** ↔️ It is free for research, not for commercial use. FLAME 2023 Open may change this; that is unverified.
- **Myth: "FLAME coefficients are portable across versions."** They are not; only the topology carries over. 🧠
- **Myth: "Fitting all 300 components to landmarks gives more likeness."** With 68–105 points it fits noise and the contour bias of landmark detectors. 🧠
- **Myth: "FLAME output is metric."** The template is; DECA-type regressors (weak perspective) are not; MICA is trained to be. 🧠
- **Myth: "the FLAME texture is albedo."** Lighting is baked in. 🧠
- **Population bias** ↔️: CAESAR adults of mostly European descent. Widening σ_β for other groups is a heuristic, not a validated fix.
- **Back of the head:** photos with hair barely constrain it, so the prior dominates. Treat the scalp as plausible, not measured. 🧠
- **Open questions:**
  - the exact contents and licence of 2023 Open;
  - whether 2023 changed the UVs or eyeball vertices;
  - which Blender versions the add-on supports in late 2026;
  - whether the 2023 "jaw" and "no jaw" files differ only in the expression basis. ↔️

## Sources

No URL-bearing input existed for this step: the harvest file and the earlier draft were both absent. No URLs are cited. Related URLs are already cited in the sibling notes named inline.

**Further reading (by name, not yet linked)**
- Li, Bolkart, Black, Li, Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), ACM TOG / SIGGRAPH Asia 2017
- Loper et al., "SMPL: A Skinned Multi-Person Linear Model", SIGGRAPH Asia 2015
- Pavlakos et al., "Expressive Body Capture" (SMPL-X), CVPR 2019
- Sanyal, Bolkart, Feng, Black, RingNet and the NoW benchmark, CVPR 2019
- Feng, Feng, Black, Bolkart, DECA, SIGGRAPH 2021
- Danecek, Black, Bolkart, EMOCA, CVPR 2022
- Zielonka, Bolkart, Thies, "Towards Metrical Reconstruction of Human Faces" (MICA), ECCV 2022
- Retsinas et al., SMIRK, CVPR 2024
- Smith et al., "A Morphable Face Albedo Model" (AlbedoMM), CVPR 2020
- Qian et al., GaussianAvatars, CVPR 2024
- Cosker, Krumhuber, Hilton, D3DFACS, ICCV 2011
- Robinette et al., CAESAR final report, 2002
- Code by name: TimoBolkart/FLAME-Universe, TimoBolkart/TF_FLAME, Rubikplayer/flame-fitting, soubhiksanyal/FLAME_PyTorch, TimoBolkart/BFM_to_FLAME, HavenFeng/photometric_optimization, the MPI FLAME Blender add-on (FLAME website)
