# Verified landmark index tables and cross-convention correspondences

> A photo-to-head fitter fails silently when it reads an index under the wrong convention: left/right, 0- vs 1-based numbering, fixed vertex vs sliding contour, or a detector's habit vs the anthropometric definition. This note settles the conventions for MediaPipe 478 (subject-relative left/right; image-space z, smaller = nearer; canonical mesh y-up, face toward +z). It gives index→Farkas tables and ordered region polylines, and cross-maps iBUG 68, WFLW 98, the 3D-68 sets, FLAME's 51 + 17 embedding, MICA's MediaPipe embedding and ARKit's 1,220-vertex mesh. Only the coarse layouts are confirmed by sources. Almost every per-index anatomical assignment is expert knowledge and must be locked by the render-and-detect calibration below before it becomes an engine constant. This topic had no harvest and no earlier draft, so the cited URLs come from sibling harvests in this library.
>
> Evidence status: 8 ✅ / 19 📄 / 83 🧠 / 28 ↔️ — 🧠 items are queued for web verification.

## Key facts

**MediaPipe 478**
- **Layout.** The 478 points are the 468 mesh vertices, in a stable order, plus 10 iris points at 468–477 [6][7] ✅. Legacy Face Mesh returns the first 468 [5][8] ✅. The refined model adds the iris points and refines the eye and lip points with an attention mesh [8] 📄. Face Landmarker also returns 52 blendshape scores in [0, 1] [1][2] ✅. So every 468-vertex table (canonical OBJ, UV picture, connection sets) applies unchanged to 478 output 🧠.
- **Left/right.** Labels are relative to the subject, and a mirrored (selfie) image swaps them [1] 📄. `FACEMESH_LEFT_EYE` is the 263/362 ring: on the image's right in an unmirrored frontal photo, and at +x in the canonical mesh 🧠.
- **Iris.** By the connection sets, `RIGHT_IRIS` is the ring 469–472 (centre 468) and `LEFT_IRIS` is 474–477 (centre 473) 🧠. Sources label the eye sides inconsistently [9][10] ↔️, so assign each iris to an eye geometrically and never by name.
- **z.** Normalised z is depth relative to the head centre: smaller is nearer, and the magnitude is roughly on the scale of x [3] 📄. The frame is therefore x right, y down, z away from the camera: right-handed and OpenCV-like. For isotropic pixels, multiply x and z by W and y by H 🧠.
- **Canonical model.** `canonical_face_model.obj` has 468 vertices with one UV per vertex. It is in centimetres, y up, face toward +z, with the subject's left at +x 🧠. A virtual perspective camera sits at the origin [3] 📄 and looks down −z 🧠. Expect about 898 triangles 🧠. If the only boundary is the 36-edge oval, Euler's formula implies the eye and mouth openings are triangulated across, so the lip seam is mesh-connected. Count the boundary edges before using the mesh as a wrap source 🧠.
- **Connection sets.** `FACE_OVAL` has 36 points. `LIPS` has 40 (20 outer, 20 inner). Each eye has 16. Each brow has 10, in two rows of 5. Each iris has a 4-point ring, centre excluded. `CONTOURS` (their union, irises excluded) has 128 unique points. Newer releases add a `NOSE` set 🧠.
- **Freeze the sets yourself.** The legacy `mp.solutions` package, home of `face_mesh_connections`, is gone from wheels from 0.10.30 onward [12] 📄. The Tasks API exposes `FaceLandmarksConnections` instead 🧠. Vendor frozen copies under Apache-2.0 attribution 🧠.
- **Midline.** 28 vertices, in order: 10, 151, 9, 8, 168, 6, 197, 195, 5, 4, 1, 19, 94, 2, 164, 0, 11, 12, 13, 14, 15, 16, 17, 18, 200, 199, 175, 152 🧠.
- **Lid points.** 159/145 and 386/374 are upper/lower lid contour points [9][10] 📄.

