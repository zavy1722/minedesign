# Photogrammetry of human heads

> Photogrammetry (structure-from-motion, SfM, then multi-view stereo, MVS) can recover a head to well under a millimetre: at head-portrait resolution, triangulation precision is about 0.05–0.25 mm. On a live sitter the error budget is set instead by **non-rigid motion** (blinks, lips, jaw, gaze), **skin shine and low texture**, and **materials MVS cannot see** (hair, eyes, lashes), far more than by the choice of COLMAP, Meshroom/AliceVision, RealityScan/RealityCapture or Metashape. A synchronised multi-camera rig removes the motion problem; a single camera works if each ring of photos takes ≤20–30 s, the background is masked or plain, and expression and gaze are held fixed. For likeness sculpting, the scan supplies trustworthy mid-face and profile depth plus absolute size (given a scale reference), while eyes, hair, ear backs and lip edges must be rebuilt by hand. With no harvest or prior draft for this topic, every item is expert knowledge or camera arithmetic, cross-referenced to sibling notes.
>
> Evidence status: 0 ✅ / 0 📄 / 59 🧠 / 16 ↔️ — 🧠 items are queued for web verification.

## Key facts

**What the solver needs**
- **SfM assumes one rigid scene.** It matches keypoints, solves cameras and sparse points by bundle adjustment, and recovers shape **only up to a similarity transform**, so absolute size needs a scale reference. MVS then computes per-view depth maps, fuses them and meshes the result (Poisson or Delaunay/graph-cut) 🧠
- **Each surface point should be seen sharply in at least 3 images**, with 10–30° between neighbouring views. Below about 5° parallax, depth is poorly conditioned; above about 30–40°, skin appearance changes too much to match reliably 🧠
- **Skin matches well only at fine sampling.** At ≤0.1 mm/px (ground sample distance, GSD) pores give cheeks and forehead enough texture; at ≥0.2–0.3 mm/px they turn into "orange peel" noise 🧠
- **Geometry is not the bottleneck.** Depth σ ≈ GSD·σ_px / (√2·sin(α/2)) (α = angle between views) gives about 0.16 mm at 0.1 mm/px, 0.3 px noise and α = 15° (Table 4), so observed 0.5–2 mm errors come from motion, skin matching and regularisation 🧠

**The subject-movement problem**
- **Rigid head motion against a textured background** gives two rigid bodies. The solver locks onto the dominant one (often the room), and the head comes out blurred, doubled or missing 🧠
- **Rigid head motion against a masked or plain background is harmless:** it is absorbed into the camera poses (the turntable principle). That is why masks are applied *before* alignment 🧠
- **Non-rigid motion cannot be absorbed.** Blinks (about 10–20/min), eyelid height, lip seal, jaw drop, brow and gaze shifts, and breathing-driven neck and shoulder motion produce doubled edges, noise or averaged shapes. At 0.05–0.15 mm/px, **1 mm of motion is 7–20 px**, while MVS photo-consistency tolerates about 1–2 px. Hence ≤20–30 s per ring and ≤1–3 min in total 🧠
- **Synchronised rigs remove the problem.** One trigger plus a strobe (flash duration ≤1/1000 s) freezes the subject. Typical counts: face only (ear to ear) 8–16 cameras, full head 24–60, full body 80–200 ↔️ (counts vary widely by studio)

