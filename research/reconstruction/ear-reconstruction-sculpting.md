# Reconstructing and sculpting the ear from photos

> Generic photo-to-3D tools get the ear wrong more than any other part. Face 3DMMs carry coarse, averaged ears, face landmarkers stop at the tragus, recognition crops leave the ear out, and hair hides it. The route that works is to fit each ear as its own part, hinged on the otobasion line and anchored at tragion in a Frankfort-horizontal (FH) frame, with its own tilt, protrusion and twist. Fit it to profile, near-profile, rear-oblique and back photos taken with the hair clipped away and a raking light, then sculpt the folds by hand. As far as recalled, the ear-specific landmark sets and statistical models (iBUG 55-point, York Ear Model, UHM) are research-only, so a permissive tool needs CC0/MIT geometry plus its own ear modes. With no harvest or draft, every claim is expert knowledge or a pointer to a sibling library note.
>
> Evidence status: 0 ✅ / 0 📄 / 61 🧠 / 29 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Detectors, landmarks, datasets**
- **Coarse ear points are free.** COCO body keypoints and MediaPipe Pose (Apache-2.0) both include `left_ear`/`right_ear`. That is enough to crop the ear and sanity-check yaw, but not to fit shape. 🧠
- **Face landmarkers stop short of the ear.** dlib-68's jaw ends near the ear root and MediaPipe Face Mesh stops in front of the tragus. Sapiens' 308 points reportedly include ears, under a licence believed non-commercial (lib: `reconstruction/landmark-detection.md`). ↔️
- **iBUG in-the-wild ears** (Zhou & Zafeiriou, IEEE FG 2017) define a 55-point scheme on the helix, antihelix and crura, concha rim, tragus, antitragus and lobule. The set is recalled as ≈600 landmarked images plus a ≈2k-image identity collection, for research use only ↔️. Its scheme is the de facto dense ear convention 🧠.
- **Other 2D ear sets** (identity labels, mostly no landmarks): AWE/AWEx and UERC (Ljubljana, on request), USTB I–IV, IIT Delhi, AMI (≈700 images, 100 subjects), UBEAR (masks) and EarVN1.0 (≈28k images, 164 subjects). All are research or non-commercial 🧠, except perhaps EarVN1.0 (possibly CC BY) ↔️.
- **3D ear data.** Notre Dame UND (J2: ≈400 subjects, range + colour; licence agreement) 🧠. HRTF corpora with head-and-ear meshes: SYMARE, HUTUBS (≈96 subjects, recalled CC BY 4.0), SONICOM, synthetic CHEDAR (≈1,250 heads) ↔️. Spatial audio now drives consumer ear capture (Apple's TrueDepth ear scan, Sony's ear-photo app) 🧠.
- **Segmentation.** CelebAMask-HQ parsing has left-ear, right-ear and earring classes but is non-commercial. Hair and accessory masks are the key occlusion input. 🧠

**3D models and licences**
- **York Ear Model (YEM)** (Dai, Pears & Smith, FG 2018) is the main ear-only 3DMM. It was seeded from a few SYMARE scans and augmented by fitting landmarked 2D ears (recalled ≈500 training ears). Research release on request. ↔️
- **UHM** (Ploumpis et al., CVPR 2019; TPAMI 2021) fuses LSFM face statistics with LYHM cranium statistics. The TPAMI version adds a YEM ear, eyes and the mouth interior. Academic, non-commercial (lib: `reconstruction/3dmm-overview.md`). 🧠
- **FLAME ears are coarse.** Its edges are 3–6 mm long against folds 1–3 mm wide, so helix roll and crura cannot be represented. `FLAME_masks.pkl` has per-ear masks. FLAME 2023 Open is CC BY 4.0; earlier versions are non-commercial (lib: `reconstruction/flame-model.md`, confirmed there). 🧠 BFM ears are generic, and NPHM-style neural heads are non-commercial 🧠.
- **Permissive geometry, but no ear statistics.**
  - ICT-FaceKit (MIT): scan-derived ears in its head identity model 🧠.
  - MPFB2/MakeHuman: GPL code with CC0 base mesh and targets (lib: `blender/blender-face-addons.md`, sourced there). Its ear targets cover size, position, rotation, protrusion ("wing"), lobe and shape, with names that vary by version ↔️.
  - Blender Human Base Meshes (2023): CC0, sculpt-ready heads with ears 🧠.