**68 / 98 / 3D-68**
- **iBUG 68, 0-based blocks.** Jaw 0–16, right brow 17–21, left brow 22–26, nose 27–35, right eye 36–41, left eye 42–47, mouth 48–67 (outer 48–59, inner 60–67) [14][16][17][18] ✅. "Right" is the subject's right 🧠. Papers and Matlab-era tools often number 1–68, so nose tip "31" is 0-based 30 🧠.
- **The 2D jaw slides.** Its points are spaced evenly along the *visible* outline [14] 📄 and are not 3D-consistent [21] 📄. They describe a silhouette, not tissue 🧠.
- **WFLW 98.** Contour 0–32. Right brow 33–41 (upper 33–37, lower 38–41). Left brow 42–50 (upper 42–46). Nose 51–59. Right eye 60–67 (60 outer, 64 inner corner). Left eye 68–75 (68 inner, 72 outer). Outer lip 76–87. Inner lip 88–95. Pupils 96/97 🧠. The →68 conversion drops alternate jaw points and the extra lower-brow points [20] 📄.
- **3D-68 (300W-LP, AFLW2000-3D, LS3D-W).** Same index semantics as iBUG 68, but jaw points are *fixed* model vertices, projected even when hidden 🧠. 300W-LP holds 61,225 synthesised large-pose images (122,450 with flips), fitted with BFM 🧠.

**FLAME / MICA / ARKit**
- **FLAME embedding.** The static set holds 51 barycentric points equal to iBUG 17–67, so static index = iBUG index − 17. The dynamic set holds 17 jaw points (iBUG 0–16) tabulated over 79 yaw bins clamped to ±39° 🧠. In DECA-style code, yaw ≥ 0 uses bin round(yaw) and yaw < 0 uses 39 − round(yaw); check the sign on your rotation 🧠.
- **MICA.** MICA [24] / metrical-tracker ship a MediaPipe→FLAME embedding of about 105 points (MediaPipe ids, FLAME triangle ids, barycentrics) ↔️. MICA's demo writes vertices ×1000, in mm [25] 📄.
- **ARKit.** `ARFaceGeometry` has 1,220 vertices and 2,304 triangles in a fixed topology, in metres. Apple defines +x as the face's own left, +y up and +z out of the face 🧠 (L/R reports differ ↔️). Apple publishes no semantic vertex list 🧠.
- **Frames all agree.** FLAME (m, Y up, +X subject's left), ARKit, MediaPipe canonical (cm) and the engine (`face3d/synthetic.py`: mm, +x subject's left, +y up, +z out) share axes. Only the scale differs: ×1000, ×1000 and ×10 to engine mm 🧠.

**Licences** (details in Table 1)
- MediaPipe sets, canonical OBJ and UV picture are Apache-2.0 and redistributable with notice 🧠.
- The PeizhiYan 478→68 converter is MIT [13] 📄; its table was not read.
- iBUG/300-W annotations, and the dlib model trained on them, are research-only [14][19] ✅.
- FLAME is non-commercial except FLAME 2023 Open, which is CC BY 4.0 [22][23] ✅. Embedding files ride on FLAME/MPI terms ↔️.

## Numbers & reference tables

All indices are 0-based. "R / L" means the subject's right / left. MediaPipe mappings are candidates until calibrated. The full row-level tables are in `research/data/landmark-index-correspondence.json`.

**Table 1: Scheme cards and redistributability**

| Scheme | Points | Convention | Frame, units | Index-list licence | Status |
|---|---|---|---|---|---|
| MediaPipe Face Landmarker | 478 = 468 + 10 iris [6][7] | 3D mesh, relative z | normalised image; z smaller = nearer [3] | Apache-2.0 | ✅ count; 🧠 licence |
| MP `canonical_face_model.obj` | 468 v, 468 vt, ≈898 tri | template | cm, y up, +z out, +x subject L | Apache-2.0 | 🧠 |
| iBUG / dlib 68 | 68 | 2D, jaw slides | px | annotations research-only [14][19] | ✅ |
| WFLW | 98 | 2D | px | research-only (dataset terms) | 🧠 |
| 300W-LP / AFLW2000-3D | 68 | 3D, fixed BFM vertices | px (+z) | research-only (300-W/AFLW/BFM) | 🧠 |
| FLAME embedding | 51 static + 17 × 79 bins | barycentric on FLAME | m, Y up, +X subject L | FLAME/MPI terms | ↔️ |
| MICA MP embedding | ≈105 | barycentric on FLAME | m | MPI non-commercial (believed) | ↔️ |
| ARKit `ARFaceGeometry` | 1,220 v / 2,304 tri | dense, fixed topology | m, +x face's left | Apple SDK; do not ship derived files | 🧠 |
| PeizhiYan converter | 478 → 68 | derived | — | MIT [13] | 📄 |