**Capture choices**
- **Move the camera, not the person.** If the sitter rotates (swivel chair), the lighting moves across the face, and both matching and texture suffer unless the light is perfectly even ↔️
- **Fix the gaze.** The sitter looks at a mark straight ahead and does *not* follow the camera; eye rotation changes eyelid and brow shape between views 🧠
- **Depth of field is shallow** (about 6.5 cm at f/8 for a 40 cm full-frame field, Table 3), but each region is reconstructed mainly from views facing it. Focus on the nearest cheek or eye, not the nose tip 🧠
- **Diffraction caps stopping down:** the sweet spot is f/8–f/11 on full frame (FF), f/5.6–f/7.1 on APS-C and f/4–f/5.6 on Micro Four Thirds 🧠
- **Smartphones.** Use the 2–3× lens (about 48–77 mm equivalent) at 0.8–1.2 m; the 24–26 mm main lens forces 0.3–0.5 m, the most distorting range. Lock exposure, focus and white balance; turn off HDR, night, beauty and portrait modes; use a manual app so the phone cannot **auto-switch lenses** (each lens has its own intrinsics). Optical stabilisation shifts the principal point slightly per shot 🧠
- **Video** (4K, about 8 MP) is fast, but rolling shutter skews fast pans, default 1/50–1/60 s shutters blur, and compression erases pores: use ≥1/250 s, a slow orbit, and only sharp, non-blink frames 🧠
- **Phone depth sensors.** The front TrueDepth structured-light camera gives quick but smooth face scans; rear LiDAR is too coarse for facial features (`community/reddit-face-from-photos.md`) ↔️

**Lighting and surfaces**
- **Even, diffuse light** (overcast, open shade, large softboxes) minimises moving highlights and baked shadows 🧠
- **Cross-polarisation** (linear film on the lights, lens polariser at 90°) removes surface specular, improving both matching and albedo at a cost of 2–3 stops. Extinction is good only for near-axis lights, so a single moving camera works best with a polarised ring or on-axis flash (`blender/skin-shading.md`) 🧠
- **Failing materials.** Corneas reconstruct flat, concave or noisy; hair, beards, brows and lashes form blobs **outside** the skin; nostrils, ear backs, conchae, under-chin and lip seal are occluded; T-zone shine causes holes and bumps 🧠
- **Mitigations:** matte powder; a wig or swim cap (adds about 1–3 mm and compresses hair) or wet slicked hair; glasses and earrings off; lips together, teeth lightly touching as a repeatable rest position 🧠

**Software (time-sensitive; verify versions, prices, licences)**
- **COLMAP:** BSD-licensed, scriptable reference SfM/MVS; the dense PatchMatch stage needs an NVIDIA CUDA GPU. GLOMAP (global SfM, 2024) is faster; check whether current COLMAP releases include it 🧠
- **Meshroom/AliceVision:** MPL-2.0 node graph, CUDA for depth maps. Cameras missing from its sensor database get a default field of view (reportedly 45°), a common cause of failed head scans 🧠
- **RealityCapture:** very fast and detailed; Windows; NVIDIA CUDA for meshing. Epic made it free below about US$1 M annual revenue (2024) and, as I understand it, renamed it **RealityScan 2.0** in 2025 ↔️ (verify)
- **Agisoft Metashape:** Standard and Professional perpetual licences; Windows, macOS and Linux with any GPU. Markers, scale bars, coded targets and Python are, I believe, Professional-only 🧠 (verify)
- **Apple Object Capture** and phone apps (Polycam, KIRI Engine, Scaniverse) are object-tuned, with little mask or camera control 🧠
- **Gaussian splats and NeRFs** render photoreal heads but are not sculpt-ready meshes; mesh-extraction variants (2DGS and successors) are improving ↔️

## Numbers & reference tables

**Table 1 — Single-camera live-sitter recipe** (adult, still photos)

| Parameter | Value | Why | Badge |
|---|---|---|---|
| Rings | 3–4: low (−20 to −30°), eye level, high (+30 to +45°), optional top | jaw underside, nostrils, crown | 🧠 |
| Angular step | 10–20° (18–36 stations per full ring) | ≥3 views per point, 60–80% overlap | 🧠 |
| Photos | 60–120 full head; 30–50 face only; +10–20 ear, nostril, top details | coverage vs time | 🧠 |
| Time per ring / total | ≤20–30 s / ≤1–3 min | non-rigid drift | 🧠 |
| Distance, FF focal | 0.8–1.5 m, 50–105 mm | ≤0.1 mm/px, low perspective | 🧠 |
| Aperture (FF) | f/8–f/11 | DoF vs diffraction (Table 3) | 🧠 |
| Shutter | ≥1/200 s handheld, or strobe | blur ≤1 px | 🧠 |
| ISO | 100–400 (phone: lowest) | noise kills skin matching | 🧠 |
| Format | RAW; manual exposure and WB | consistent texture | 🧠 |