- **Verdict.** No permissively licensed ear 3DMM is known to this author ↔️. Ship hand-authored shape keys on a CC0 ear, or let users train an ear PCA locally on CC-BY scans after checking licence and consent scope 🧠.
- **Ear-specific reconstruction papers are few.** They are YEM fitting from 2D landmarks and AudioEar (Huang et al., AAAI 2023), which does single-view ear reconstruction with a 2D landmark set and a small 3D set ↔️. The state of the art in 2025–2026 was not recalled 🧠.

**Geometry that drives the fit** (anatomy: `anatomy/ear.md`)
- **Tragion sits at about orbitale height in FH**, just behind the mandibular condyle (lib: `anatomy/ear.md`) 🧠. The helix and lobule are rigid relative to the cranium; tragion moves about 1–2 mm when the jaw opens 🧠.
- **Protrusion has two causes**: concha set-back (the conchomastoid angle) and antihelix under-folding (the conchoscaphal angle). One hinge angle cannot separate them, so the model needs a hinge rotation plus shape modes. 🧠
- **Ear-plane yaw is roughly the auriculocephalic angle minus the backward tilt of the mastoid skin.** So the plane usually lies within about ±20° of sagittal and faces forward when the ear protrudes. A true profile is close to the ear-normal view. ↔️
- **Pitch error becomes tilt error one-to-one.** A 10° pitch error also moves the ear about 17–19 mm against the brow (lib: `reconstruction/camera-pose-solving.md`). 🧠
- **Ear relief is 25–35 mm deep**: about 6% near-to-far magnification at 0.5 m, 2% at 1.5 m (pinhole arithmetic). 🧠