**Table 2: MediaPipe index → anatomy, with cross-scheme equivalents.** Type: fixed = pin; curve = slides along a polyline; contour = silhouette, re-associated per view; extremal = defined in a head frame.

| MP (R / L) | Engine name | Farkas | Type | Set | iBUG 68 | WFLW 98 | FLAME static | Status |
|---|---|---|---|---|---|---|---|---|
| 10 | forehead_top_mesh | ≠ tr | oval boundary | OVAL | — | — | — | 🧠 |
| 9 (8) | glabella | g′ | extremal (profile) | — | — | — | — | 🧠 |
| 168 (6) | nasion_soft | n′ / se | curve (dorsum) | NOSE | 27 | 51 | 10 | 🧠 |
| 1 (4) | pronasale | prn | extremal | NOSE | 30 | 54 | 13 | 🧠 |
| 2 (94) | subnasale | sn | fixed | NOSE | 33 | 57 | 16 | ↔️ |
| 98 / 327 (64 / 294) | subalare | sbal | fixed | NOSE | 31 / 35 | 55 / 59 | 14 / 18 | ↔️ |
| 129 / 358 (48 / 278) | alare | al | extremal (frontal) | — | — | — | — | ↔️ |
| 37 / 267 | crista_philtri | cph | fixed | LIPS | 50 / 52 | 78 / 80 | 33 / 35 | 🧠 |
| 0 | labrale_superius | ls (border) | fixed | LIPS | 51 | 79 | 34 | ↔️ |
| 61 / 291 | cheilion | ch | fixed | LIPS | 48 / 54 | 76 / 82 | 31 / 37 | 🧠 |
| 78 / 308 | commissure_inner | — | fixed | LIPS | 60 / 64 | 88 / 92 | 43 / 47 | 🧠 |
| 13 / 14 | stomion sup / inf | sto | fixed if lips closed | LIPS | 62 / 66 | 90 / 94 | 45 / 49 | 🧠 |
| 17 | labrale_inferius | li (border) | fixed | LIPS | 57 | 85 | 40 | ↔️ |
| 18 (200) | sublabiale | sl | extremal (profile) | — | — | — | — | 🧠 |
| 199 (175) | pogonion_soft | pg′ | extremal (profile) | — | — | — | — | 🧠 |
| 152 | menton_soft | me′ (Farkas gn) | contour | OVAL | 8 | 16 | dyn 8 | ↔️ |
| 33 / 263 | exocanthion | ex | fixed | EYE | 36 / 45 | 60 / 72 | 19 / 28 | 🧠 |
| 133 / 362 | endocanthion | en | fixed + offset | EYE | 39 / 42 | 64 / 68 | 22 / 25 | 🧠 |
| 159 / 386 | lid_upper_apex | ps | curve | EYE | ≈37–38 / 43–44 | 62 / 70 | — | 📄 [9][10] |
| 145 / 374 | lid_lower_apex | pi | curve | EYE | ≈40–41 / 46–47 | 66 / 74 | — | 📄 [9][10] |
| 468 / 473 | iris_centre | ≈ p | gaze-dependent | IRIS | — | 96 / 97 | — | ↔️ |
| 107 / 336 | brow_inner | — | curve end | BROW | 21 / 22 | 37 / 42 | 4 / 5 | 🧠 |
| 105 / 334 | brow_peak | ≈ sci | curve | BROW | ≈19 / 24 | 35 / 44 | 2 / 7 | 🧠 |
| 70 / 300 | brow_outer | — | curve end | BROW | 17 / 26 | 33 / 46 | 0 / 9 | 🧠 |
| 234 / 454 | cheek_lateral | ≈ zy′ | contour | OVAL | ≈1 / 15 | ≈2 / 30 | dyn 1 / 15 | 🧠 |
| 127 / 356 | face_side_upper | ≠ t | contour | OVAL | ≈0 / 16 | 0 / 32 | dyn 0 / 16 | 🧠 |
| 172 / 397 (58 / 288) | gonial_region | ≈ go′ | contour | OVAL | ≈5 / 11 | ≈10 / 22 | dyn | ↔️ |