**Table 2 — GSD (mm/px) by sensor and framed field** (long side; GSD = field ÷ pixels; arithmetic)

| Sensor (long-side px) | 300 mm field | 400 mm | 600 mm | Badge |
|---|---|---|---|---|
| 12 MP phone (4032) | 0.074 | 0.099 | 0.149 | 🧠 |
| 24 MP FF (6000) | 0.050 | 0.067 | 0.100 | 🧠 |
| 45 MP FF (8192) | 0.037 | 0.049 | 0.073 | 🧠 |
| 61 MP FF (9504) | 0.032 | 0.042 | 0.063 | 🧠 |

Phone optics and processing typically resolve only 50–70% of nominal pixels ↔️.

**Table 3 — Total depth of field (mm), FF, DoF ≈ 2Nc(1+m)/m²** (c = 30 µm "print" / 12 µm ≈ 2 px at 24 MP; arithmetic)

| f-number | 300 mm field (m = 0.12) | 400 mm field (m = 0.09) | Airy disc, px at 24 MP | Badge |
|---|---|---|---|---|
| 5.6 | 26 / 10 | 45 / 18 | 1.3 | 🧠 |
| 8 | 37 / 15 | 65 / 26 | 1.8 | 🧠 |
| 11 | 51 / 21 | 89 / 36 | 2.5 | 🧠 |
| 16 | 75 / 30 | 129 / 52 | 3.6 | 🧠 |

**Table 4 — Precision vs motion** (GSD 0.1 mm/px, 0.3 px matching σ; arithmetic)

| Angle between views | 5° | 10° | 15° | 20° | 30° | 45° | Badge |
|---|---|---|---|---|---|---|---|
| Two-view depth σ (mm) | 0.49 | 0.24 | 0.16 | 0.12 | 0.08 | 0.06 | 🧠 |

| GSD (mm/px) | 0.05 | 0.067 | 0.10 | 0.15 | Badge |
|---|---|---|---|---|---|
| 1 mm non-rigid motion, in px | 20 | 15 | 10 | 6.7 | 🧠 |

**Table 5 — Typical surface accuracy vs a reference scan** (adult faces; ranges reflect study and vendor disagreement)

| Method | Central face | Periphery (ears, hairline, under chin) | Badge |
|---|---|---|---|
| Synchronised DSLR rig (≥40 cameras, cross-polarised strobes) | 0.1–0.5 mm, pore detail | 0.5–2 mm | ↔️ |
| Clinical stereophotogrammetry (3dMD/Vectra class) | ≈0.2–0.5 mm; landmark distances mostly within 1–2 mm of calipers (see Sources) | 1–2 mm | ↔️ |
| Single DSLR, still sitter, 60–120 photos | 0.5–2 mm | 2–5 mm | ↔️ |
| Smartphone stills | 1–3 mm | 2–6 mm | ↔️ |
| TrueDepth structured light | 0.5–2 mm, smoothed | 2–5 mm | ↔️ |
| Hair or beard surface vs underlying skin | 5–30 mm outward bias | — | 🧠 |

**Table 6 — Scale reference error** (σ_scale ≈ σ_ref ÷ length)

| Reference | Scale σ | On 150 mm head breadth | Badge |
|---|---|---|---|
| Scale bar 300 mm, ±0.5 mm | 0.17% | 0.25 mm | 🧠 |
| Scale bar 100 mm, ±0.5 mm | 0.5% | 0.75 mm | 🧠 |
| Caliper head breadth (eu–eu), ±1–2 mm | ~1% | 1–2 mm | 🧠 |
| Iris or IPD prior, no measurement | ~4–6% | 6–9 mm | 🧠 (see `reconstruction/multi-view-fitting.md`) |

