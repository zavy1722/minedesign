# Open-licence template head kit for fitting and sculpting

> extensions.blender.org accepts only CC0 non-code assets inside an add-on, so the shippable default is a project-owned quad head derived from a CC0 source (Blender Studio's Human Base Meshes head or the MakeHuman/MPFB2 hm08 head), released as CC0 with a versioned sidecar: landmark barycentrics, anthropometric vertices, contour rings, region masks, a mirror map and priors. hm08's CC0 face targets, transferred barycentrically and calibrated against anthropometric norms, give a bundled identity prior that may be used commercially. FLAME 2023 Open (CC BY 4.0), ICT-FaceKit (MIT claimed, contested) and the MediaPipe canonical mesh (Apache-2.0) are GPL-3-compatible in principle but not CC0, so they load from user paths through one barycentric adapter, or ship only in builds distributed off-platform with attribution. FLAME 2023 Open's licence is settled in sibling notes, but its contents (component counts, masks, UVs, landmark files and their licences) are not. No harvest or draft existed for this topic: **lib✓** marks facts source-checked in the sibling note named, and every count is a recollection or design default to assert on import.
> Evidence status: 0 ✅ / 0 📄 / 71 🧠 / 15 ↔️ — 🧠 items are queued for web verification (19 of them are lib✓, already checked in sibling notes).

## Key facts

**Licence and redistribution**
- **Platform rule:** add-on code must be GPL-3.0-or-later and bundled non-code assets must be CC0. Requiring externally downloaded components is not allowed. 🧠 lib✓ (`blender/blender-extensions-packaging.md`, Terms of Service). So FLAME-, ICT- or MediaPipe-derived meshes cannot sit in the listed zip.
- **Outside the platform** (own repository), the test is GPL-3 compatibility: CC0, MIT, Apache-2.0 and CC BY 4.0 qualify in the FSF's reading; non-commercial (NC) terms do not. 🧠 CC BY 4.0 requires credit, a licence link and a change note, and forbids added restrictions or technological measures. 🧠
- **MPFB2:** code GPL-3.0-or-later. MakeHuman's base mesh, targets, proxies and system assets are CC0; asset packs are CC0 or CC-BY, so check each pack. 🧠 lib✓ (`blender/blender-face-addons.md`)
- **Blender Studio Human Base Meshes** (asset bundle, June 2023) are CC0. 🧠 lib✓ two sources (`community/youtube-likeness-blender.md`)
- **FLAME 2023 Open** is CC BY 4.0, the only CC-BY FLAME. Download still needs registration, a script converts expression parameters from `flame2023.pkl` to `flame2023_Open.pkl`, and the site lists it as 11/25. 🧠 lib✓ (`reconstruction/flame-model.md`). The FLAME texture model is reported as CC BY-NC-SA 4.0 ↔️ (`ethics/README.md` C6).
- **ICT-FaceKit:** I recall an MIT LICENSE in the GitHub repo, but the USC VGL page says to contact it for commercial use ↔️ (lib, `community/awesome-lists-resources.md`). The consent scope of the scan subjects is unknown. 🧠

**What each candidate actually is**
- **Blender Studio head:** sculpt-grade all-quad topology made for Multires, at real scale on Blender axes. It has no shape space, no landmark map and no 3DMM correspondence. Its vertex counts, and whether the heads carry eyeballs, teeth or a mouth bag, are not recalled: inspect them. 🧠 ↔️
- **hm08** is a whole-body quad mesh: ≈13.4k body vertices, ≈19.2k with the helper geometry (tights, skirt, hair, joint cubes) that MPFB hides with a Mask modifier. Its native frame is Y-up, facing +Z, in decimetres. 🧠 (lib count unconfirmed)
  - Eyes, teeth, tongue, brows and lashes are separate CC0 proxies. Each proxy vertex is bound to three base vertices with weights plus a scaled offset, so MakeHuman already uses the barycentric-sidecar mechanism proposed here. 🧠
  - Face targets are sparse offsets named `region-feature-decr|incr`. A modifier value v ∈ [−1, 1] applies `decr` with weight −v or `incr` with weight v, which is **piecewise linear, not linear**. Macros (gender, age, muscle, weight, proportions, ancestry blends) are multilinear interpolations between corner targets. 🧠
- **FLAME:** 5,023 vertices and 9,976 triangles covering head, neck and two eyeball shells, with an open neck base, low-resolution ears and no mouth interior. Metres, Y-up, facing +Z. A fitting cage, not a sculpt topology. 🧠 lib (`reconstruction/flame-model.md`)
- **ICT-FaceKit** (recalled; verify all of it) 🧠 ↔️:
  - ≈26.7k quad vertices, in named index blocks: face ≈9.4k (dense), head and neck (coarse), mouth socket, left and right eye sockets, gums and tongue, teeth, eyeballs, lacrimal fluid, and eye-blend and occlusion shells.
  - 100 identity PCA modes in the "Light" release (200+ in "Full", lib) and 53 expressions.
  - My reconstruction of the 53: ARKit's 52 minus `tongueOut`, with `browInnerUp` and `cheekPuff` split left and right.
  - It is the best existing template for sub-mesh structure.
- **MediaPipe canonical mesh** (`face_geometry/data/canonical_face_model.obj`, Apache-2.0 with the repo): 468 vertices with UVs, face only, all triangles, believed cm 🧠. The OBJ should have **898 triangles** with the eyes and mouth closed over; the landmark tessellation has 852 with them open. The Euler check fits: a 36-edge face-oval boundary, and 16 + 16 + 20 hole edges filled by 46 triangles 🧠. It *defines* the MediaPipe landmark convention; it is not a base head.

**FLAME 2023 Open: what is and is not known**
- Established: the licence, the registration gate and the expression-parameter converter (lib✓). 🧠
- Inferred: the converter only makes sense if the topology is the shared 5,023-vertex one and the **expression basis differs** from FLAME 2023. That no shape converter is reported hints the identity space may be unchanged. ↔️
- Unknown: the K_β and K_ψ counts; training data; whether `posedirs`, `J_regressor` and LBS weights are included; and whether `FLAME_masks.pkl`, landmark embeddings and the UV template are released under CC BY or remain under the original non-commercial terms. ↔️ Lib reports that FLAME 2023 folds jaw rotation into the expression basis (two papers, `reconstruction/flame-model.md` log). ↔️

**Barycentric basis transfer**
- With a sparse map W (n_t × 5,023, three non-zeros per row), the transferred basis is U′ = (W ⊗ I₃)U and the mean is x̄′ = Wx̄. **The prior stays N(0, I)**, because β parameterises the same shapes, now sampled at different points. Coefficients stay FLAME-compatible both ways. 🧠
- Licence: a transferred FLAME 2023 Open basis is CC BY "adapted material". It can be shared with attribution and a change note, off-platform only. An NC FLAME transfer must be computed locally and never shipped. 🧠 ↔️ (not legal advice)

## Numbers & reference tables

**Table 1: candidate templates** (rows recalled; assert everything on import)

| | Blender Studio head | hm08 (MPFB2) | FLAME 2023 Open | ICT-FaceKit | MediaPipe canonical |
|---|---|---|---|---|---|
| Licence | CC0 🧠 lib✓ | CC0 base and targets 🧠 lib✓ | CC BY 4.0 🧠 lib✓ | MIT? ↔️ | Apache-2.0 🧠 |
| Bundle on extensions.blender.org | yes | yes (CC0 parts) | no (not CC0) | no | no (C7 open) ↔️ |
| Ship off-platform in GPL-3+ | yes | yes | yes, with attribution and change note 🧠 | yes, with notice, if MIT holds ↔️ | yes, with NOTICE 🧠 |
| Vertices / faces | not recalled | ≈13.4k body / ≈19.2k all, quads 🧠 | 5,023 / 9,976 tris 🧠 | ≈26.7k, quads 🧠 | 468 / 898 tris 🧠 |
| Edge flow | sculpt loops 🧠 | animation loops, coarse face 🧠 | none (tris) | production loops 🧠 | none |
| Head, neck, ears | yes 🧠 | full body 🧠 | yes, open neck, coarse ears 🧠 | yes, coarse back of head 🧠 | face only |
| Eyes, teeth, tongue, mouth bag, sockets | inspect ↔️ | eyes, teeth, tongue as proxies 🧠 | eyeballs only 🧠 | all 🧠 | none |
| UVs | yes? ↔️ | body-wide tile 🧠 | separate template OBJ, licence? ↔️ | yes 🧠 | frontal UV 🧠 |
| Units, up, face direction | m, +Z, −Y 🧠 | dm, +Y, +Z (MPFB: m) 🧠 | m, +Y, +Z 🧠 | cm?, +Y, +Z ↔️ | cm, +Y, +Z ↔️ |
| Shape prior | none | targets (piecewise linear) 🧠 | β ~ N(0, I), K unknown ↔️ | 100 PCA 🧠 | none |
| Mirror map shipped | no; compute (modelled symmetric) 🧠 | no; MakeTarget mirrors targets 🧠 | no; compute on mean ↔️ | no; compute ↔️ | landmark pairs by construction 🧠 |

**Table 2: proposed template budget** (adult head at 1 unit = 1 m; edge lengths at Multires level 0) 🧠

| Sub-mesh | Vertices | Edge length | Notes |
|---|---|---|---|
| Skin: head, neck, ears; closed scalp, open neck | 8,000–12,000 | lids 1–2 mm across loops; lips 1.5–3; nose 1.5–3; cheek 4–7; scalp and neck 6–12 | exact x = 0 midline; poles ≥ 2 rings from margins |
| Lid tuck into the socket | 2–3 loops | ≤ 1.5 mm | ends behind the globe, or closes into a socket sac |
| Mouth bag, continuous with the inner lip loops | 300–800 | 4–8 mm | ≈30–40 mm deep |
| Eyeballs (sclera + cornea shells) ×2 | 500–1,000 each | — | globe ≈24 mm (lib 📄), cornea R ≈7.8 mm (lib ✅) |
| Teeth and gums (upper, lower) | 600–3,000 | — | rigid; follow skull and jaw |
| Tongue | 300–800 | — | rigid in neutral |
| Multires at level 4 (×256 faces) | ≈2–3M faces on skin | 0.15–0.5 mm | pores need level 4–5 |

**Table 3: landmark conventions the sidecar embeds** 🧠

| Convention | Points | Kind | Storage |
|---|---|---|---|
| MediaPipe 468 (+10 iris) | 478 | surface; the 36 face-oval points are semi-contour; iris on the eyeball model | (tri, bary) via canonical-mesh registration; iris → limbus circle |
| iBUG-68 (dlib, FAN, 300-W) | 68 | 51 surface + 17 jaw contour | 51 (tri, bary); 17 → candidate rings |
| WFLW-98 | 98 | 65 surface + 33 contour | same pattern |
| FLAME static 51 + dynamic 17 | 68 | as iBUG, yaw-binned (79 bins, lib) | only when FLAME is loaded |
| Farkas anthropometric | ≈40 | fixed vertex, or extremal over a candidate set | see Applying, step 4 |

**Table 4: region masks and per-region residual σ** (per-vertex offset after the basis fit, at 1 SD) 🧠 design defaults

| Region | σ offset (mm) | Landmark weight | Comment |
|---|---|---|---|
| Lids, canthi | 1.0–1.5 | 1.0 | thin tissue, well observed |
| Lips, vermilion | 1.5–2.5 | 1.0 | expression contaminates |
| Nose | 2–3 | 1.0 | profile and silhouette drive it |
| Brow, forehead | 2–3 | 0.7 | brow points mark hair, not bone |
| Cheek, malar | 2.5–4 | 0.5 | fat variation; shading cues |
| Jaw, chin | 2–4 | 0.7 (contour) | silhouette-driven |
| Ears | 3–5 | 0.3–0.5 | poorly observed, highly individual |
| Scalp, back of head | 3–6 | 0.1 | hair; prior dominates |
| Neck | 5–10 | 0.1–0.2 | posture, not identity |
| Mouth interior, eyeballs, teeth | 0 (rigid or excluded) | 0 | own models |
| Symmetry residual | face 1.5, lateral and lower 2.5, ears 3.5 | — | mirror RMSD ≈0.8 mm (closest point); landmark pairs differ 0.6–4.6 mm (lib 📄 `anatomy/facial-asymmetry.md`) |

**Table 5: axis conversions into Blender** (Z-up, face toward −Y, +X = subject's left) 🧠

| Source | (x, y, z) → Blender | Scale to m | Badge |
|---|---|---|---|
| FLAME | (x, −z, y), +90° about X | 1 | 🧠 lib |
| MediaPipe canonical | (x, −z, y) | 0.01 | ↔️ |
| ICT-FaceKit | (x, −z, y) | 0.01 if breadth reads ≈15 | ↔️ |
| MakeHuman native | (x, −z, y) | 0.1 | 🧠 |
| Blender Studio, MPFB import | identity | 1 | 🧠 |

Unit check for any import: adult en–en spans ≈31–41 mm (lib ✅ `blender/import-export-scans.md`) and eu–eu ≈140–160 mm. 🧠

## Applying this to photo→3D face sculpting in Blender

1. **Choose the source once.** Take the Blender Studio realistic head if its sculpt topology and sub-meshes pass inspection; otherwise crop hm08 at the clavicles. Either way, re-author into one project template (`minehead`). Release it as CC0, and record its provenance in `NOTICE`. 🧠
2. **Run the topology QA** from `blender/face-retopology.md`:
   - zero non-quads in deforming zones;
   - poles at least 2 rings from the lid margins, vermilion, commissures, alar rims and canthi;
   - an exact x = 0 midline;
   - skin watertight except the neck, with the sockets and mouth bag closed, so random-walk SSS works.

   Then freeze it: write `topology_sha256` over the face-index array. 🧠
3. **Build the mirror map.** Mirror x, match each vertex to its partner with a KD-tree at 1e-5 m tolerance, and require a bijection with M(M(i)) = i and midline vertices mapping to themselves. Store it as `mirror.npy`. For scan-derived topologies (FLAME, ICT), match on the mean shape, then repair one-to-one with an assignment solve. 🧠
4. **Place anthropometric points.** Fixed vertices: n, se, prn, sn, ls, sto, li, sl, pg, gn, me, en, ex, ps, pi, al, sbal, ch, cph, t, sa, sba, obs, obi. Extremal points (eu, zy, go, v, op, tr) are defined as a candidate set plus a rule (for example "max |x| in the Frankfort-horizontal frame"), not as one vertex. 🧠
5. **Register each detector convention.** Non-rigid-ICP the MediaPipe canonical mesh onto `minehead`, seeding with about 20 hand-placed pairs. Store (tri, bary) for each index; MediaPipe indices 468–477 bind to the eyeball limbus model. 🧠
6. **Define contour rings.** Store 5–9 parallel candidate rings from the ear lobe to the chin, the profile midline, forehead and scalp rings, the helix rim and two neck rings. At fit time the silhouette point is chosen *on these rings*, not on fixed vertices. 🧠
7. **Bind sub-meshes like MakeHuman proxies.** Eyeball centre = Σ wₖvₖ + d over orbital-rim vertices. Upper teeth follow a maxilla patch; lower teeth follow the jaw. Identity changes then carry them along and do not intersect. 🧠
8. **Check each import** (FLAME, ICT, MediaPipe): vertex count, topology hash, breadth ≈0.14–0.16 m after scaling, nose pointing −Y, and outward-facing normals. 🧠
9. **What goes wrong:**
   - CC-BY MakeHuman packs or ICT data slipping into the listed zip;
   - transferred bases spiking where the template has geometry FLAME lacks (mouth bag, nostrils, lid tuck);
   - hm08 `incr`/`decr` treated as ±1 of one vector;
   - Join, Separate or Sort Elements reordering vertices;
   - Multires added before identity is final.

   🧠

## Algorithmic implications

- **Sidecar schema** (`minehead.json` plus `.npz`) 🧠:
  `{version, topology_sha256, units:"m", axes:{up:"+Z", face:"-Y", left:"+X"}, licence:"CC0-1.0", derived_from:[…], submeshes:{name:[start,end)}, mirror, midline, landmarks:{conv:{tri, bary, weight, kind}}, anthro:{code: vid | {candidates, rule}}, contours:{name:[rings]}, regions:{name: soft mask 0–1, 5–10 mm falloff}, sigma_region_mm, bases:{name:{U, sigma, licence, commercial_ok, bundle_ok, source_sha256}}}`.
  The loader refuses a hash mismatch.
- **Transfer algorithm** 🧠:
  1. Landmark-seeded non-rigid ICP of `minehead` onto the source mean (stiffness schedule, as in `blender/import-export-scans.md`).
  2. Closest-point projection gives (tri, bary).
  3. Accept a projection only if its distance is under 2–3 mm and the normals agree (cos > 0.5).
  4. Rejected vertices (mouth bag, deep nostril, lid tuck) get each basis column by harmonic or biharmonic interpolation from accepted neighbours.
  5. Rigid sub-meshes get per-component rigid motions of their binding patches.

  Store W as data; compute U′ at load time from the user's file.
- **hm08 targets as a basis** 🧠:
  - Split every modifier into two non-negative columns (incr, decr) with a box of [0, 1] and a penalty λ·cᵢ⁺cᵢ⁻ that discourages using both. Restrict to head vertices, convert dm to m, and transfer.
  - Optionally orthogonalise with a mass-weighted SVD for conditioning, keeping K ≈ 40–80.
  - Fit macros (age, gender, weight) in an outer loop, boxed to [0, 1] with σ 0.15 toward user values (lib).
- **Calibrate σ by moment matching:**
  - Let J = ∂m/∂c, the Jacobian of about 25 Farkas measurements (n–gn, zy–zy, al–al, ch–ch, en–en, ex–ex, prn–sn, sn–sto, …) with respect to the target coefficients.
  - Solve min ‖JΣ_cJᵀ − Σ_m‖_F subject to Σ_c ⪰ 0 (diagonal first). Σ_m comes from sex- and age-specific norm SDs (`anatomy/anthropometric-norms.md`) and assumed correlations (ρ 0.3–0.6 within size groups). ↔️
- **Anthropometric morphable model, a commercially clean fallback** 🧠:
  1. Sample 2–5k measurement vectors from N(μ_m, Σ_m).
  2. Realise each on `minehead` by least squares over the targets plus bounded-biharmonic handles at the landmarks, with Laplacian regularisation.
  3. Run PCA and keep 95–99 % of the variance as the basis, with σ_k = √λ_k.
  4. Validate that resampled measurements reproduce the norms, and test fits on consented scans you own.

  It spans only what the handles express. It is a prior on proportions, not on shape detail.
- **Energy and defaults** 🧠:
  - E = Σ landmarks ρ_Huber(r/σ_px) + contour terms + ‖β/σ_β‖² + Σ_r ‖Δ_r‖² / σ_r² (Table 4) + ‖(I − M)Δ‖² / σ_sym² + a Laplacian term.
  - Landmark σ: about 1.5 % of the inter-ocular distance for corners and the nose tip, 3–5 % for contour points.
  - Component schedule: K = 10 → 30 → all. Per-vertex offsets are released last.
- **Licence as data:** `commercial_ok`, `bundle_ok_platform` (CC0 only) and `attribution` strings travel with every basis. Export writes `ATTRIBUTION.txt` whenever a CC-BY basis touched the result. 🧠

## Disagreements, myths & open questions

- **Does the CC0 rule cover data-only meshes and index tables?** ↔️ A MediaPipe or FLAME *index map* holds no geometry and is arguably facts. Ask a platform reviewer before relying on that (`ethics/README.md` C7).
- **ICT-FaceKit licence:** MIT file versus "contact for commercial use". Treat it as not commercially clean until it is resolved. ↔️
- **FLAME 2023 Open** contents, auxiliary-file licences, and whether the click-through adds terms beyond CC BY. ↔️
- **Blender Studio versus hm08 as the source:** the Studio head is better topology; hm08 brings CC0 targets and proxies. Transferring hm08 targets onto a Studio-derived template gets both. 🧠
- **Myth: "CC0 targets make a statistical prior."** They are artist-made, correlated and unvalidated. Calibrated σ matches only marginal measurements. 🧠
- **Myth: "the MediaPipe canonical mesh is a base head."** It is a 468-point face cage with no ears, scalp, neck or loops. 🧠
- **Myth: "a denser template gives more likeness."** Likeness lives at levels 0–2. Density beyond about 12k vertices slows fitting and weakens the priors. 🧠
- **Population bias:** CAESAR (FLAME), Light Stage subjects (ICT), MakeHuman's artist-made ancestry sliders and Farkas's mostly North American norms. None is representative. ↔️

## Sources

No web harvest or earlier draft existed for this topic, so no URLs are cited here. The licence facts marked lib✓ carry their URLs in the sibling notes listed below.

**Library cross-references (internal):** `reconstruction/flame-model.md`, `reconstruction/3dmm-overview.md`, `blender/blender-extensions-packaging.md`, `blender/blender-face-addons.md`, `blender/face-retopology.md`, `blender/import-export-scans.md`, `community/youtube-likeness-blender.md`, `community/awesome-lists-resources.md`, `ethics/README.md`, `anatomy/facial-asymmetry.md`, `anatomy/anthropometric-norms.md`.

**Further reading (by name, not yet linked)**
- Li, Bolkart, Black, Li, Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017
- Li et al., "Learning Formation of Physically-Based Face Attributes" (ICT-FaceKit), CVPR 2020
- Kartynnik, Ablavatski, Grishchenko, Grundmann, "Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs", CVPR Workshops 2019
- Grishchenko et al., "Attention Mesh: High-fidelity Face Mesh Prediction in Real-time", CVPR Workshops 2020
- Bastioni, Re, Misra, "Ideas and methods for modeling 3D human figures" (MakeHuman), ACM COMPUTE 2008
- Farkas, *Anthropometry of the Head and Face*, 2nd ed., 1994
- Sagonas et al., 300-W challenge (iBUG 68-point scheme), ICCV Workshops 2013
- Wu et al., "Look at Boundary" (WFLW), CVPR 2018
- Amberg, Romdhani, Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007
- Jacobson et al., "Bounded Biharmonic Weights for Real-Time Deformation", SIGGRAPH 2011
- CC BY 4.0 and CC0 1.0 legal codes; FSF, "Various Licenses and Comments about Them"
- Blender Studio, Human Base Meshes (2023); MakeHuman licence page, MakeTarget and MPFB2 docs