**Table 3: Ordered MediaPipe polylines (from the connection sets).** Mirror pairs are R/L values in the same position.

| Polyline | R side (subject) | L side | Status |
|---|---|---|---|
| Face oval, closed (36) | 10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288, 397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136, 172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109 | (one ring; 338…377 = L half) | 🧠 |
| Upper lid, outer→inner | 33, 246, 161, 160, 159, 158, 157, 173, 133 | 263, 466, 388, 387, 386, 385, 384, 398, 362 | 🧠 |
| Lower lid, outer→inner | 33, 7, 163, 144, 145, 153, 154, 155, 133 | 263, 249, 390, 373, 374, 380, 381, 382, 362 | 🧠 |
| Brow upper / lower, outer→inner | 70, 63, 105, 66, 107 / 46, 53, 52, 65, 55 | 300, 293, 334, 296, 336 / 276, 283, 282, 295, 285 | 🧠 |
| Upper lip outer, R→L | 61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291 | — | 🧠 |
| Lower lip outer, R→L | 61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291 | — | 🧠 |
| Upper lip inner, R→L | 78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308 | — | 🧠 |
| Lower lip inner, R→L | 78, 95, 88, 178, 87, 14, 317, 402, 318, 324, 308 | — | 🧠 |
| Nose outline (NOSE set) | 4, 45, 220, 115, 48, 64, 98, 97, 2 | 4, 275, 440, 344, 278, 294, 327, 326, 2 | 🧠 |
| Iris centre + ring | 468; 469–472 | 473; 474–477 (ring order: derive) | ↔️ |

**Table 4: Block correspondences** (candidates; the full 68-row list is in the data file)

| iBUG 68 | WFLW 98 | MediaPipe candidate | FLAME | Note | Status |
|---|---|---|---|---|---|
| 0–16 jaw | 0, 2, …, 32 | 127, 234, 93, 132, 58, 172, 136, 149, 152, 378, 365, 397, 288, 361, 323, 454, 356 | dynamic 0–16 | better: arc-length resample of the visible oval | 🧠 / 📄 [20] |
| 17–26 brows | 33–37, 42–46 | mean of upper and lower rows, e.g. (70+46)/2 | static 0–9 | iBUG brow sits on the arc centre or top by dataset [14] | 🧠 |
| 27–30 dorsum | 51–54 | 168, 197, 5, 1 | static 10–13 | equal steps 168→1 | 🧠 |
| 31–35 nose base | 55–59 | 98, 97, 2, 326, 327 | static 14–18 | alar choice ↔️ | ↔️ |
| 36–47 eyes | 60, 61, 63, 64, 65, 67; 68, 69, 71, 72, 73, 75 | 33, 160, 158, 133, 153, 144; 362, 385, 387, 263, 373, 380 | static 19–30 | thirds of the lid polylines | 🧠 |
| 48–59 outer lip | 76–87 | 61, 40, 37, 0, 267, 270, 291, 321, 314, 17, 84, 91 | static 31–42 | | 🧠 |
| 60–67 inner lip | 88–95 | 78, 81, 13, 311, 308, 402, 14, 178 | static 43–50 | | 🧠 |

**Table 5: Detector point vs anthropometric definition.** Offsets are estimates or derived bounds, not measurements; calibrate them.