**Table 7 — Camera exports for engine import** (conventions to verify by reprojecting sparse points)

| Tool | File | Pose | Intrinsics gotcha | Badge |
|---|---|---|---|---|
| COLMAP | `cameras.txt`, `images.txt` | quaternion QW QX QY QZ + T, world→camera; centre = −Rᵀt | first pixel centre at (0.5, 0.5), OpenCV at (0, 0) | 🧠 |
| Metashape | cameras XML | per-camera 4×4 transform (camera→chunk) plus chunk transform | cx, cy are offsets from the image centre; P1/P2 swapped vs OpenCV p1/p2 | 🧠 |
| RealityScan/RC | per-image XMP (`xcr:` namespace) | rotation matrix + position | focal as 35 mm equivalent; principal point normalised; Brown models | 🧠 |
| Meshroom | `cameras.sfm` (JSON) | 3×3 rotation + centre | principal-point convention varies by version | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Consent and comfort.** Get written consent for capture, storage and use (face scans are biometric data in many jurisdictions); screen for photosensitivity before repeated flash.
2. **Prepare the sitter.** Powder the T-zone; cap or slicked hair (log which); no glasses or earrings; plain top. Neutral face, lips together, teeth lightly touching, gaze on a mark at eye height. A headrest at the occiput helps; shoot the back of the head as a separate pass.
3. **Set the camera.** Manual exposure and WB, zoom taped, ISO ≤400, f/8–f/11 FF, ≥1/200 s or strobe; focus by keeping a constant distance. On phones, lock the 2–3× lens.
4. **Shoot rings** per Table 1: the sitter breathes out and holds for each ring and blinks between frames, against a plain backdrop or with masks planned.
5. **Put scale on the head, not the room.** A scale bar on a stand is valid only if the head stays still relative to it; once masks remove the room to absorb sway, the bar goes too. Also caliper head breadth (eu–eu) and bizygomatic breadth; references disagreeing by >1% signal a problem.
6. **Process.**
   - **Metashape:** align on High with masks applied to key points; gradual-select tie points (reprojection error to about 0.3–0.5 px, removing ≤10–20% per pass); optimise f, cx, cy, k1–k3, p1, p2; depth maps on High or Ultra with **Mild** filtering, which keeps fine detail.
   - **RealityScan:** check that one component holds all images; set a tight reconstruction region; High detail.
   - **COLMAP:** `--ImageReader.single_camera 1`, an `OPENCV` or `SIMPLE_RADIAL` model and `--ImageReader.mask_path`; exhaustive matching (<300 images), `mapper`, `image_undistorter`, `patch_match_stereo`, `stereo_fusion`, then a mesher.
   - **Meshroom:** add the sensor width if missing, supply masks, depth-map downscale 1 (defaults vary by version).
7. **Import.** Keep 1 BU = 1 m at true size (vertex–menton about 0.21–0.24 m; adult head breadth about 140–160 mm as a sanity check). Orient to the Frankfurt horizontal (porion–orbitale) and the midsagittal plane.
8. **Clean up.** Keep the raw mesh for baking. On a copy: Decimate (Collapse) to 1–2 M triangles, delete small loose islands, fill holes, and voxel remesh at 0.5–1 mm for a watertight sculpt proxy (about 1 M faces at 0.5 mm). Smooth noise on cheeks and forehead only; mask the philtrum, alar grooves, eyelid creases and vermilion border.
9. **Rebuild what MVS cannot see:** eyes as spheres (axial length about 24 mm, visible iris about 11.7 mm), eyelid margins from photos, a scalp sculpted *inside* the hair blob with hair as cards or curves, ear backs from profile photos (`anatomy/ear.md`).
10. **Wrap and bake.** Wrap a 5–20 k-quad base onto the scan (landmarks plus non-rigid ICP, below; or Shrinkwrap plus Multires Reshape), add 4–5 Multires levels, and bake normals and displacement from the raw scan (Selected to Active, extrusion about 1–3 mm). Keep the solved cameras and photos for likeness checks (`blender/reference-camera-setup.md`).

