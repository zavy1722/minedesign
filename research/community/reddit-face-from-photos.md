# Reddit: face-from-photos problems and answers

> On r/blender, r/3Dmodeling, r/photogrammetry, r/ZBrush and r/computergraphics, "make a 3D head of a real person from photos" recurs constantly. Answers point to four routes: template photo-fitting, photogrammetry of a live sitter, sculpting by eye over references and, increasingly, AI image-to-3D. Experienced users agree no automatic route gives a finished likeness: each gives a base that a manual pass must correct for depth, proportions, eyes and hair. Recurring failures are about inputs more than tools: selfie perspective, unmatched front/side photos, mirrored or filtered phone images, sitter motion, hair, beards, eyes and shine. No Reddit thread was retrieved for this note, so everything is the author's synthesis of long-running discussion plus camera arithmetic: hypotheses to verify, not quotes.
>
> Evidence status: 1 ✅ / 1 📄 / 57 🧠 / 8 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Routes and verdicts**
- Asked how to model a real face from photos, the community gives three answers: a template fit (KeenTools FaceBuilder in Blender; Reallusion Headshot, Daz Face Transfer or FaceGen outside it), photogrammetry (RealityCapture/RealityScan, Metashape, Meshroom, phone apps), or sculpting by hand against references. AI image-to-3D is now a fourth answer, criticised almost as often as it is offered 🧠
- The most common verdict: auto-fits come out like "a relative of the person". They give topology, scale and texture; the likeness is still sculpted by eye 🧠
- FaceBuilder, the default Blender answer, is praised for camera-matched pins and textures from a few photos. Criticisms: subscription cost, pin effort in 3/4 and profile views, fixed topology, dependence on neutral, well-lit photos 🧠 (time-sensitive)
- AI image-to-3D tools (Meshy, Tripo, Rodin/Hyper3D, Hunyuan3D, TRELLIS, Stable Fast 3D) are judged fine for blockouts, concepts and small prints but weak on likeness: averaged, too-symmetric features, soft eyes and lips, baked lighting, an invented back of head and ears, triangle-soup topology. Promotional posts get a sceptical reception ↔️ (judgements go stale within months)

**Perspective and input defects**
- **Orthographic front and side planes** are the classic beginner failure: eye height, ears and chin never line up, because the photos differ in distance, focal length and head pitch. Advice: shoot from ≥1.5–2 m, camera at nose height, head level, or camera-match instead 🧠
- **Selfie distortion.** Arm's-length photos (about 0.3–0.6 m) make the nose and central face bigger and the face, jaw and ears smaller. Ward et al. (2018) modelled that the nasal base looks about 30% wider (nasal tip about 7%) at 12 in than at 5 ft 📄 [1] (corrected in verification: 30% applies to the nasal base, not overall nasal width; figure from press/university coverage, not the paper text)
- **Perspective depends on distance only.** "Telephoto flattens the face" is shorthand: at equal distance, focal length only crops. At ≥3 m the projection of a head is within about 4% of orthographic (Table 1) 🧠
- **Mirrored selfies.** Front cameras on some phones and apps save a mirrored image. This flips hair partings, moles and real asymmetry, and it breaks multi-view solves 🧠
- **Processed images.** Beauty, face-slimming and wide-angle face-correction modes, portrait-mode processing and social-media re-compression or cropping change geometry and strip EXIF. Use originals, filters off 🧠
- **Photos from different times disagree** (weight, hairstyle, beard, age). Use one session 🧠