| Point | Detector idx (MP; 68) | Definition | Expected systematic offset | Pin / slide | Status |
|---|---|---|---|---|---|
| en | 133/362; 39/42 | medial lid junction [33][34] | 0–3 mm per side, usually lateral (caruncle/sclera edge), so en–en reads up to ~6 mm wide (≤ ~19 % of ~32 mm) | pin + calibrated offset | ↔️ |
| ex | 33/263; 36/45 | lateral lid junction [33][34] | 0–2 mm medial with lateral hooding; grows with age | pin | 🧠 |
| prn | 1/4; 30 | most anterior nasal tip [31] | highlight pull ≤ R·θ/2 ≈ 1.5–5 mm toward the key light (R 6–10 mm, θ 30–60°) | pin σ 2–2.5 mm; recompute extremal after each pose | ↔️ |
| sn | 2/94; 33 | columella–lip junction; definitions differ [31][32][33] | 0–2 mm vertical, shadow-driven | pin | ↔️ |
| ls | 0; 51 | vermilion-border midpoint vs most prominent point [32][33] | 1–3 mm between the two definitions | pin to a declared variant | ↔️ |
| ch | 61/291 vs 78/308; 48/54 | commissure [33][34] | outer and inner corners 1–4 mm apart | pin | 🧠 |
| me′ / gn | 152; 8 | lowest chin point vs ceph Gn midway Pog–Me [29][30][31] | silhouette slides ≈1.3–2.6 mm per 5° pitch (chin R 15–30 mm) | slide | ↔️ |
| zy′ | 234/454; ≈1/15 | most lateral cheek point | ≈3.5–7 mm per 5° yaw (R 40–80 mm) | slide (silhouette) | 🧠 |
| go′ | 172/397 or 58/288; ≈4–5/11–12 | mandibular angle [29][30] | 5–10 mm along the border; error runs along go–me [35] | slide | ↔️ |
| n′ | 168/6; 27 | nasofrontal depth over nasion | 2–5 mm vertical ambiguity | curve (vertical free) | 🧠 |
| brows | 105/334 etc.; 17–26 | hair, not the supraorbital rim | subject-dependent | curve, low weight | 🧠 |
| iris centre | 468/473; — | limbus centre, moves with gaze | ≈2 mm per 10° of gaze (eye radius ≈12 mm) | latent eyeball + gaze | 🧠 |
| 10 | 10; — | mesh top, not trichion | subject-dependent | never use as tr | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Freeze conventions first.** Use one scheme file per detector version: 0-based, subject-relative L/R, explicit `mirrored` and EXIF flags. Store the vendored connection sets and a model hash. Convert 1-based paper indices on import 🧠.
2. **Build the labelled canonical mesh.**
   - Import `canonical_face_model.obj` with the default axes (Forward −Z, Up Y). That maps (x, y, z) → (x, −z, y), so the face looks down −Y and the subject's left is +X, `.L`. Scale ×10 for engine mm or ×0.01 for metres 🧠.
   - Enable Developer Extras, then Overlays → Indices, to read vertex numbers in Edit Mode 🧠.
   - Assert: 468 vertices; v[263].x > 0 > v[33].x; v[1] is the most forward midline vertex; midline |x| < 0.01 cm; the mirror permutation is an involution; set sizes are 36/40/16/16/10/10.
   - Create vertex groups per set and `LM.<abbr>.L/R` empties for Table 2.
3. **Wink test on the subject.** Ask the subject to close their own left eye. The `LEFT_EYE` ring should collapse and `eyeBlinkLeft` should rise. Also check that x(263) > x(33) on an upright, unmirrored face. If either fails, the image is mirrored [1] 🧠.
4. **Calibrate detector semantics.**
   - Use a consented, photoreal head of known geometry: a scan, or a textured MPFB2 head. Hand-place the Farkas landmarks on it.
   - Render yaw −60…+60° in 10° steps, × pitch −15/0/+15°, × key light at 0/45/90°, at 85 mm equivalent and 1.5 m.
   - Run the detector in IMAGE mode, out of process. Ray-cast every detection into the mesh with the known camera.
   - Per index, record the mean offset in the local tangent frame and the spread of hits across yaw.
   - Classify each index: **fixed** if spread < 1.5 mm with no trend; **curve** if the spread is along one tangent; **sliding** if the hit moves monotonically > 3 mm with yaw or sits on the silhouette. Use ≥ 3 different heads so one head's anatomy does not become "detector bias" 🧠.