**What goes wrong**

| Symptom | Cause | Fix |
|---|---|---|
| Doubled lips, eyelids or brows | non-rigid motion | shorter rings, fixed gaze, drop blink frames, cull views per region, rig |
| Head split into components or missing | rigid sway vs textured room | mask before alignment; plain backdrop |
| Holes or bumps on nose, forehead, cheekbones | specular shine | powder, cross-polarise, diffuse light |
| Orange-peel cheeks | coarse GSD, high ISO, phone denoising | closer framing, low ISO, RAW |
| Helmet cranium, bulging brows or beard | hair surface ≠ skin | cap; one-sided fit; sculpt the scalp |
| Missing jaw underside, nostrils, crown | no low or top ring | add rings |
| Bent or domed surface | zoom changed, lens switched, unknown sensor | lock zoom; one camera group per lens; fix sensor |
| Wavy skew (video) | rolling shutter | stills, or slow orbit at fast shutter |
| Blotchy texture seams | auto exposure or WB | manual settings; RAW |

## Algorithmic implications

- **Camera importer** (proposed `face3d/io/sfm_import.py`): COLMAP text, Metashape XML, RealityScan XMP and AliceVision `.sfm` → `Camera`. `Camera` models square pixels and k1, k2 only, so accept SIMPLE_RADIAL, RADIAL, PINHOLE, and OPENCV when |fx−fy|/f < 0.1% with negligible tangential terms; otherwise require the tool's undistorted images. `Camera.centered` uses cx = width/2, COLMAP's corner convention; OpenCV-convention sources need +0.5 px. **Validate every import** by reprojecting the tool's sparse points: the mean must match its reported error (<1 px) 🧠
- **Never let landmarks move SfM cameras.** Detector noise is about 1–1.5% of inter-ocular distance, i.e. 10–14 px at 0.067 mm/px, against about 0.5 px for SfM. Pass imported cameras with `estimate_focal=False` (or `f_prior_log_sigma` ≈ 0.005–0.01) and frozen poses (if refined: rotation σ ≈ 0.05°, centre σ ≈ 0.5 mm). Then `triangulate_points` → `umeyama` to the template 🧠
- **Scale as data:** a `ScaleRef` (two 3D points, length in mm, σ), combined by inverse variance, warning at >1% disagreement, plus the scale-mode tag from `multi-view-fitting.md` 🧠
- **Scan-to-template fitting:** `fit_template_to_landmarks`, then point-to-plane non-rigid ICP regularised by `laplacian_deform`/`ReducedDeformer`, stiffness high→low over 5–8 stages (Amberg et al. 2007). Reject correspondences beyond 3σ_region (coarse cap 10 mm, fine 3–5 mm), with normal angle >45°, or on scan boundaries; Huber at about 1.5σ. Residual σ: 0.3–0.5 mm (rigs); 0.5–1 mm (single camera: cheeks, forehead, nose, chin); 2–3 mm (ears, hairline, under chin) 🧠
- **Zero weight on unseen materials:** project face-parsing labels onto scan vertices by majority vote over visible views; exclude eyes, inner mouth, nostrils, brows, lashes, hair and beard 🧠
- **One-sided constraint under hair:** penalise the template only when it lies *outside* the hair surface, with a weak inward prior of about 5–15 mm (1–3 mm under a cap) 🧠
- **Weak symmetry for scans:** `Priors.sigma_sym` ≥ 3–5 mm instead of 2 mm, because the scan measures real asymmetry (`anatomy/facial-asymmetry.md`) 🧠
- **Coverage QA:** per template vertex, count views with incidence <60–70° and the largest pairwise triangulation angle; below 3 views or 10–15°, tag it prior-driven and show a heat-map in Blender 🧠
- **Motion QA:** inspect per-view, per-region residuals of rigidly triangulated landmarks; eye or mouth outliers >3σ mean a blink or expression change, so drop that view for that region only. Reject frames with eye aspect ratio <~0.2 (Soukupová & Čech 2016); rank sharpness by variance of the Laplacian 🧠
- **Capture planner:** from target GSD and sensor, compute distance, stations per ring (360°/step) and expected σ (Table 4) before shooting 🧠