**Photogrammetry of people**
- **One camera, one live sitter** works only if the person holds still for the 1–3 min of shooting; breathing, sway and blinks cause doubled edges and noisy eyes and lips. Studios use synchronised rigs of tens to over 100 cameras; DIY Raspberry Pi rigs are a recurring hobby build 🧠
- **Move the camera, not the person**, is the usual advice. A swivel chair can work only with flat, even light and a plain, masked background, so the solver cannot lock onto the room ↔️
- **Problem materials.** Hair, beards, brows and lashes, eyes, teeth, inner nostrils, backs of ears and under the chin come out as blobs or holes. Fixes: swim or bald cap or slicked hair, matte powder on oily skin, overcast or diffuse light (cross-polarised flash in studios), and rebuilding eyes and hair by hand 🧠
- **Phone depth sensors.** Rear iPhone LiDAR is called too coarse for faces; front TrueDepth scans (Heges and similar) are quick but soft; photo-mode photogrammetry gives more detail. Bellus3D, once the go-to face-scan app, shut down around 2021–22 🧠
- **Hardware limits.** RealityCapture and Meshroom's dense stage need NVIDIA CUDA, so Mac and AMD users are pointed to Metashape or Apple Object Capture apps 🧠 (time-sensitive)
- **Gaussian splat and NeRF captures** look photoreal but are not meshes; extracted meshes are noisy, so sculptors are told to use a photogrammetry mesh 🧠
- **Raw scans are not sculpt-ready** (millions of triangles, holes, noise). The standard answer is to wrap a clean base topology onto the scan (R3DS Wrap, Mesh to MetaHuman, Shrinkwrap, Instant Meshes or Quad Remesher) and project detail with Multires 🧠
- **Scale.** Photogrammetry has no inherent scale: put a ruler or target in shot, or measure a distance on the sitter 🧠

**Likeness craft (mostly r/ZBrush)**
- **Shape before detail.** Block big proportions and planes first; check silhouette, profile and 3/4; flip the canvas; judge at thumbnail size, where likeness is decided; compare against many photos from one period 🧠
- **Recurring critique points:** face too flat or head too shallow front-to-back; eyes not set deep enough under the brow; ears too high or too far forward; neck too thin or too vertical; cranium behind the ears too small 🧠
- **Symmetry.** Rough in with symmetry on, then turn it off: real asymmetry is part of the likeness ↔️ (the "uncanny symmetric face" claim is common, but its size is unmeasured)
- **3DMM methods.** Single-image 3DMM methods (DECA, EMOCA, MICA, SMIRK, Deep3DFaceRecon, 3DDFA_V2) score about 1.1–1.5 mm mean scan error on NoW, yet r/computergraphics users call their likeness weak: errors sit where identity lives (nose projection, eye depth, jaw), priors pull towards the training-set mean, and the FLAME and BFM licences are mostly non-commercial. See `reconstruction/single-image-regression.md` 🧠
- **Consent.** Requests to model an ex, a stranger or a celebrity draw warnings about consent and publicity rights. A deceased relative from a few old photos gets sympathy and the realistic answer "artist sculpt, not a scan" 🧠

## Numbers & reference tables

**Table 1 — Perspective magnification of nose tip relative to the ear plane** (pinhole arithmetic: ratio = (d+Δ)/d, d = camera-to-nose-tip; Δ = nose-tip-to-tragion depth, taken as 10–12 cm for adults 🧠)

| Camera distance d (m) | Typical situation | Nose/ear magnification ratio | Badge |
|---|---|---|---|
| 0.3 | close selfie | 1.33–1.40 | 🧠 |
| 0.5 | arm's-length selfie | 1.20–1.24 | 🧠 |
| 1.0 | phone held by another person; 85 mm headshot | 1.10–1.12 | 🧠 |
| 2.0 | 135–180 mm headshot | 1.05–1.06 | 🧠 |
| 3.0 | 200 mm+ telephoto | 1.033–1.040 | 🧠 |
| 5.0 | press/long-lens photo | 1.020–1.024 | 🧠 |

**Table 2 — Full-frame-equivalent focal length needed to frame a 40 cm-tall head-and-shoulders field** (f = 36 mm × d / 0.40 m; portrait orientation; arithmetic)

| d (m) | 0.3 | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 | Badge |
|---|---|---|---|---|---|---|---|
| f₃₅ (mm) | 27 | 45 | 90 | 135 | 180 | 270 | 🧠 |

Phone main and front cameras are about 22–30 mm equivalent 🧠. That is why a phone photo that is not cropped implies d ≈ 0.3–0.5 m, the most distorting range.

**Table 3 — Single-camera head photogrammetry settings commonly recommended** (community ranges, adult sitter, still photos)