5. **Per photo.** Before trusting en–en, nose width or mouth width, overlay the corrected points on the photo at 400 %. Gate on closed lips for sto, li and ch, and on open eyes for en and ex 🧠.
6. **What goes wrong.**
   - L/R swaps (selfies, iris naming).
   - Off-by-one errors from 1-based tables.
   - Forgetting the W/H anisotropy of normalised coordinates.
   - Treating MediaPipe z as depth.
   - Pinning 0–16 or `FACE_OVAL` as tissue.
   - Reading 10 as the hairline, 127/356 as tragion, or the jaw corner as gonion.
   - Mixing FLAME 2020 embeddings with 2023 bases, or forgetting the MICA mm ×1000 [25].

## Algorithmic implications

- **Registry, not constants.** Use `Scheme{name, detector_version, n, mirror_perm[n], midline[], polylines{}, semantics{idx: (engine_name, farkas, kind ∈ fixed|curve|contour|extremal|none, variant, sigma_n_mm, sigma_t_mm)}, licence}`. Branch on `scheme`, never on N 🧠.
- **Embeddings everywhere.** Use `Embedding{scheme, template, template_version, tri[n], bary[n,3], offset_local[n,3], cov_local[n,3,3]}`, FLAME's pattern generalised to MPFB2 or any base mesh. Regenerate it whenever topology changes 🧠.
- **Residuals by kind.**
  - Fixed: reprojection with Σ = R·diag(σn², σt²)·Rᵀ.
  - Curve: point-to-projected-polyline normal distance, with σt = 3–5 × σn.
  - Contour: silhouette distance. Re-associate by arc length to the template's occluding contour in every Gauss-Newton iteration.
  - Extremal: argmax ⟨p, d⟩ in the current head frame, softened at about 1–2 mm.
- **Continuous dynamic contour.** FLAME's 79-bin, ±39° table is a discrete version of the same silhouette idea 🧠. Interpolate across bins, or compute the silhouette directly, so beyond ±39° you do not get a frozen, wrong jaw.
- **Default σ (mm, before the N_eff inflation in `landmark-detection.md`)** 🧠:

| Class | σ normal | σ tangent |
|---|---|---|
| Sharp junction (en, ex, ch, sn, closed sto) | 1.0–1.5 | 1.0–1.5 |
| Extremal (prn, pg′) | 1.5–2.5 | 2–4 |
| Lid / lip / dorsum curve | 1.0–2.0 | 5 or free |
| Oval / 2D jaw | 2–3 | free (silhouette) |
| Brows | 3–5 | free |
| MediaPipe z | ≥ 10 or off | — |

- **Apply the calibrated offset, then shrink it.** Use offset_used = w·offset_calib, with w = n_heads/(n_heads + 2). Add the calibration spread to Σ in quadrature 🧠.
- **Mirror and L/R from geometry.** Compute mirror_perm by reflecting the canonical mesh (x → −x, nearest vertex, tolerance 0.5 mm). Pair irises by which eye ring contains each centre. Flag mirroring by the sign of x(263) − x(33) relative to the roll-corrected face axis 🧠.
- **Scale prior.** Iris diameter 11.7 ± 0.5 mm [11] 📄, giving about ±4 % per eye and about ±3 % for both eyes combined 🧠. Treat iris centres as gaze-dependent, never as shape landmarks.
- **Cross-scheme conversion at the semantic level.** Convert MediaPipe → 68 through Table 2 kinds. A converted jaw is a 3D-convention contour, never interchangeable with dlib's 2D jaw statistics 🧠.
- **CI tests.** Set sizes, involution, midline fixed points under mirror_perm, the canonical x-sign check, and a WFLW→68→WFLW round trip on non-jaw points 🧠.

## Disagreements, myths & open questions