## Disagreements, myths & open questions

- **"More photos is always better."** For a live sitter, extra photos cost time, and time costs non-rigid error. Coverage and speed beat count ↔️
- **Swivel chair vs orbiting camera.** A swivel chair works only with perfectly even light and masks; otherwise moving shading hurts ↔️
- **Which solver is best?** RealityScan has a reputation for speed and detail, Metashape for robustness and Mac support, COLMAP for openness and scripting, Meshroom for a free GUI. On heads, capture quality dominates. No head-specific benchmark is known to me ↔️
- **Accuracy claims.** Vendor sub-0.2 mm figures are system specs; independent face studies report larger landmark-level errors (Table 5) ↔️
- **Open questions** 🧠 (time-sensitive): do learned matchers (LightGlue) or feed-forward models (MASt3R, VGGT) help on low-texture skin and sparse views; will 2DGS-style meshes reach sculpt quality; current RealityScan and Metashape editions and prices; measured smartphone-vs-rig error on live sitters.

## Sources

None linked: no harvest exists for this topic yet. Sourced stereophotogrammetry accuracy figures live in `_raw/harvests/anthropometric-norms.json`.

**Further reading (by name, not yet linked)**
- Schönberger & Frahm, "Structure-from-Motion Revisited", CVPR 2016
- Schönberger, Zheng, Frahm & Pollefeys, "Pixelwise View Selection for Unstructured Multi-View Stereo", ECCV 2016
- Pan, Baráth, Pollefeys & Schönberger, "Global Structure-from-Motion Revisited" (GLOMAP), ECCV 2024
- Griwodz et al., "AliceVision Meshroom: An open-source 3D reconstruction pipeline", ACM MMSys 2021
- Jancosek & Pajdla, "Multi-View Reconstruction Preserving Weakly-Supported Surfaces", CVPR 2011
- Furukawa & Hernández, "Multi-View Stereo: A Tutorial", Foundations and Trends in Computer Graphics and Vision, 2015
- Kazhdan & Hoppe, "Screened Poisson Surface Reconstruction", ACM TOG 2013
- Beeler, Bickel, Beardsley, Sumner & Gross, "High-Quality Single-Shot Capture of Facial Geometry", SIGGRAPH 2010
- Ma et al., "Rapid Acquisition of Specular and Diffuse Normal Maps from Polarized Spherical Gradient Illumination", EGSR 2007
- Hartley & Zisserman, Multiple View Geometry in Computer Vision, 2nd ed., 2004
- Luhmann, Robson, Kyle & Boehm, Close-Range Photogrammetry and 3D Imaging, de Gruyter
- Brown, "Decentering Distortion of Lenses", Photogrammetric Engineering, 1966
- Amberg, Romdhani & Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007
- Soukupová & Čech, "Real-Time Eye Blink Detection using Facial Landmarks", CVWW 2016
- Huang et al., "2D Gaussian Splatting for Geometrically Accurate Radiance Fields", SIGGRAPH 2024
- Leroy, Cabon & Revaud, "Grounding Image Matching in 3D with MASt3R", ECCV 2024
- Wang et al., "VGGT: Visual Geometry Grounded Transformer", CVPR 2025
- Lindenberger, Sarlin & Pollefeys, "LightGlue: Local Feature Matching at Light Speed", ICCV 2023
