# Engine requirements: community & artist knowledge

For the numpy-only fitting engine and Blender add-on. Compiled 2026-11-20 from the 14 notes in `research/community/`, with verification-log corrections applied. Overview: [README][README].

**Evidence caveat.** The area holds 19 ✅ / 63 📄 / 824 🧠 / 250 ↔️ claims (≈7% sourced). **Unless marked, every number is 🧠 and provisional:** ship it as a configurable default and calibrate with the harness (R8.4) and held-out photos. Pinhole arithmetic is reliable.

Units: engine mm; Blender m (display mm). IOD = interpupillary distance ≈ 63 mm.

## 1. Ingest and photo audit

- **R1.1 EXIF:** parse `FocalLengthIn35mmFilm`, `FocalLength`, `Make`, `Model`, `LensModel`, `DateTimeOriginal` and `Orientation`. Bake orientation into working copies; record every crop and resize. [RD][RPP]
- **R1.2 Manifest** (JSON per session): per photo view tag, nominal yaw/elevation, lens id, tape distance, expression, hair, glasses, lighting, source type, mirrored, anamorphic, retouch risk, date; per session calipers with σ, scale objects, consent record. [RPP][AS]
- **R1.3 Focal groups:** key on (Make, Model, LensModel, FocalLength, W, H, still/video). Share log f within a group (tie σ 0.02); video always gets its own group. [RPP][BA]
- **R1.4 Gates:** eye aspect ratio < 0.2 reject; bottom 20% Laplacian variance down-weight; face < 250 px warn, < 120 px reject; > 2% clipped skin, no photometric terms; mouth > 3% IOD or smile, no identity use; hair over ears, drop ear and temple landmarks. [RPP]
- **R1.5 Distance estimate:** d = f_px·63 mm/IPD_px. Apply the tiers in §9. [IG][YT][RD][BA]
- **R1.6 Mirror test:** mirrored if the flipped image lowers the multi-view residual by > 20%; ask when `LensModel` names a front camera. [RD][BA]
- **R1.7 Phone lens correction:** f₃₅ ≤ 16 mm or face beyond 60% of the half-diagonal → σ ×2 or exclude (effect ✅, thresholds 🧠). [AS]
- **R1.8 View weights:** 1/(views in its 15° bin); cap any view at 40% of the total. [RPP][AS]
- **R1.9 Video:** ≤ 3 frames per bin; drop frames turning > 10–15°/s ↔️. [RPP]

## 2. Camera solve

- **R2.1 Joint solve:** pose per view, focal per group, shape and scale global; inverse depth, weak-perspective initialisation, full-perspective refinement. [ZB]
- **R2.2 Focal priors:** log-normal on f₃₅.

| Situation | Median | σ_log | Cite |
|---|---|---|---|
| EXIF, uncropped | EXIF | 0.03 | [ZB][YT] |
| EXIF, possible crop or digital zoom | EXIF | 0.05–0.10 | [RD][BA] |
| Physical focal length, guessed sensor | computed | 0.10 | [ZB] |
| Phone, no EXIF | 26 mm | 0.25 | [RD] |
| Press / studio / film or video / phone rear / selfie | 135 / 100 / 50 / 26 / 26 mm | 0.5 / 0.4 / 0.7 / 0.6 / 0.1 | [AS] |
| Unknown | 50 mm | 0.6 | [RD][ZB] |

  The engine default 0.35 puts a 26 mm phone lens ≈1.9σ from 50 mm; use 0.6 when nothing is known.
- **R2.3 Free focal** only if views span ≥ 60° of yaw or include a profile; otherwise fix it or tie it to distance via the IPD prior. [RD][IG][YT]
- **R2.4 Distance:** tape z σ 5 cm; else median 1.0 m, σ_log 0.7. [RPP][ZB]
- **R2.5 Nuisances:** principal point σ 1% of max(W, H) (10% if cropped); k1 = 0 ± 0.02, reject ultra-wide; pixel aspect 1.0 ± 0.01 unless anamorphic. [ZB][AS]
- **R2.6 35 mm conversion** on the diagonal (43.27 mm), as in `focal_px_from_35mm`; width-based is ≈4% short on 4:3 ↔️. [BA]
- **R2.7 Pose priors:** yaw σ 10° freehand (5° with floor marks); pitch σ 5° main ring, 8–10° high/low; roll σ 3°; > 3σ from nominal means mislabelled or mirrored. [RPP]
- **R2.8 Perspective signature:** regress `per_view_residuals` on ρ_i·δ_i; > 5% implied magnification error → free focal or request a distant photo. [LM]
- **R2.9 Blender export:** one convention. `to_blender_camera` uses HORIZONTAL fit with lens and both shifts over width; AUTO with max(W, H) works only if used throughout. Unit-test by reprojecting a landmark (unverified). [BA][YT][ZB]