| Parameter | Recommended range | Badge |
|---|---|---|
| Photos | 40–150 (often 3 rings × 15–36 stations) | 🧠 |
| Angular step | 10–20° per station | 🧠 |
| Overlap between neighbours | 60–80% | 🧠 |
| Shutter | ≥1/125 s handheld, ≥1/200 s preferred | 🧠 |
| Aperture (full-frame) | f/5.6–f/11 | 🧠 |
| Camera distance | 0.6–1.5 m | 🧠 |
| Total capture time | ≤1–3 min | 🧠 |
| Professional rigs | 24 to more than 150 synchronised cameras | ↔️ |

**Table 4 — Mesh sizes the community meets** (vertices unless stated)

| Mesh | Size | Badge |
|---|---|---|
| ARKit face mesh | 1,220 | 🧠 |
| MediaPipe Face Mesh | 468 / 478 landmarks (verified in `blender/blender-face-addons.md`) | 🧠 |
| FLAME | 5,023 | 🧠 |
| Basel Face Model 2009 | 53,490 | 🧠 |
| Raw photogrammetry head | 1–10 M triangles before decimation | 🧠 |
| Sculpt-ready base for Multires | 5–20 k quads | 🧠 |

**Table 5 — Tool landscape as discussed** (cost and licence are time-sensitive and unverified)

| Tool | Input | Cost/licence (verify) | Community verdict | Badge |
|---|---|---|---|---|
| KeenTools FaceBuilder (Blender) | 1+ photos, pins | paid subscription, trial | best quick base; sculpt after | 🧠 |
| Reallusion Headshot (CC4) | 1 photo or mesh | paid | fast rigged head, likeness middling | 🧠 |
| Daz Face Transfer | 1 frontal photo | free base | "plastic", Daz-only | 🧠 |
| FaceGen Modeller | 1–3 photos | paid | dated, generic | 🧠 |
| MetaHuman (Mesh/footage to MetaHuman) | scan or depth video | free with Unreal; use outside Unreal changed 2025 (UE 5.6; other tools incl. Blender allowed, but Blender export is clunky) [2][3] | best rig, needs a clean neutral scan | ✅ |
| RealityCapture/RealityScan | photos | free under about US$1 M revenue (2024 change) | top quality, CUDA | 🧠 |
| Agisoft Metashape | photos | Standard/Pro perpetual licences | robust, runs on Mac | 🧠 |
| Meshroom / COLMAP | photos | open source (MPL-2.0 / BSD) | free, slower, CUDA for dense | 🧠 |
| 3DF Zephyr Free | photos | free, capped at 50 photos | fine for small sets | 🧠 |
| Hunyuan3D 2.x | 1+ images | open weights, licence excludes EU/UK/South Korea | best open generator, no likeness | ↔️ |
| TRELLIS / TripoSR | 1 image | MIT | blockout only | 🧠 |
| Meshy / Tripo / Rodin | 1+ images | freemium credits | blockout, retopology needed | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Capture for the solver.** Views: frontal, 3/4 left and right (yaw ±35–45°), both profiles, one slightly below and one slightly above (pitch ±20°). Camera 1.5–2.5 m away at 85–135 mm equivalent or the phone's optical 2–3× lens, cropping later; avoid digital zoom (loses detail, EXIF focal may be inconsistent). Sitter neutral, lips lightly closed, eyes open on a fixed target, hair back, no glasses. Even, diffuse light. Keep originals with EXIF.
2. **Photogrammetry is a separate pass** of rings (Table 3); the sitter breathes out and holds still for each ring.
3. **Quarantine bad inputs:** beauty-filtered images, screenshots and social re-uploads; mirrored front-camera shots (check a hair parting or mole); other years; smiles (keep for expression checks only).
4. **Never trace selfies in orthographic views.** Solve a perspective camera per photo and use it as a Blender camera with the photo as background (`blender/reference-camera-setup.md`).
5. **Sculpt order:** skull mass and back of head → brow ridge and eye depth → nose projection and alar width → mouth width and lip volume → jaw angle, chin, ear placement. Depth errors show only in 3/4 and profile cameras, so cycle every solved camera after each pass.
6. **Likeness QA:** mirror the viewport, view at thumbnail size, overlay the render through each solved camera at 50% opacity or Difference, and check one held-out photo.
7. **Scan cleanup.** Decimate a copy, wrap your base mesh onto it (Shrinkwrap, target-normal projection, plus Multires reshape) or use an external wrap tool. Rebuild eyes as spheres with a cornea bulge and hair as cards or curves.
8. **What goes wrong**