**Recognition and likeness**
- **Machine ear recognition** uses whole-ear shape: the helix and antihelix contours, concha, intertragal notch and lobule. It degrades steeply with viewing angle (lib: `anatomy/ear.md`, sourced there). 🧠
- **Face embeddings** use tight 5-point crops, so they cannot validate ears (lib: `reconstruction/identity-embeddings.md`). 🧠
- **Perceived-likeness priority** (author synthesis) ↔️:
  1. position (tragion height and set-back, tilt);
  2. protrusion silhouette, front and back;
  3. length and width;
  4. helix outline in profile (top shape, Darwin's tubercle, rim-roll width);
  5. lobule size and attachment;
  6. concha size and depth, and whether the antihelix shows outside the helix from the front;
  7. tragus shape.

  Acquired marks (cauliflower ear, stretched piercings, keloids) override all of these 🧠.

## Numbers & reference tables

**Table 1 — Ear landmark and segmentation resources** (sizes and licences recalled)

| Resource | Content | Size | Licence | Commercial | Status |
|---|---|---|---|---|---|
| iBUG in-the-wild ears (FG 2017) | 55 2D landmarks | ≈600 + ≈2k ID images | research | no | ↔️ |
| AWE / AWEx / UERC | in-the-wild IDs | AWE 1,000 / 100 subjects | on request | no | 🧠 |
| EarVN1.0 | in-the-wild IDs | ≈28k / 164 | possibly CC BY | check | ↔️ |
| UND J2 | 2D + 3D range | ≈400 subjects | agreement | no | 🧠 |
| CelebAMask-HQ | ear, earring masks | 30k faces | non-commercial | no | 🧠 |
| COCO / MediaPipe Pose | 1 point per ear | — | CC BY annotations / Apache-2.0 | yes (check weights) | 🧠 |

**Table 2 — 3D ear geometry sources**

| Model | Ear content | Licence | Ship in add-on? | Status |
|---|---|---|---|---|
| York Ear Model | ear-only 3DMM, ≈500 training ears | research, on request | no | ↔️ |
| UHM (TPAMI) | head 3DMM + YEM ear | academic NC | no | 🧠 |
| FLAME / FLAME 2023 Open | coarse ear, 3–6 mm edges | NC / CC BY 4.0 | 2023 Open only, attributed | 🧠 |
| ICT-FaceKit | scan-derived head + ears | MIT | yes (verify) | 🧠 |
| MPFB2 / MakeHuman | ear morph targets | CC0 assets, GPL code | yes | 🧠 |
| Blender Human Base Meshes | generic sculpt-ready ears | CC0 | yes | 🧠 |
| HUTUBS / SYMARE / SONICOM / CHEDAR | acoustic head-and-ear scans | HUTUBS CC BY 4.0?; others unknown | train locally | ↔️ |

**Table 3 — Sub-feature dimensions** (adult; mm unless stated)

| Feature | Value | Population | Status |
|---|---|---|---|
| Length sa–sba | means 57–63; M > F | several (lib: `anatomy/ear.md`) | 🧠 |
| Width / length | 0.47–0.54 | same | 🧠 |
| Pinna height / width (CIPIC, recalled) | ≈64 / ≈29 | 45 subjects, HRTF set | ↔️ |
| Cavum concha height / width / depth (CIPIC) | ≈19 / ≈16 / ≈10 | same | ↔️ |
| Cymba height; fossa height (CIPIC) | ≈7; ≈15 | same | ↔️ |
| Intertragal incisure width (CIPIC) | ≈5 | same | ↔️ |
| Pinna rotation / flare (CIPIC) | ≈24° / ≈28° | same | ↔️ |
| Long-axis tilt from vertical, FH | 10–30°, typical ≈20° | mixed (lib) | ↔️ |
| Auriculocephalic angle | 20–30° vs <25° | clinical (lib) | ↔️ |
| Helix–mastoid, upper / mid / lower third | ≈10–12 / 16–18 / 20–22 | surgical goals | 🧠 |
| Lobule height | 15–22 | rough | 🧠 |
| Rim thickness | 3–6 | rough | 🧠 |
| Attachment length obs–obi ÷ length | ≈0.6–0.8 | low confidence | 🧠 |

**Table 4 — Ear photo protocol** (yaw 0° = front; head views from at least 1.5 m)

| Shot | Yaw | Purpose | Status |
|---|---|---|---|
| Front | 0° | protrusion silhouette, left/right height | 🧠 |
| Profile L/R | ±90° | helix outline, tilt, length, tragion vs orbitale | 🧠 |
| Bracket L/R | ±75°, ±105° | ear-normal view (concha widest) | 🧠 |
| Rear-oblique L/R | ±135° | helix–mastoid gap, ear back, sulcus | 🧠 |
| Back (and optional top) | 180° | both protrusions | 🧠 |
| Raking-light close-up | ≈90°, pitch 0 to +15° | concha depth, crura; tele at 0.8–1 m or more, lateral canthus in frame | 🧠 |
| Caliper or ruler sa–sba | — | metric scale, ±1 mm | 🧠 |

At 1.5 m, an 85 mm lens on 24 MP gives ≈9 px/mm, so the ear is ≈560 px long. A 3× phone tele on 12 MP gives ≈340 px. Aim for at least 300 px. 🧠

**Table 5 — Expected accuracy** (author estimates)

| Quantity | Condition | Error | Status |
|---|---|---|---|
| Length | multi-view + caliper scale | ±1–2 mm | ↔️ |
| Length | multi-view, scale from an IPD prior | ±3–4 mm | ↔️ |
| Tilt | pitch solved from 2 or more views | ±3–5° | ↔️ |
| Tilt | single profile | ± pitch error (5–10°) | 🧠 |
| Tragion height vs orbitale | multi-view | ±2–4 mm | ↔️ |
| Protrusion | front + back or rear-oblique | ±2–3 mm | ↔️ |
| Protrusion | profile only | unobserved; prior ±5–8 mm | 🧠 |
| Concha depth | raking-light oblique + sculpt | ±2–3 mm | ↔️ |
| AI image-to-3D ears | generic generators | 5–15 mm (lib: `reconstruction/generative-3d-heads.md`) | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Shoot for the ears (Table 4).** 🧠
   - Clip the hair up. Do not tuck it behind the ear, which wedges the ear outward.
   - Remove earrings, glasses, headphones and behind-the-ear hearing aids, and use no pressing caps.
   - Take two lighting passes: diffuse or cross-polarised for contours and texture, then raking, with the key 30–45° above and slightly in front of the ear so the antihelix and tragus shadow into the concha.
   - No backlight: the translucent ear glows red and its edges smear. Shoot at f/8.
2. **Solve the head first.** Solve all cameras and level the head to FH, then read ear height, tilt and length. Tragion and subaurale can join the rigid pose anchors. 🧠
3. **Block the ear as its own object.** 🧠
   - Parent it to an Empty at tragion, oriented with X along the hinge (otobasion superius to inferius) and Z along the long axis. Rotating the Empty then sets tilt, protrusion and twist, and scaling it sets size.
   - Match the outline in the profile camera, protrusion in the back and front cameras, and the concha in the bracket view.
   - Use a Lattice before any detail.
4. **Sculpt in this order.** 🧠
   1. Block the C of the helix, the Y of the antihelix, the concha bowl, the tragus and the lobule.
   2. Carve the concha deep: the cavum toward the canal behind the tragus, the cymba above the helical crus.
   3. Roll the helix rim forward over the scapha, widest at the top-back and fading into the lobule.
   4. Make the superior crus soft and the inferior crus sharper.
   5. Keep the lobule soft, with no cartilage edges.
   6. Do the back of the ear last: the conchal eminence and the auriculocephalic sulcus.

   Brushes: Clay Strips and Draw to block; Draw Sharp, Crease and Pinch for cartilage edges; Inflate and Blob for the rim and lobule; Snake Hook or Pose to pull and angle. Brush names changed with brush assets in 4.3 (lib: `blender/blender-sculpt-features-5x.md`).
5. **Resolution.** 🧠
   - A 0.2–0.4 mm voxel holds a helix rim. On a whole head that is about 1–3 M faces, so artists explore on a separate ear object (Dyntopo or voxel remesh) and project back.
   - For the final mesh, use Multires on a quad ear of 300–1,000 base quads, ≈500 by default (lib: `blender/face-retopology.md`).
6. **Topology.** Two or three helix-rim loops, a loop around the antihelix Y, concha rings into the canal, tragus loops, and helix loops closing through the lobule. Join with a root ring of about 16–24 edges (Bridge Edge Loops). Put poles behind the ear, at the crura ends and at the helical crus. The ear needs several times the cheek's L0 edge density. 🧠
7. **Keep the sides separate.** Mirror only the blockout. Fit size, height, tilt and protrusion per side. 🧠
8. **Validate in every solved camera.** Check the profile helix contour, the front and back silhouettes, and the concha shadows under a matched raking light. 🧠
9. **Common failures** (lib: `community/likeness-mistakes.md`) 🧠:
   - ears flat to the head, too high (from unsolved pitch), too far forward or too upright;
   - a shallow concha, a rim of uniform thickness, or a sharp crease at the root;
   - an unsculpted back, or a mirrored copy;
   - the hair silhouette read as the helix.

## Algorithmic implications

- **Part model.** E(θ, s, α) = R(θ)·s·(ē + Uα) + t, in an ear frame. 🧠
  - Frame: origin at tragion, hinge axis obs→obi, long axis sba→sa, and the lateral normal as their cross product.
  - θ = (tilt, protrusion about the hinge, twist about the long axis).
  - U holds 5–15 PCA modes or hand-authored keys: helix roll, concha depth, antihelix fold, lobule length and attachment, top shape, Darwin's tubercle.
  - Last, per-vertex offsets, Laplacian-smoothed and at most 1.5–2 mm.
- **Priors** (adult, provisional) 🧠:

| Parameter | Prior | Bounds | Basis |
|---|---|---|---|
| log s (length ≈ 61 mm) | N(0, 0.075); +2 mm if male; +0.2 mm/yr over age 25 | 45–85 mm | lib `anatomy/ear.md` |
| width/length | N(0.50, 0.05) | 0.38–0.65 | lib |
| tilt | N(20°, 7°) | −5 to 45° | lib ↔️ |
| protrusion | N(25°, 8°); warn above 35° | 5–70° | lib ↔️ |
| helix–mastoid, mid-third | N(17, 4) mm | 5–35 | lib |
| twist | N(0°, 6°) | ±20° | 🧠 |
| tragion vertical vs orbitale | N(0, 4.5) mm | ±20 | lib |
| tragion behind exocanthion (FH) | N(65, 8) mm | 40–95 | derived from lib depths |
| α | N(0, I); flag ‖α‖² > χ²_K at 99.9% | — | lib `3dmm-overview.md` |
| left–right coupling | Δlength 2 mm, Δtilt 4°, Δtragion 3 mm, Δprotrusion 3 mm, Δα 0.5 | — | lib |

- **Observation σ, in mm on the ear.** At 5–10 px/mm, landmark-definition ambiguity outweighs pixel noise. 🧠
  - Pinned fixed points (t, intertragal notch, sba, sa, antitragus tip): 1–1.5 mm.
  - Detector points: 2–3 mm.
  - Helix and concha contour semi-landmarks: 1.5–2.5 mm, point-to-curve, re-associated each iteration.
  - Front and back helix silhouettes go through `fit_silhouettes`.
  - Huber loss at 1.5σ, with σ ×2–3 next to hair.
- **View weights.** Weight in-plane terms by max(0, n_ear·v)²; silhouettes get full weight. Give ears zero weight until at least 2 views constrain pitch (lib: `community/likeness-mistakes.md`). 🧠
- **Hair.** 🧠
  - Drop landmarks more than 50% covered by the hair or accessory mask.
  - Add a one-sided carving term: projected ear pixels must lie inside the union of the ear, hair and accessory masks.
  - Let the prior fill the hidden parts, and write a per-vertex observed/prior confidence attribute.
- **Seam.** Fix the head's root ring, solve the part, then blend a 5–10 mm band with `laplacian_deform`. Never warp the ear with a head-wide RBF, which drags scalp into the helix (lib: `reconstruction/deformation-fitting-math.md`). 🧠
- **Landmark scheme.** Farkas points (sa, sba, pra, pa, obs, obi, t), intertragal notch, antitragus tip and helical crus, plus about 40 of our own contour semi-landmarks, so nothing derives from the research-licensed 55-point set. 🧠
- **Provenance.** Store the licence, the measurement definition and `commercial_ok` with every ear basis. Map research bases onto the template only locally, from files the user supplies. 🧠

## Disagreements, myths & open questions

- **Ear-normal camera.** `anatomy/ear.md` says to shoot 20–35° *behind* profile and gives a 20–35° flare from sagittal. The geometry above puts the ear plane near sagittal, facing forward when prominent. Shoot the ±15° bracket until this is measured. ↔️
- **Permissive ear statistics.** The licences of YEM, UHM, AudioEar and the HRTF corpora are unconfirmed and time-sensitive. ↔️
- **Myth: ears are unique like fingerprints.** They are discriminative; uniqueness is unproven. 🧠
- **Myth: ears never change.** The lobule lengthens with age (lib: `anatomy/ear.md`). 🧠
- **Do parametric ears help likeness?** They fix position, size and protrusion. Artists still hand-sculpt the folds. ↔️
- **Open:**
  - single-view ear benchmark errors;
  - ear-detector accuracy under hair;
  - whether CIPIC measures flare against the head or the sagittal plane;
  - the accuracy of consumer TrueDepth ear scans.

## Sources

No harvest or earlier draft existed, so no URLs are cited. Sourced versions of related claims sit in the library notes named inline, mainly `anatomy/ear.md`, `reconstruction/flame-model.md` and `blender/blender-face-addons.md`.

**Further reading (by name, not yet linked)**
- Zhou & Zafeiriou, "Deformable Models of Ears in-the-Wild for Alignment and Recognition", IEEE FG 2017
- Emeršič, Štruc & Peer, "Ear recognition: More than a survey", Neurocomputing 2017; UERC papers (2017, 2019)
- Dai, Pears & Smith, York Ear Model, IEEE FG 2018
- Ploumpis et al., "Combining 3D Morphable Models: A Large Scale Face-and-Head Model", CVPR 2019; TPAMI 2021 follow-up
- Algazi, Duda, Thompson & Avendano, "The CIPIC HRTF Database", IEEE WASPAA 2001
- Jin et al., SYMARE, 2014; Brinkmann et al., HUTUBS, 2019; Huang et al., AudioEar, AAAI 2023
- Yan & Bowyer, 3D ear biometrics, IEEE TPAMI 2007; Hoang, EarVN1.0, Data in Brief 2019; Lee et al., CelebAMask-HQ, CVPR 2020
- Iannarelli, *Ear Identification*, 1989; Farkas, *Anthropometry of the Head and Face*, 1994; McDowell, otoplasty goals, 1968
- Blender Studio, Human Base Meshes, 2023; MakeHuman/MPFB2 documentation