## 3. Landmarks and formats

- **R3.1 Schemes:** iBUG 68, WFLW 98, MediaPipe 478, ARKit 1,220 and FLAME 51+17 as barycentric embeddings on the template; ship a 68↔478 map and a versioned landmark→vertex table per base mesh. [AWL][BA]
- **R3.2 Pins:** `Pin{view, xy_px, surface(tri, bary), sigma, source}`; re-solve after each edit; ≤ 12 auto-suggested per view. [YT][BA]
- **R3.3 Noise σ** (× IOD unless stated):

  | Landmark kind | σ |
  |---|---|
  | Detector interior | 0.02–0.03 |
  | Contour (along the normal only) | 0.05–0.08 |
  | Brows | 0.04–0.06 |
  | Ears (weight 0 if \|yaw\| < 30° or pitch is unconstrained) | 0.06–0.10 |
  | Reviewed pins: corners / lid and lip / oval | 1.5 / 2.5 / 4% |
  | User pins | 1–2 screen px |

  Hairline (3–5 mm) and brows (≈2 mm) never drive camera solving. Huber δ = 2σ; down-weight views with RMS > 3σ or > 2× median. [RD][BA][YT][ZB][PC][LM]
- **R3.4 Tiers:** A bony (n, t, ex, en, prn, sn, pg, gn, zy, go) σ 1–2 mm, Procrustes anchors; B soft (ch, sto, ls, li, al) σ 2–4 mm; C hair-dependent (v, eu, op, tr) one-sided bounds only, never scale. [TR]
- **R3.5 Sliding contours:** re-associate jaw, cheek and ear outlines with the occluding contour every iteration. [YT][ZB][TR]
- **R3.6 Brows and hairline** (≥ 5 points per brow) are fitted and exported as curves, outside the skin loss; moles seen in ≥ 2 views become tie points. [AS]
- **R3.7 Identity vs expression:** one identity vector; per-view expression with prior N(0, 1), fixed at 0 for neutral views; drop lips in open-mouth views and lids in squints. [RD][BA][ZB]

## 4. Priors

| Prior | Value | Badge | Cite |
|---|---|---|---|
| IPD | 63 ± 3.5 mm (3.7 or 4 elsewhere); a measured PD or caliper overrides at ±1 mm | 🧠 ↔️ (SD unconfirmed) | [BA][ZB][IG] |
| ID-1 card | 85.60 ± 0.5 mm | 🧠 | [RPP] |
| Iris (HVID) | 11.7 ± 0.5 mm, only if the iris is ≥ 20 px; device means 11.77–12.40 mm | ↔️ | [IG] |
| Eyeball radius | 12 ± 0.5 mm | 🧠 | [LM][AI] |
| Cornea ahead of lateral orbital rim | 16 ± 2.5 mm; populations span 8–23 mm | ↔️ | [LM][PC] |
| MRD1 | 4.5 ± 1 mm; sources say 3.5–4.5, so consider 4.0 | ↔️ | [LM][PC] |
| Sclera above iris | hinge penalty unless ≥ 2 views show it | 🧠 | [LM] |
| Lid margin on globe | +0–0.5 mm, σ 0.3 | 🧠 | [SCW] |
| Ear | length 60 ± 4 mm; axis 20 ± 7°; protrusion 17 ± 4 mm; tragion vs orbitale 0 ± 4 mm once pitch is solved | 🧠 ↔️ | [LM][PC] |
| Cranium | g–op 175–205 mm, σ ≈ 7 mm; scalp 4–8 mm | ↔️ | [PC] |
| Tragion depths | σ 6–8 mm; 1.5–2 mm if measured; values reconstructed, not from a source | ↔️ | [TR] |
| Pressed caliper offset | +2 to +5 mm | ↔️ | [TR] |
| Symmetry / midline | `sigma_sym` 2.0 mm, `sigma_mid` 1.5 mm; schedule in R5.3 | 🧠 | [LM][PC] |
| Landmark prior | 8 mm in stage B, 3–4 mm in stage C; uncalibrated | 🧠 | [IG][LM] |
| Canon ratios (weak) | en–en/en–ex 1.08 ± 0.10; al–al/en–en 1.05 ± 0.12; ch–ch/en–en 1.55 ± 0.12 (📄); ch–ch/IPD 0.83 ± 0.07; (g–sn)/(sn–me) 0.90 ± 0.08; (sn–sto)/(sn–me) 0.32 ± 0.03; ear/nose 1.15 ± 0.12; eye line 0.50 ± 0.02 | 🧠 ↔️ | [AAB] |
| External mesh as a prior | photogrammetry 0.5–1 mm; pin fit 1–1.5 mm; another person's scan 3–5 mm; atlas skull 4–6 mm | 🧠 | [YT][AWL] |
| AI mesh (by c = cos(normal, view)) | 3–5 mm (c > 0.7), 6–10 mm (0.3–0.7), ≥15 mm or off; off on hair, eyes, mouth, ears | 🧠 | [AI][RD] |
| Ancestry outside the prior's population | σ ×1.5 | ↔️ | [AWL] |