| Symptom | Likely cause | Fix |
|---|---|---|
| Nose too big, face too narrow | selfie perspective traced as orthographic | solve the focal length; add a distant photo |
| Right in front view, wrong in 3/4 | depth comes from the prior | add profiles; sculpt depth |
| Asymmetry on the wrong side | mirrored selfie | flip and re-solve |
| Doubled lips or eyes in the scan | sitter moved | shorter session; mask; re-shoot |
| "Cousin, not the person" | averaging prior; symmetry | turn off symmetry; exaggerate distinctive features slightly |
| Waxy texture, shadows baked in | directional light | flat light; de-light |

## Algorithmic implications

- **Sanitise inputs.** Parse EXIF `FocalLengthIn35mmFilm`, `FocalLength`, `Make/Model`, `LensModel`, `DateTimeOriginal`, `Orientation`. Flag missing EXIF, cropped aspect ratios and front-camera lenses; warn when photo dates span more than 18 months.
- **Mirror test.** Solve each photo and its horizontal flip; if the flip lowers the multi-view residual by more than 20%, mark it mirrored, and ask the user only when unclear.
- **Focal prior** (log-normal on f₃₅): EXIF present σ_log 0.05 (digital zoom, crop); phone without EXIF μ = 26 mm, σ_log 0.25; unknown camera μ = 50 mm, σ_log 0.6. With a single view, fix focal at the prior mean; free it only when views span ≥60° of yaw.
- **Distance sanity check.** Z ≈ f_px · 63 mm / IPD_px (adult interpupillary distance about 63 ± 3.5 mm 🧠). If Z < 0.8 m, warn "strong perspective: focal must be right", but keep the photo; it is informative.
- **Landmark noise σ** in units of interocular distance:

| Landmark type | σ (× IOD) |
|---|---|
| Automatic internal points | 0.02–0.03 |
| Automatic jaw and cheek contour, sliding along the silhouette normal only | 0.05–0.08 |
| Ears (disable when \|yaw\| < 30°) | 0.06–0.10 |
| User-moved pins | 0.01, treated as near-hard |

  Use a Huber loss with δ = 2σ in `levenberg_marquardt`. Down-weight a view whose RMS is above 3σ.
- **Hair and beard masks.** Exclude silhouette and contour points that fall inside segmented hair or beard regions. Rebuild the hairline and jaw under a beard from the skull and shape prior.
- **Separate identity from expression.** Use one identity vector and a per-view expression vector with prior N(0, 1) in model units. Views tagged neutral have expression fixed at 0.
- **Symmetry prior, not a constraint.** Use σ ≈ 1–2 mm per mirrored landmark pair, consistent with the 0.6–4.6 mm left-right differences in `anatomy/facial-asymmetry.md`. Let multi-view evidence override it.
- **Coverage-driven mode.** If max |yaw| < 20°, label depth "prior-driven" and ask for a profile. Write a per-vertex confidence attribute (triangulation spread from `triangulate_points`, prior dominance) to the Blender mesh for use as a sculpt mask.
- **AI-generated meshes are weak priors only:** align with `umeyama`, add a low-weight shape term (σ ≈ 3–5 mm), never use as landmark ground truth.
- **Built-in QA:** held-out-view reprojection error in pixels; overlay and Difference renders through `to_blender_camera`; one-click flip and thumbnail views; optional identity-embedding cosine as a secondary score (`reconstruction/identity-embeddings.md`).

## Disagreements, myths & open questions

