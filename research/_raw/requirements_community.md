# Engine requirements: community & artist knowledge

Digest for the numpy-only fitting engine and the Blender add-on (multi-view perspective camera solving, landmark bundle adjustment with anatomical priors, template warping, silhouette/profile fitting, shape keys, texture projection). Compiled 2026-11-20 from the 14 notes in `research/community/` and their verification logs (corrections applied). Area overview: [README][README].

**Evidence caveat.** The area holds 19 ✅ / 63 📄 / 824 🧠 / 250 ↔️ claims (≈7% sourced). **Unless marked, every number below is 🧠 and provisional.** Ship such values as named, configurable defaults, and calibrate them with the synthetic harness (R8.4) and held-out photos before trusting them. Pinhole arithmetic is reliable as geometry.

Units: engine mm, Blender m (scale 1.0, display mm). IOD = inter-ocular (interpupillary) distance ≈ 63 mm.

## 1. Ingest and photo audit

- **R1.1 EXIF.** Parse `FocalLengthIn35mmFilm`, `FocalLength`, `Make`, `Model`, `LensModel`, `DateTimeOriginal` and `Orientation`. Bake orientation into working copies; keep originals untouched. Never crop or resize without recording it. [RD][RPP]
- **R1.2 Capture manifest** (one JSON per session):
  - per photo: `view_tag`, nominal yaw and elevation, `lens_id`, tape distance, expression, hair, glasses, lighting tag (even / cross-pol / directional), `source_type`, `mirrored`, `anamorphic_desqueezed`, `retouch_risk`, date;
  - per session: caliper pairs with σ, scale objects, consent record.

  [RPP][AS]
- **R1.3 Intrinsics groups.** Group key: (Make, Model, LensModel, FocalLength, W, H, still/video). log f is shared within a group (tie σ 0.02) and never across groups; video always gets its own group. Phones swap lenses silently, so group on `LensModel`. [RPP][BA]
- **R1.4 Quality gates.** [RPP]
  - eye aspect ratio < 0.2 → reject as a blink;
  - bottom 20% by variance of the Laplacian → down-weight;
  - face < 250 px wide → warn; < 120 px → reject;
  - > 2% clipped skin pixels → no photometric terms;
  - mouth aperture > 3% IOD, or a smile → exclude from identity;
  - hair over the ears → drop ear and temple landmarks.
- **R1.5 Distance estimate.** d = f_px · 63 mm / IPD_px for near-frontal views. Apply the tiered policy in §9. [IG][YT][RD][BA]
- **R1.6 Mirror test.** Solve the image and its horizontal flip; a > 20% drop in multi-view residual marks it mirrored. A front-camera `LensModel` → ask the user. [RD][BA][YT]
- **R1.7 Phone lens correction.** If f₃₅ ≤ 16 mm, or the face lies beyond ~60% of the half-diagonal, inflate σ ×2 or exclude. The warping is ✅; the thresholds are 🧠. [AS]
- **R1.8 View weighting.** Weight each view by 1/(views in its 15° bin), and cap any single view at ≤ 40% of the total data weight. [RPP][AS]
- **R1.9 Video.** Keep ≤ 3 frames per yaw/elevation bin and drop frames whose relative angular speed exceeds 10–15°/s (rolling shutter) ↔️. [RPP]

## 2. Camera model and multi-view solve

- **R2.1 Joint solve.** One least-squares problem: R and t per view, f per focal group, shape and scale global. Parametrise with inverse depth, initialise with weak perspective, then refine under full perspective. [ZB]
- **R2.2 Focal priors** (log-normal on f₃₅; σ_log = SD of ln f):