Canons: E_canon = Σ w_i((r_i − μ_i)/σ_i)², w_i = w0(1 − coverage_i), w0 ≈ 0.05–0.1; σ ×1.5 if sex or population unknown; vertical canons off for children; trichion weight 0; refuse non-zero weight while status is `knowledge` [AAB]. AI term ≤ 25% of landmark information per region; depth weights ×0.25 when f₃₅ < 35 mm [AI].

## 5. Fitting, silhouettes, warping

- **R5.1 Stages:** 0 similarity; A masses (10–50 parameters) vs silhouettes and Tier A; B low-frequency warp (50–200 control points, length scale 30–40 mm); C per-vertex Laplacian, offsets capped ≈ 5 mm unless ≥ 2 views agree; D local refinement only where ≥ 2 views agree. [IG][ZB][YT][TR]
- **R5.2 Gates:** leave A at chamfer < 2% of n–gn (or 2–3 mm) and landmark RMS < 4% IOD; leave B at detector RMS < 3% IOD (pins < 1.5%) in every view including a held-out one; afterwards no landmark moves > 0.5 mm. Primary-likeness target: reprojection 2–3% IOD, silhouette 1–2 mm. [PC][TR][AS]
- **R5.3 Symmetry σ:** ≈ 1 → 2 → 4 mm by stage (ZB: 0.5 → 2–3); strong only where unobserved; ≥ 3–5 mm in scan wraps; never symmetrise output. [PC][ZB][SCW]
- **R5.4 Silhouettes:** occluding-contour correspondences recomputed each iteration, weighted per view and region; profile and midline landmarks (n, prn, sn, pg) weighted highest; visual-hull hinge only outside masks; hair and beard one-sided (margin 0–3 mm), cranium from the prior; a missing view never counts as agreement. [TR][PC][ZB][IG]
- **R5.5 Template warp:** Procrustes on ≥ 3 Tier A points → TPS (λ so residual ≈ σ_lm) → Laplacian; ARAP if cranium or jaw scale changes > 10%. [TR][SCW][PC]
- **R5.6 Scan wrap:** Huber data term at 1.5σ (σ 0.3–0.5 mm rig, 0.5–1 single camera, 2–3 periphery); NICP radius 15–20 → 8–10 → 4–5 mm → per vertex, α 100 → 20–50 → 5–10 → 1–2, β 1 → 0.5 → 0.2 → 0.05, caps 10 → 8 → 5 → 3 mm, normal gate 60° → 45°; reverse term 0.3–0.5; drop pairs in the 2–3 mm boundary band; finish with a 1–2 mm snap and 3–10 tangential iterations (λ 0.3–0.5). Annealing ✅; Shrinkwrap alone is never a wrap. [SCW]
- **R5.7 Caliper term:** Σ((‖X_a − X_b‖ − d − o)/σ)², overriding population priors; trilaterate from both tragi plus nasion. [TR][IG]
- **R5.8 Anti-shrinkage:** warn when ‖c‖² < k − 2√(2k); user-tagged handles ×2 weight, excluded from shrinkage; optional distinctiveness key, default 1.0, preview only ↔️. [LM][PC][ZB]
- **R5.9 Coverage:** all views within |yaw| < 20° → depth "prior-driven"; projection is "measured" only with a front view plus one at |yaw| ≥ 60°. [RD][AS][RPP]
- **R5.10 Paintover:** flow → per-vertex Δx (σ_w ≈ 2 px) with a cotan Laplacian; reject if another view's RMS rises > 0.5% IOD. [PC]