- **Iris naming** ↔️ [9][10]: geometry decides.
- **Alare** (129/358 vs 48/278 vs 64/294) ↔️ and **subnasale** (2 vs 94) ↔️: calibrate, then pick.
- **Is the MediaPipe oval fixed or sliding?** ↔️ It is a fixed mesh vertex by construction. In practice, far-side oval points hug the visible outline beyond about 15–20° of yaw. Treat it as contour.
- **ls, sn and gn definitions** conflict [29][31][32][33] ↔️. Store the variant with every point.
- **Myth: `LEFT_EYE` = image left.** It is the subject's left [1].
- **Myth: "a 478→68 converter makes MediaPipe a 68-point detector."** The semantics differ at the jaw [21].
- **Myth: FLAME's 51 statics are anthropometric points.** They are iBUG semantics, embedded once by a fit.
- **Open questions:**
  - PeizhiYan's actual table [13].
  - MICA's exact count and file keys.
  - Whether FLAME 2023 Open ships embeddings [22].
  - The ARKit vertex semantics and licence terms.
  - Measured MediaPipe offsets by yaw. No published per-index offset table was found; the calibration above produces one.

## Sources

[1] Google AI Edge — Face Landmarker documentation — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[2] MediaPipe FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — official docs — n.d.
[3] MediaPipe 3D Face Transform (Google Developers Blog) — https://developers.googleblog.com/en/mediapipe-3d-face-transform/ — official blog — n.d.
[4] MediaPipe Face Mesh docs (google-ai-edge/mediapipe) — https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md?plain=1 — official docs — n.d.
[5] MediaPipe Face Mesh (legacy docs mirror) — https://mediapipe.readthedocs.io/en/latest/solutions/face_mesh.html — official docs — n.d.
[6] yakhyo/mediapipe-face-mesh-onnx README — https://github.com/yakhyo/mediapipe-face-mesh-onnx/blob/main/README.md — repo — n.d.
[7] cornpip/mediapipe_face_mesh — https://github.com/cornpip/mediapipe_face_mesh — repo — n.d.
[8] MediaPipe Face Mesh: All 478 Landmark Points (DEV Community) — https://dev.to/metsander/mediapipe-face-mesh-all-478-landmark-points-5ec8 — blog — n.d.
[9] MediaPipe face-mesh constants, mp_constants.py (Hugging Face Space) — https://huggingface.co/spaces/Akjava/mediapipe-face-skin-transform/blob/refs%2Fpr%2F1/mp_constants.py — code — n.d.
[10] MediaPipe face mesh landmark indices cheat sheet (HackerNoon) — https://hackernoon.com/mediapipe-face-mesh-landmark-indices-cheat-sheet — developer guide — n.d.
[11] MediaPipe Iris: Real-time Iris Tracking & Depth Estimation (Google Research blog) — https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/ — official blog — 2020
[12] google-ai-edge/mediapipe issue #6204 (`mp.solutions` missing from 0.10.30) — https://github.com/google-ai-edge/mediapipe/issues/6204 — issue tracker — 2026
[13] PeizhiYan/Mediapipe_2_Dlib_Landmarks — https://github.com/PeizhiYan/Mediapipe_2_Dlib_Landmarks/ — repo — n.d.
[14] iBUG facial point annotations — https://ibug.doc.ic.ac.uk/resources/facial-point-annotations/ — official docs — n.d.
[15] 300 Faces In-the-Wild Challenge (300-W) — https://ibug.doc.ic.ac.uk/resources/300-W — official docs — 2013
[16] PyImageSearch: Detect eyes, nose, lips, and jaw with dlib — https://pyimagesearch.com/2017/04/10/detect-eyes-nose-lips-jaw-dlib-opencv-python/ — blog — 2017
[17] PyImageSearch: (Faster) facial landmark detector with dlib — https://pyimagesearch.com/2018/04/02/faster-facial-landmark-detector-with-dlib/ — blog — 2018
[18] librealsense2 markup_68.h source — https://docs.ros.org/en/kinetic/api/librealsense2/html/markup__68_8h_source.html — code docs — n.d.
[19] davisking/dlib-models README — https://github.com/davisking/dlib-models — repo — n.d.
[20] NeoLoc-68: 68-point neonatal facial landmark localisation — https://arxiv.org/pdf/2606.20823 — preprint — 2026
[21] Infinite 3D Landmarks: Improving Continuous 2D Facial Landmark Detection — https://arxiv.org/pdf/2405.20117 — preprint — 2024
[22] FLAME project site — https://flame.is.tue.mpg.de/ — official site — n.d.
[23] FLAME model licence — https://flame.is.tue.mpg.de/modellicense.html — licence — n.d.
[24] Zielon/MICA — https://github.com/Zielon/MICA — repo — n.d.
[25] Zielon/MICA demo.py — https://www.github.com/Zielon/MICA/blob/master/demo.py — source code — n.d.
[26] peizhiyan/flame-head-tracker — https://github.com/peizhiyan/flame-head-tracker — repo — 2025
[27] VGCLUB/facefit-mpfb — https://github.com/VGCLUB/facefit-mpfb — repo — n.d.
[28] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d.
[29] Columbia University craniology slides — https://columbia.edu/itc/hs/medical/humanAnatomy/yuan/craniologyISlides_files/slide0061.html — lecture slides — n.d.
[30] Grand Valley State, Introduction to Human Osteology — https://pressbooks.gvsu.edu/introhumanosteology/?p=60 — textbook — n.d.
[31] Nobel Biocare: Definition of 3D cephalometric soft tissue landmarks — https://nobellicense.nobelbiocare.com/help/d3d046fb-52e8-4b33-9f51-d3fd98ca3ed4/2.0/EN/3D_cephalometric_soft_tissue_landmarks.htm — commercial docs — n.d.
[32] Clinical Equivalence of a CNN-Based Automated Soft Tissue Landmark Detection System on 2D Facial Images — https://pmc.ncbi.nlm.nih.gov/articles/PMC13205844/ — paper — n.d.
[33] Facial Anthropometry and Analysis in Egyptian Women — https://pmc.ncbi.nlm.nih.gov/articles/PMC9116947/ — paper — n.d.
[34] Facial Landmarks Determination with Different Digital Scanners: An In Vivo Study — https://pmc.ncbi.nlm.nih.gov/articles/PMC12941515/ — paper — n.d.
[35] Accuracy and reliability of automated landmark identification on CBCT using Invivo software — https://pmc.ncbi.nlm.nih.gov/articles/PMC12418967/ — paper — 2025