| Situation | Median | σ_log | Cite |
|---|---|---|---|
| Uncropped original with EXIF | EXIF | 0.03 (plus lens-group tie 0.02) | [ZB][YT][RPP] |
| EXIF but possible crop or digital zoom | EXIF | 0.05–0.10 | [RD][BA] |
| Physical focal length, guessed sensor | computed | 0.10 | [ZB] |
| Phone, no EXIF | 26 mm | 0.25 | [RD] |
| Source-typed (press / studio / film or video / phone rear / selfie) | 135 / 100 / 50 / 26 / 26 mm | 0.5 / 0.4 / 0.7 / 0.6 / 0.1 | [AS] |
| Unknown | 50 mm | 0.6 | [RD][ZB] |

  The current engine default of 0.35 cannot cover phone main cameras (26 mm sits ≈1.9σ from a 50 mm median), so use 0.6 when nothing is known.
- **R2.3 Freeing focal length.** Free it only when the views span ≥ 60° of yaw or include a profile; otherwise fix it at the prior, and for near-frontal views at d > 1 m tie focal and distance through the IPD prior. [RD][IG][YT]
- **R2.4 Distance prior.** A tape-measured z gets σ ≈ 5 cm (it breaks the focal–distance degeneracy). Without one, median 1.0 m, σ_log 0.7. [RPP][ZB]
- **R2.5 Intrinsic nuisances.** Principal point at the centre with σ = 1% of max(W, H), or 10% if cropped. k1 = 0 with σ 0.02; reject ultra-wide images. Pixel aspect 1.0 with σ 0.01 unless the frame is flagged anamorphic. [ZB][AS]
- **R2.6 35 mm conversion** on the diagonal (43.27 mm, CIPA; `focal_px_from_35mm`). A width-based conversion is ≈4% short on 4:3 images. Per-maker practice is unverified ↔️. [BA]
- **R2.7 Pose priors from view tags.** Yaw σ 10° freehand or 5° with floor marks; pitch σ 5° on the main ring and 8–10° on the high and low rings; roll σ 3°. A view more than 3σ from its nominal pose is mislabelled or mirrored. [RPP]
- **R2.8 Perspective-error signature.** The radial residual is ≈ ρ_i·δ_i·(1/d − 1/d′). Regress `BundleResult.per_view_residuals` on ρ_i·δ_i; a slope implying > 5% magnification error → free the focal length or request a distant photo. [LM]
- **R2.9 Blender export.** Keep one convention. `to_blender_camera` uses sensor fit HORIZONTAL with lens and both shifts normalised by width. The notes' AUTO plus max(W, H) form is equivalent only if used consistently. Render resolution W × H, pixel aspect 1. Unit-test the signs by reprojecting a known landmark; the conventions are unconfirmed by verification. [BA][YT][ZB]

## 3. Landmarks and data formats

- **R3.1 Landmark schemes** stored as barycentric embeddings (face index plus weights) on the working template: iBUG 68, WFLW 98, MediaPipe 478 (468 without irises), ARKit 1,220, FLAME 51 static + 17 dynamic. Ship a 68↔478 correspondence so all schemes share one `levenberg_marquardt` residual. Version a landmark → vertex table per base mesh. [AWL][BA]
- **R3.2 Pins** as `Pin{view, xy_px, surface(tri, bary), sigma, source}`. Re-solve after every edit; cap auto-suggested pins at ≈12 per view. [YT][BA]
- **R3.3 Noise** (× IOD unless stated):
  - automatic interior points 0.02–0.03;
  - jaw and cheek contour 0.05–0.08, residual along the silhouette normal only;
  - brows 0.04–0.06;
  - ears 0.06–0.10, weight 0 when |yaw| < 30° or until pitch is constrained by ≥ 2 views;
  - reviewed vendor-style pins 1.5% (corners), 2.5% (lid and lip contours), 4% (face oval);
  - user pins 1–2 screen px at the placement zoom (other notes: 0.01 × IOD or 0.75% IOD);
  - hairline σ 3–5 mm and brows ≈ 2 mm never feed camera solving;
  - Huber δ = 2σ; down-weight a view with RMS > 3σ or > 2× the median.

  [RD][BA][YT][ZB][PC][LM]