## 6. Blender outputs

- **R6.1 Topology:** fixed quads, stable vertex order, UVs, topology hash; never remesh in the add-on. [YT][SCW]
- **R6.2 Shape keys:** one per stage, slider max 1.5 [ZB]; `scan_fit`, never applied [SCW]; region keys ±3 mm [PC]; characteristic expression 0–1, default 0 [AS]; caricature S(α) = M + α(S − M) [LM]; monochrome compensation [TR].
- **R6.3 Attributes:** depth σ from (JᵀJ)⁻¹ as a colour attribute [BA]; `ai_prior_weight`, `confidence` [AI]; 20–30 self-authored plane-region groups [AAB].
- **R6.4 Scene:** one locked camera per photo with its background image (Depth Front, opacity 0.3–0.5), bound to markers; 24 mm eye spheres; brow and hairline curves. [YT][ZB]
- **R6.5 Metadata:** `output_scale`; material shrink (clay 8–15%, bronze 1–3%); α; `{licence, commercial_ok}` for each prior. [TR][BA]

## 7. Texture projection

- **R7.1 View weighting:** cos^k θ (k = 2–4), cut off at 70–75°, depth-tested, with per-camera gains. Work in linear float; fill holes by push-pull and dilate 16 px at 4K. [SCW]
- **R7.2 View roles:** only even or cross-polarised views feed albedo; directional views feed landmarks and silhouettes. Prefer front and 3/4 views over profiles, and discard AI albedo. [RPP][YT][AI]

## 8. Diagnostics and validation

- **R8.1 Breakdown sheet** per camera, numpy-side: photo, clay render, 50% overlay, difference, edges, silhouette with chamfer, flipped, blurred (σ 3% face width), 64 px thumbnail, grayscale, 3 Hz blink GIF, residual arrows. [LM][PC][AS]
- **R8.2 Reports:** landmark error % IOD worst first; per-view RMS and IoU; d and f₃₅ per photo; asymmetry vector; leave-one-out RMS on ≥ 2 held-out photos; caliper sheet (Δ > 2 mm Tier A, > 3 mm Tier B); canon z-scores in art vocabulary; a lint flagging only |model − photo| > 2σ_photo, or |z| > 2.5 where no photo sees the region. [IG][TR][AAB][LM][PC]
- **R8.3 Identity embeddings:** relative only, on textured matched-light renders; a large textured-vs-clay gap means geometry is not carrying the likeness. [LM][AI]
- **R8.4 Synthetic harness:** 3–8 cameras, 24–135 mm, 0.4–3 m, yaw ±90°; pass at focal error < 5% and rotation < 2° when yaw spans ≥ 60°; shape by the NoW protocol. [AWL]
- **R8.5 Wrap acceptance:** median < 0.3, RMS < 0.5, p95 < 1.5 mm; area ratio 0.2–5, no flips; detail median > 0.3 mm = failed wrap; never claim better than the modality (≈ 0.2 mm ✅ to 1 mm 📄). [SCW]
- **R8.6 Export tolerances** (block approval): lid margins, vermilion, alar rim 0.2–0.3 mm; nose tip, ear rims, chin 0.5; cheeks, forehead 1.0; back of head, neck 1.5–2. [PC]

## 9. Failure modes to detect