- ↔️ **AI generators and likeness.** "AI is good enough now" against "AI cannot do likeness." Users agree it is fine for blockout. Whether recent models (2025–26) keep identity from several photos is unsettled and changes fast.
- ↔️ **Swivel chair or orbiting camera** for single-camera scans of people (Key facts).
- ↔️ **Symmetry.** Some sculptors say a likeness lives in its asymmetries. Others say proportions matter far more, and that sculpting asymmetry early adds error.
- **Myth: "telephoto flattens faces."** Distance sets perspective. A long lens only lets you stand far enough away 🧠
- **Myth: "iPhone LiDAR scans faces."** It is too coarse; TrueDepth or photos do better 🧠
- **Myth: "more photos are always better."** Blurred, mismatched or expressive photos hurt the solve; prune them 🧠
- **Myth: "a splat or NeRF is a sculptable model."** It is not a clean surface 🧠
- **Myth: "eyes are 90% of the likeness."** Human face-recognition research points to eyes and brows plus overall configuration (Sinha et al., 2006), not the eyes alone 🧠
- **Open questions:** Has anyone measured the likeness (mm error or recognition rate) of FaceBuilder, Headshot or AI generators against ground-truth scans? What fraction of threads involve one photo versus controlled multi-view sets? What are current prices and licences? (Process note: domain-filtered search on reddit.com returned HTTP 400 earlier, so verify with unfiltered queries containing "reddit" plus the subreddit name.)

## Sources

1. Rutgers news, selfies and nasal distortion: https://www.rutgers.edu/news/selfies-drive-self-image-and-may-lead-many-seek-plastic-surgery
2. CG Channel, MetaHumans in Unity/Godot (June 2025): https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/
3. Creative Bloq, MetaHuman outside Unreal: https://www.creativebloq.com/3d/metahuman-just-broke-free-from-unreal-engine-5-why-everyone-can-now-create-lifelike-characters

**Further reading (by name, not yet linked)**
- Ward, Ward, Fried, Paskhover, "Nasal distortion in short-distance photographs: the selfie effect", JAMA Facial Plastic Surgery, 2018
- Fried, Shechtman, Goldman, Finkelstein, "Perspective-aware manipulation of portrait photos", SIGGRAPH 2016
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*, 2nd ed., 2004
- Schönberger & Frahm, "Structure-from-Motion Revisited" (COLMAP), CVPR 2016
- Egger et al., "3D Morphable Face Models — Past, Present and Future", ACM TOG 2020
- Li et al., FLAME, "Learning a model of facial shape and expression from 4D scans", SIGGRAPH Asia 2017
- Paysan et al., Basel Face Model, 2009
- Sanyal et al., RingNet / NoW benchmark, CVPR 2019
- Zielonka, Bolkart, Thies, MICA, "Towards Metrical Reconstruction of Human Faces", ECCV 2022
- Kerbl et al., "3D Gaussian Splatting for Real-Time Radiance Field Rendering", SIGGRAPH 2023
- Sinha et al., "Face recognition by humans: nineteen results all computer vision researchers should know about", Proc. IEEE 2006
- Farkas, *Anthropometry of the Head and Face*, 1994
- Dodgson, "Variation and extrema of human interpupillary distance", Proc. SPIE, 2004
- Faraut, *Portrait Sculpting: Anatomy & Expressions in Clay*

## Verification log (2026-11-20)

- Adult IPD about 63 mm, SD about 3.5 mm: unconfirmed. Secondary sources cite Dodgson (2004) mean near 63 mm (63.36 mm cited), but no SD found and no result tied to a specific page. 🧠 kept.
- Ward et al. 2018 30% at 12 in vs 5 ft: corrected/confirmed (nasal base about 30%, tip about 7%). https://www.rutgers.edu/news/selfies-drive-self-image-and-may-lead-many-seek-plastic-surgery
- Nose-to-tragion depth 10-12 cm (Farkas): unconfirmed; no values found. 🧠 kept.
- MetaHuman usable outside Unreal incl. Blender, UE 5.6 era (2025): confirmed (Blender export unofficial/clunky). https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/ ; https://www.creativebloq.com/3d/metahuman-just-broke-free-from-unreal-engine-5-why-everyone-can-now-create-lifelike-characters