- **R3.4 Landmark tiers.** [TR]
  - A, bony (n, t, ex, en, prn, sn, pg, gn, zy, go): σ 1–2 mm; Procrustes anchors.
  - B, soft (ch, sto, ls, li, al): σ 2–4 mm.
  - C, hair-dependent (v, eu, op, tr): one-sided bounds only, never used for scale.
- **R3.5 Sliding contours.** Jaw, cheek and ear outlines are re-associated with the nearest occluding-contour vertex every iteration, never fixed vertex IDs. [YT][ZB][TR]
- **R3.6 Brows and hairline.** Brows (≥ 5 points each) and the hairline polyline are fit targets exported as Blender curves and kept out of the skin-shape loss. User-clicked moles and scars seen in ≥ 2 views become bundle-adjustment tie points and texture anchors. [AS]
- **R3.7 Identity and expression.** One identity vector for the set and a per-view expression vector with prior N(0, 1) in model units. Expression is fixed at 0 for views tagged neutral. Drop lip landmarks from open-mouth views and lid landmarks from squints. [RD][BA][ZB]

## 4. Priors (mean ± σ)

| Prior | Value | Badge | Cite |
|---|---|---|---|
| IPD scale | 63 ± 3.5 mm (3.7 ZB, 4 IG); a measured PD or caliper overrides at ± 1 mm | 🧠 ↔️ (mean ≈63.36 per a secondary source; SD unconfirmed) | [BA][ZB][IG] |
| ID-1 card | 85.60 mm, σ 0.5 mm | 🧠 | [RPP] |
| Iris (HVID) | 11.7 ± 0.5 mm, only if the iris is ≥ 20 px; device means 11.77–12.40 mm | ↔️ | [IG][YT] |
| Eyeball | radius 12 ± 0.5 mm (24 mm sphere) | 🧠 | [LM][AI] |
| Cornea ahead of lateral orbital rim | 16 ± 2.5 mm; populations span 8–23 mm | ↔️ | [LM][PC] |
| MRD1 | 4.5 ± 1 mm; sources give 3.5–4.5 mm, so consider centring at 4.0 | ↔️ | [LM][PC] |
| Sclera above the iris | hinge penalty unless ≥ 2 views show it | 🧠 | [LM] |
| Lid margin on the globe | +0–0.5 mm, σ 0.3 mm | 🧠 | [SCW] |
| Ear | length 60 ± 4 mm; axis 20 ± 7° (one cohort 15.6 ± 3.9°); protrusion 17 ± 4 mm; tragion vs orbitale 0 ± 4 mm, after pitch is solved | 🧠 / ↔️ | [LM][PC] |
| Cranium | g–op 175–205 mm, σ ≈ 7 mm within one sex; scalp 4–8 mm | ↔️ (unconfirmed) | [PC] |
| Tragion depths (t–n, t–sn, t–gn) | σ 6–8 mm as population priors; 1.5–2 mm when measured; values reconstructed, not taken from Farkas | ↔️ | [TR] |
| Pressed caliper offsets (zy–zy, go–go, eu–eu) | +2 to +5 mm | ↔️ | [TR] |
| Symmetry and midline | `sigma_sym` 2.0 mm, `sigma_mid` 1.5 mm (engine defaults) plus the schedule in R5.3 | 🧠 | [LM][PC][BA] |
| Landmark prior | `Priors.sigma` 8 mm in stage B, relaxed to 3–4 mm in stage C; the scalar is uncalibrated | 🧠 | [IG][LM] |
| Canon ratios (weak) | en–en/en–ex 1.08 ± 0.10; al–al/en–en 1.05 ± 0.12; ch–ch/en–en 1.55 ± 0.12 (📄 1.52–1.59); ch–ch/IPD 0.83 ± 0.07; (g–sn)/(sn–me) 0.90 ± 0.08; (sn–sto)/(sn–me) 0.32 ± 0.03; (sa–sba)/(n–sn) 1.15 ± 0.12; eye line 0.50 ± 0.02 of v–me | 🧠 / ↔️ | [AAB] |
| External mesh as a point-to-plane prior | photogrammetry 0.5–1 mm (eyes and hair masked or σ ×5); multi-view pin fit 1–1.5 mm; scan head of another person 3–5 mm; atlas skull 4–6 mm | 🧠 | [YT][AWL] |
| AI mesh, by c = cos(normal, conditioning view) | c > 0.7: 3–5 mm; 0.3–0.7: 6–10 mm; ≤ 0.3: ≥ 15 mm or off; off on hair, beard, eyes, mouth interior, ears | 🧠 (no benchmark found) | [AI][RD] |
| Ancestry outside the prior's population | σ × 1.5 (a guess) | ↔️ | [AWL] |