| Failure | Detector | Action | Cite |
|---|---|---|---|
| Close camera | d < 1.0 m: warn; < 0.8 m: strong warning; < 0.6 m | down-weight depth landmarks; below 0.6 m, use for texture only | [IG][YT][RD][BA] |
| Wrong focal length | slope > 5%; focal off EXIF or same-lens views by > 10–15% | free focal; check pins or crop | [LM][BA] |
| Mirrored photo | flip lowers residual by > 20%; pose > 3σ from nominal | flip and re-solve | [RD][RPP] |
| Unsolved pitch | fewer than 2 views constrain pitch | ear weight 0 | [LM] |
| Pose read as asymmetry | left/right difference correlates with one view's roll or yaw | flag | [LM] |
| Liquify / retouch | signed jaw and eye residual pattern | robust scale; σ ×2–3 | [AS] |
| Expression leakage | mouth > 3% IOD; residuals shaped like action units | exclude; ask for a neutral photo | [RPP][AAB] |
| Crop | aspect ratio not native | free the principal point, or ask for the original | [YT][ZB] |
| Lens swap; mixed dates | LensModel differs; dates span > 18 months | split the group; warn | [RPP][RD] |
| Prior-driven depth | no view at \|yaw\| ≥ 60° | heat-map; ask for a profile | [RD][AS] |
| Shrinkage; over-symmetry | χ² test; mirror RMSD < 0.3 mm | warn | [LM] |
| Hero view; outlier view | weight > 40%; RMS > 3σ or > 2× median | cap; down-weight | [AS][RD][ZB] |
| Conflicting pins | > 3σ after convergence | list them | [YT] |
| AI depth contradicts photos | \|Δ\| > 3σ at g, prn, sn, pg | AI term off in that region | [AI] |
| Hair fitted as cranium | scalp outside the hair mask | one-sided hinge | [PC][SCW] |
| Edit breaks other views | drift > 0.5 mm; RMS rises > 0.5% IOD | reject | [PC] |
| Bad solve | front yaw or roll > 2°; profile outside 85–95°; distance off the tape by > 10% | distrust the view | [RPP] |

## 10. Licence constraints

- **L1** `assets.toml` per file (SPDX licence, `commercial_ok`, sha256, attribution); bundle nothing non-commercial or unknown; re-verify each release. [AWL]
- **L2** Default template: Blender Studio Human Base Meshes (CC0 ✅); MPFB2 assets disputed ↔️; ICT-FaceKit unverified. [YT][AWL][BA]
- **L3** Only FLAME 2023 Open (CC BY 4.0; texture model BY-NC-SA) is commercial-safe 📄; FLAME 2017–2020, BFM, LSFM, FaceScape and NeRSemble load from user paths with a commercial warning. [AWL][BA]
- **L4** MediaPipe (Apache-2.0), 3DDFA_V2 (MIT), face-alignment (BSD-3), eos (Apache-2.0) shippable once checked; dlib-68 and InsightFace weights are not. [AWL]
- **L5** AI meshes from user files only, never auto-uploading faces; Hunyuan3D excludes EU/UK/South Korea 📄; TRELLIS has non-commercial NVIDIA dependencies 📄; Meshy free outputs are CC BY 4.0 📄. [AI]
- **L6** MetaHuman is under the UE EULA ✅ (not bundleable); the Asaro head and modern atlases are in copyright. [AWL][AAB]
- **L7** Offline by default (network permission declared); consent record kept, face data is biometric (GDPR ↔️); share sheets only within consent. [AWL][RPP][AI][PC]

## 11. Open questions

1. What millimetre tolerance makes a likeness read to people who know the sitter? Only a 1–2 mm heuristic exists. [ZB][AS]
2. How should the σ values, the 25% AI cap and the gates be calibrated? This needs real scans with held-out photos. [LM][AI][PC]
3. Several anthropometric values are unconfirmed: the IPD SD, tragion depths, MRD1 by age, Hertel and canthal tilt by ancestry, ear tilt and head length. [BA][TR][PC][LM]
4. Does caricature help realistic 3D, and do embedding scores track human judgement? [LM][IG]
5. Which Blender export and viewport sensor conventions are correct? ↔️ [ZB]
6. How much does each extra view gain, and which oblique angle is best? Do phone processing pipelines alter face geometry? [RPP]
7. How large are caliper error and the pressed-landmark offsets? [TR]
8. Licences remain unconfirmed for MPFB2 assets, ICT-FaceKit, the FaceBuilder EULA, Tripo and BodyParts3D. [AWL][BA][YT][AI]
9. How accurate are AI generators and face fitters against scans? No mm benchmark exists. [AI][RD]

[README]: ../community/README.md
[LM]: ../community/likeness-mistakes.md
[RPP]: ../community/reference-photography-protocol.md
[RD]: ../community/reddit-face-from-photos.md
[IG]: ../community/instagram-social-sculptors.md
[PC]: ../community/polycount-likeness.md
[ZB]: ../community/zbrush-to-blender-likeness.md
[YT]: ../community/youtube-likeness-blender.md
[AS]: ../community/artstation-likeness.md
[TR]: ../community/traditional-portrait-sculpture.md
[AAB]: ../community/art-anatomy-books.md
[SCW]: ../community/scan-cleanup-wrapping.md
[AWL]: ../community/awesome-lists-resources.md
[AI]: ../community/ai-assisted-sculpting.md
[BA]: ../community/blenderartists-forum.md