Uses not marked inline: [4] and [15] are the official homes of the MediaPipe Face Mesh and 300-W definitions. [26] uses MediaPipe and FLAME, with FLAME files downloaded separately for licensing reasons 📄. [27] fits MPFB2 using 57 "stable" MediaPipe points 📄, a precedent for a rigid subset. [28] documents ARKit blendshape coefficients in [0, 1] 📄.

**Further reading (by name, not yet linked)**
- MediaPipe source files `face_mesh_connections.py`, `canonical_face_model.obj`, `canonical_face_model_uv_visualization.png`, `geometry_pipeline_metadata_landmarks.pbtxt` (google-ai-edge/mediapipe).
- Kartynnik et al., Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs, CVPR Workshops 2019; Grishchenko et al., Attention Mesh, 2020.
- Sagonas et al., 300 Faces In-The-Wild Challenge: database and results, Image and Vision Computing 2016.
- Wu et al., Look at Boundary (WFLW), CVPR 2018.
- Zhu et al., Face Alignment Across Large Poses: A 3D Solution (300W-LP, AFLW2000-3D), CVPR 2016; Bulat & Tzimiropoulos, How far are we from solving the 2D & 3D Face Alignment problem? (LS3D-W), ICCV 2017.
- Li, Bolkart, Black, Li, Romero, Learning a model of facial shape and expression from 4D scans (FLAME), SIGGRAPH Asia 2017; Sanyal et al., RingNet, CVPR 2019; Feng et al., DECA, SIGGRAPH 2021.
- Zielonka, Bolkart, Thies, Towards Metrical Reconstruction of Human Faces (MICA), ECCV 2022.
- Apple Developer documentation: ARFaceAnchor, ARFaceGeometry.
- Farkas, Anthropometry of the Head and Face, 2nd ed., 1994.
- Bookstein, Morphometric Tools for Landmark Data, 1991; Gunz & Mitteroecker, Semilandmarks, Hystrix 2013.