Canon rules [AAB]:
- E_canon = Σ w_i((r_i − μ_i)/σ_i)², with w_i = w0·(1 − coverage_i) and w0 ≈ 0.05–0.1 of the landmark term.
- Widen σ ×1.5 when sex or population is unknown.
- Turn the vertical canons off for children; give trichion weight 0.
- The loader refuses a non-zero weight while a prior's status is `knowledge`.

The AI term is capped at ≈ 25% of the landmark information per region, and its depth weights are multiplied by 0.25 when the conditioning photo has f₃₅ < 35 mm [AI].

## 5. Fitting schedule, silhouettes, warping

- **R5.1 Stages,** mirroring "big to small" [IG][ZB][YT][TR]:
  - 0: similarity pose and scale from 6–10 robust landmarks plus the silhouette.
  - A: masses (10–20 parameters, or 10–50 identity parameters) against silhouettes and Tier A landmarks.
  - B: low-frequency warp (50–200 RBF or cage control points; length scale 30–40 mm).
  - C: per-vertex offsets with a Laplacian regulariser, capped near 5 mm unless ≥ 2 views agree.
  - D: local refinement only where ≥ 2 views agree.
- **R5.2 Gates** [PC][TR][AS]:
  - leave A when the silhouette chamfer is < 2% of n–gn (or < 2–3 mm) and landmark RMS < 4% IOD;
  - leave B when detector RMS < 3% IOD (user pins < 1.5%) in every view, including one held-out photo;
  - during C and D no landmark may move > 0.5 mm;
  - primary-likeness target: interior reprojection < 2–3% IOD and silhouette < 1–2 mm.
- **R5.3 Symmetry schedule.** About 1 → 2 → 4 mm across the stages (ZB uses 0.5 → 2–3), with a strong pull kept only in unobserved regions and ≥ 3–5 mm for scan wraps. Never symmetrise the output. [PC][ZB][SCW]
- **R5.4 Silhouette energy** [TR][PC][ZB][IG]:
  - recompute occluding-contour correspondences every iteration, weighted per view and per region;
  - give the profile silhouette and the midline landmarks (n, prn, sn, pg) the highest weight;
  - apply a visual-hull hinge only to points outside a mask;
  - treat hair and beard masks as one-sided outer bounds (margin 0–3 mm, no inward pull), filling the cranium from the prior;
  - never count a missing view as agreement.
- **R5.5 Template warp ("pointing").** Procrustes/Umeyama on ≥ 3 Tier A points → TPS/RBF (λ chosen so the landmark residual ≈ σ_lm) → Laplacian fill. Switch to ARAP when the cranium or jaw scale changes > 10%. [TR][SCW][PC]
- **R5.6 Mesh-to-scan wrap** [SCW][AI]:
  - point-to-plane Huber term at 1.5σ_data, with σ_data 0.3–0.5 mm (camera rig), 0.5–1 mm (one camera), 2–3 mm (periphery);
  - four NICP stages: radius 15–20 → 8–10 → 4–5 mm → per vertex; α 100 → 20–50 → 5–10 → 1–2; β 1 → 0.5 → 0.2 → 0.05; caps 10 → 8 → 5 → 3 mm; normal gate 60° → 45°;
  - a reverse term at weight 0.3–0.5; reject pairs beyond max(3·MAD, the stage cap) or inside the 2–3 mm boundary band;
  - a lip hinge (margin 0–0.2 mm) and an edge-length log-ratio σ ≈ 0.3;
  - finish with a 1–2 mm normal snap and 3–10 tangential Laplacian iterations (λ 0.3–0.5).

  The annealing schedule is ✅ in the NICP literature; Blender's Shrinkwrap is never the wrap.
- **R5.7 Caliper term.** E_cal = Σ((‖X_a − X_b‖ − d_ab − o_ab)/σ_ab)². It overrides population priors and supports trilateration from both tragi plus nasion. [TR][IG][RPP]
- **R5.8 Anti-shrinkage** [LM][PC][ZB][IG]:
  - shrinkage detector: warn "pulled toward average" if ‖c‖² < k − 2√(2k) for whitened coefficients;
  - user-tagged caricature handles (3–5 regions) get landmark weight ×2 and are excluded from shrinkage;
  - an optional distinctiveness shape key (default 1.0, preview only, recorded in metadata) ↔️.
- **R5.9 Coverage mode** [RD][AS][RPP]:
  - max |yaw| < 20° → label depth "prior-driven" and ask for a profile;
  - nose and chin projection count as "measured" only with a front view plus a view at |yaw| ≥ 60°, and the jaw underside only with a low view.
- **R5.10 Paintover ingestion.** Take the dense flow from render to paintover; solve per-vertex Δx through the projection Jacobians (σ_w ≈ 2 px) with a cotan Laplacian. Reject the edit if any other view's RMS rises > 0.5% IOD. [PC]

## 6. Blender outputs

- **R6.1 Topology.** Fixed quad topology with stable vertex order and UVs, checked by a topology hash; never remesh inside the add-on. The default base comes from a permissive licence (§10). [YT][SCW]
- **R6.2 Shape keys:**
  - one per fitting stage, slider max 1.5 [ZB];
  - `scan_fit`, never applied [SCW];
  - region sliders (eyes, nose, mouth, jaw, ears, cranium) limited to ± 3 mm [PC];
  - an optional characteristic-expression key, 0–1, default 0 [AS];
  - caricature S(α) = M + α(S − M), excluding scale and pose [LM];
  - a monochrome-compensation key held at 0 during fitting [TR].
- **R6.3 Attributes:**
  - per-vertex depth σ from (JᵀJ)⁻¹ as a colour attribute [BA][RD];
  - `ai_prior_weight` and `confidence` [AI];
  - a `fit_weight` vertex group [SCW];
  - 20–30 self-authored plane-region vertex groups for per-region regularisation and sculpt masks; do not copy the Asaro facets [AAB].
- **R6.4 Scene objects:**
  - one locked camera per photo, with its background image (Depth Front, opacity 0.3–0.5, Stretch), bound to timeline markers;
  - separate 24 mm eye spheres;
  - brow and hairline curves.

  [YT][ZB][AS]
- **R6.5 Export metadata:** `output_scale`, `material_shrink` (fired clay 8–15%, bronze 1–3%), α, and `{licence, commercial_ok}` for every prior. [TR][BA]

## 7. Texture projection

- **R7.1 Projection weights.** Weight views by cos^k θ (k = 2–4), cut off at 70–75°, depth-test against the fitted mesh, and solve per-camera gains on overlaps. Work in linear float and write sRGB only on save. Fill holes by push-pull, then dilate 16 px at 4K (≈0.10 mm per texel). [SCW]
- **R7.2 View selection.** Only even or cross-polarised views feed albedo and photometric terms; directional views feed landmarks and silhouettes, with a per-image gain. Prefer front and 3/4 views, because profiles smear the cheeks. Discard AI albedo. [RPP][YT][AI]
- **R7.3 Colour bakes.** Use the Emit trick with Save as Render off; normal maps are OpenGL. [SCW]

## 8. Diagnostics and validation

- **R8.1 Per-camera breakdown sheet,** generated numpy-side so it does not depend on the Blender version: photo, clay render, overlay at α 0.5, difference, Canny edges, black silhouette with chamfer, flipped, blurred (σ 3% of face width), 64 px thumbnail, grayscale, 3 Hz blink GIF, residual arrows. [LM][PC][AS]
- **R8.2 Reports** [IG][TR][AAB][LM][PC]:
  - per-landmark reprojection error in % IOD, worst first;
  - per-view RMS in px and % IOD; per-view IoU and per-region mismatch;
  - d and f₃₅ per photo; the left/right asymmetry vector;
  - leave-one-view-out RMS on ≥ 2 held-out photos;
  - a caliper sheet, flagging Δ > 2 mm (Tier A) or > 3 mm (Tier B);
  - canon z-scores in art vocabulary;
  - a likeness lint that flags only |model − photo| > 2σ_photo, or |z| > 2.5 where no photo sees the feature, and never pulls a photo-supported feature toward the mean.
- **R8.3 Identity embeddings.** The cosine score is relative only, on textured, matched-light renders. A large gap between textured and clay renders means the geometry is not carrying the likeness. [LM][AI]
- **R8.4 Synthetic harness.** Render CC0 or CC BY heads through 3–8 cameras (24–135 mm equivalent, 0.4–3 m, yaw ±90°). Accept focal error < 5% and rotation error < 2° when the views span ≥ 60°. Score shape with the NoW protocol. [AWL]
- **R8.5 Wrap acceptance.** Face distance median < 0.3 mm, RMS < 0.5 mm, p95 < 1.5 mm; area ratio 0.2–5 with no flipped faces; minimum angle > 10–15°. A detail-layer median |d| > 0.3 mm means the wrap failed. Never claim more accuracy than the capture modality (≈0.2 mm ✅ to 1 mm 📄). [SCW]
- **R8.6 Export likeness tolerances.** Lid margins, vermilion and alar rim 0.2–0.3 mm; nose tip, ear rims and chin 0.5 mm; cheeks and forehead 1.0 mm; back of head and neck 1.5–2 mm. Exceeding them blocks "approved" status. [PC]

## 9. Failure modes the engine must detect

| Failure | Detector | Action | Cite |
|---|---|---|---|
| Close or selfie camera | d < 1.0 m warn; < 0.8 m strong warning; < 0.6 m | below 0.8 m down-weight depth landmarks unless focal is pinned; below 0.6 m texture and 2D cues only | [IG][YT][RD][BA] |
| Wrong focal length hidden by distance | radial-residual slope > 5%; solved focal > 10–15% off EXIF or same-lens views | free focal; flag a bad pin or crop | [LM][BA] |
| Mirrored image | flip lowers residual > 20%; pose > 3σ from nominal | flip and re-solve | [RD][RPP] |
| Unsolved pitch → ear height | pitch constrained by fewer than 2 views | ear weight 0 | [LM] |
| Pose read as asymmetry | a left/right difference correlates with one view's roll or yaw | flag "suspicious asymmetry" | [LM] |
| Liquify or retouching | consistent signed jaw and eye residuals not explained by pose | robust per-view scale; σ ×2–3 | [AS] |
| Expression leakage | mouth > 3% IOD; residuals that look like action units | exclude; request a neutral photo | [RPP][AAB] |
| Blink, blur, small face, clipping | R1.4 gates | reject or down-weight | [RPP] |
| Crop or principal-point shift | aspect ratio unlike the native one | free the principal point (σ 10%) or ask for the original | [YT][ZB] |
| Lens swap; mixed dates | `LensModel` differs; dates span > 18 months | separate focal group; warn | [RPP][RD] |
| Prior-driven depth | max \|yaw\| < 20°; no view at \|yaw\| ≥ 60° | heat-map; ask for a profile | [RD][AS] |
| Shrinkage; over-symmetry | ‖c‖² < k − 2√(2k); mirror RMSD < 0.3 mm with asymmetric photos | warn | [LM] |
| Hero-view dominance; outlier view | a view's weight > 40%; RMS > 3σ or > 2× the median | cap; down-weight | [AS][RD][ZB] |
| Conflicting pins | > 3σ after convergence | list them worst first | [YT] |
| AI depth contradicts photos | \|Δ\| > 3σ at g, prn, sn, pg | AI term off in that region | [AI] |
| Hair read as cranium | scalp outside the hair mask, or hair fitted as skull | one-sided hinge plus a cranial prior | [PC][SCW] |
| Detail pass or paintover breaks other views | landmark drift > 0.5 mm; another view's RMS rises > 0.5% IOD | flag; reject | [PC] |
| Bad solve | front yaw or roll > 2°; profile outside 85–95°; distance > 10% off the tape | distrust the view | [RPP] |

## 10. Licence and data constraints

- **L1.** Ship an `assets.toml` row per external file (`name`, `version`, `sha256`, `spdx_licence`, `commercial_ok`, `attribution`, `source_ref`, `retrieved`). Bundle nothing whose `commercial_ok` is false or unknown, and re-verify every release. [AWL]
- **L2.** Default template: Blender Studio Human Base Meshes (CC0 ✅), or MPFB2 once its asset licence is settled (↔️), or ICT-FaceKit once verified. [YT][AWL][BA]
- **L3.** FLAME: only FLAME 2023 Open (CC BY 4.0, attribution; its texture model is BY-NC-SA) may enter a commercial path 📄. FLAME 2017–2020, the FLAME add-on, BFM, LSFM, FaceScape and NeRSemble load only from user-supplied paths, with a warning when the project is flagged commercial. [AWL][BA]
- **L4.** Landmark and fitting references: MediaPipe (Apache-2.0), 3DDFA_V2 (MIT), face-alignment (BSD-3) and eos (Apache-2.0) are shippable once their licences are checked. The dlib 68-point model (300-W terms) and InsightFace weights are non-commercial and not shippable. [AWL]
- **L5.** AI meshes are ingested only from files the user supplies. Hunyuan3D excludes the EU, UK and South Korea 📄; TRELLIS is MIT, but some NVIDIA dependencies are non-commercial 📄; Meshy free outputs are CC BY 4.0 📄. Never upload faces automatically. [AI]
- **L6.** MetaHuman is usable outside Unreal ✅ but falls under the Unreal Engine EULA, so it cannot be bundled. The Asaro head and the modern atlases are in copyright, so author your own regions. [AWL][AAB]
- **L7.** The extension is offline by default: declare the network permission and do no scraping. Store a consent record in the manifest, since face data is biometric (GDPR special category ↔️). Share breakdown sheets only as far as the sitter's consent covers. [AWL][RPP][AI][PC]

## 11. Open questions

1. What millimetre or reprojection tolerance makes a likeness "read" to familiar viewers? Only a 1–2 mm heuristic exists ↔️. [ZB][AS][LM]
2. All σ values, the 25% AI cap and the stage gates are uncalibrated; we need a real-scan calibration set with held-out photos. [LM][AI][PC]
3. Which anthropometric values need confirming? IPD SD, tragion depths, MRD1 by age, Hertel and canthal tilt by ancestry, ear tilt, head length, scalp thickness (check the anatomy notes and ANSUR II). [BA][TR][PC][LM]
4. Does caricature help realistic 3D, and do embedding scores track human likeness judgements? [LM][IG]
5. What are the right Blender camera export conventions, and does the viewport use a doubled sensor (↔️)? [ZB]
6. How much does each extra view gain in mm, are 30° or 45° obliques better, and do phone computational pipelines alter geometry? [RPP]
7. What is caliper error for non-expert operators, and what are the pressed-landmark offsets? [TR]
8. Licences still to confirm: MPFB2 assets, ICT-FaceKit, the FaceBuilder EULA on exported heads, Tripo, BodyParts3D, the Lee Perry-Smith head. [AWL][BA][YT][AI]
9. What is the mm accuracy of 2025–26 AI generators and face fitters against scans? No benchmark exists. [AI][RD]

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
