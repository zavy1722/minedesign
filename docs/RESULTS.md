# Face3D results: release gates (WP-23, M6; updated by FU-03 and FU-04)

Status of face3d 0.2.0 (engine v2) against the DESIGN 7.4 fault-injection matrix, the DESIGN 7.5 honesty
metrics and the committed baseline scorecard. Everything here is **test-bed tier 1**: synthetic subjects,
simulated detections, seeded (provenance `synthetic`). Nothing is validated against a scan (H8); all
targets are 🆕 (uncalibrated design targets) and all measured values are 🔢 (checked numerically on this
test bed only).

**No gate was weakened.** Targets that are not met are listed as *calibration-pending* with the measured
value, the cause and the proposed fix; the DESIGN 7.4/7.5 tables keep their thresholds (a status note
under each points here). Honesty conditions that must hold whatever the detection rate (no false flip, no
false "keep", never over-confident, no focal labelled "measured" on the strength of a prior) are asserted
separately. **All of them pass.** The release blocker of the WP-23 run, `exif_crop.focal_label`, was
closed by FU-03 (section 3.1, "Closed by FU-03").

Engine behaviours that changed and are recorded as deviations or amendments in DESIGN: the observe stage
reports sigma_rep with the FU-02 factor, calibrated against the noise before the QA sigma multipliers, and
the per-vertex sigma_n uses the shape covariance with a recalibrated residual term (WP-23; DESIGN 4.13 /
D-16 and 4.15; sections 4.1 and 4.2); the focal label "measured" is earned from the photos, the EXIF focal
prior can be overruled by the photos, Q-SMALL measures the pose-independent face width and the post-BA
Q-RETOUCH test is wired (FU-03; DESIGN 4.1, 4.12, 4.13, H5; section 3.1); the mirror test and the expression re-tag
use thresholds derived from their own null distributions, and the observation noise *can* be made
anisotropic along image tangents derived from the detections (opt-in, off by default) (FU-04; DESIGN 4.4,
4.9, 4.10; section 3.1, "Changed by FU-04").

**FU-04 in one paragraph (as amended by its review).** The engine can narrow the noise model where the
scheme documents a curve direction (16 of the 44 landmarks), but this ships **off**
(`pipeline.image_tangents` = false): the direction metadata is an unmeasured expert reading, and on the
WP-01 detector simulator, whose anisotropic noise is unrelated to it, the tangent-derived noise rejects
4.5 % of good observations (DESIGN 7.4 bound 2 %). The first FU-04 version shipped it on and re-built the
gate scenes so that the simulator's noise axes followed the scheme's own neighbour pairs; that made every
gate agree with the engine's assumption by construction, so it was reverted: **all gates are again
measured on the WP-01 simulator as is, with the shipped default** (section 3.1 gives the four
combinations). The "common cause" of the WP-23 note (isotropic noise) is therefore still there: clean-set
chi2_red 0.72, gamma 0.85. What FU-04 does ship is the recalibration of the single-view detectors: one
pending gate closed (`jaw_open.tpr`, 0/30 -> 28/30); the mirror, smile and retouch targets are
**unreachable at nominal detector noise** and stay pending with the measured rates and the reasons; every
honesty gate passes. The mirror test's "keep" now requires the power of its complete decision rule
(review finding; section 3.1). **Open owner decisions:** the tangent default (DESIGN 4.4), the narrowed
"every extremal landmark" item, and no set-level pooling of mirror evidence (DESIGN 4.10).

## 1. How to reproduce

| What | Command | Wall time here (4 cores) |
|---|---|---|
| Policy checks | `python tools/ci_checks.py` | ~10 s |
| Per-push gates (5 seeds) | `python -m pytest tests/test_policy_ci.py tests/test_fault_matrix.py tests/test_honesty_gates.py` | 1 min 30 s |
| Release run (30 seeds) | `python -m pytest -m slow` | 6 min 0 s (5 min 58 s before FU-04) |
| Tables of sections 3 and 4 | `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONPATH=. python tests/test_fault_matrix.py [--diagnostics]`, `... PYTHONPATH=.:tests python tests/test_honesty_gates.py` (BLAS pinned to one thread, as `tests/conftest.py` does: the gate runs fork a process pool; `--diagnostics` adds the runs of section 3.2) | 14 min 25 s with diagnostics (FU-04 added ten diagnostic conditions); 1 min |
| Scorecard v1 | `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m face3d.testbed.scorecard --seeds 30 --out tests/golden/scorecard_v1.json --compare tests/golden/baseline_scorecard_v0.json` | ~1.5 min |

Seeds: fault matrix and honesty 2300-2329 (per push 2300-2304), streams `SeedSequence(seed).spawn(4)` =
subject, rig, detector, fault; scorecard 1000-1029 (the baseline's). The gate runs use a process pool
(`FACE3D_GATE_WORKERS`, default min(4, cores)); every run is a pure function of its seed.

Scene of the gate runs: a WP-11 out-of-prior surface subject on the procedural CC0 head (0.8 mm RMS
asymmetry), 44 anatomical landmarks from the detector simulator at the DESIGN 4.4 nominal noise with
the nominal definition bias and **no** gross outliers (outliers are a fault row), 5 views, run as a
project through `face3d.pipeline` (ingest .. observe; fit and uncertainty for the surface gates). The
clean rig is the studio ring (85 mm, 1.5-3 m, yaw -90..90 deg) in a 1500 x 2000 px frame: it is the only
WP-01 protocol that is clean by the engine's own QA thresholds, apart from a few far views whose
face is just under 250 px wide (4 of 150 photos; section 3.3). Clean-set medians over 30
seeds: configuration RMS 2.41 mm, chi2_red 0.72, LOVO gamma 0.85 (sigma_rep factor 0.76), tier B on every
set (no metric scale reference, H4).

**Detector noise axes (the WP-01 simulator, unchanged).** The simulator draws the (normal, tangent)
noise of a landmark along one *random* image direction per landmark, the same in every view; every gate
uses it as is. `tests/test_fault_matrix.py::anatomical_noise_axes` can re-apply the same two noise
components (identical random draws) along and across the chord between the true projections of the
landmark's scheme neighbours, for the 16 landmarks whose scheme entry names neighbours. Those scenes are
**diagnostic only**: their "true" axes come from exactly the neighbour pairs the engine uses, so they are
the best case for the opt-in tangents by construction and cannot show a wrong neighbour choice (the first
FU-04 version gated on them; FU-04 review). The procedural head has no lid, lip or outline curves from
which an independent direction could be taken.

## 2. Summary

| Area | Result |
|---|---|
| Scorecard v1 vs baseline v0 (7 legacy scenarios, 30 seeds) | configuration RMS better in all 7 (-2.7 % to -12.4 %); NoW-7 RMS better in all 7; no failed seed. Two secondary metrics worse by > 2 % (section 5). |
| Fault matrix (16 rows of `FAULT_MATRIX`, 11 DESIGN rows) | 28 design gates pass, 10 are calibration-pending (section 3.1; 11 before FU-04: `jaw_open.tpr` closed); all 11 honesty gates and all 5 regression floors pass. No open release blocker. |
| Alarm budget | 4 warn findings on 150 clean photos (30 sets; all Q-SMALL on faces just under 250 px wide, section 3.3); budget 0.1 per photo. No false EXIF overrule (0/60 clean sets); Q-RETOUCH on 1 of 1110 unretouched views (stated rate 0.7 %, gate 5 %); no flip suggested on 390 unmirrored views; no neutral view tagged "expressive" (0/150; 6 "mild"). |
| Honesty (DESIGN 7.5) | All six bands met on the pipeline as shipped: vertex coverage 0.986, landmark NEES/dof 1.023 and 1-sigma coverage 0.722, false confidence 0/104, likeness-mode invariance 30/30, scale z RMS 1.07. Nothing pending. Sets with QA down-weights stay conservative (section 4.1). |
| Release blocker FU-02 | **Closed by option (i)** (section 4.1): the observe stage enables the deflation with chi2_red and gamma taken before the QA multipliers; golden result regenerated; DESIGN 4.13 / D-16 deviation recorded. |
| Release blocker `exif_crop.focal_label` | **Closed by FU-03** (section 3.1): the focal label is derived from the photos' own information; 0/150 views of the wrong-EXIF sets are labelled "measured" (150/150 before). |
| Release status | No failing honesty gate. Still open: 10 calibration-pending design targets (section 3.1; three of them unreachable at nominal detector noise, which needs a decision on the DESIGN 7.4 rows), three FU-04 owner decisions (tangent default off, narrowed extremal metadata, no set-level mirror pooling; DESIGN 4.4, 4.10, 7.4) and the default-suite time budget (section 6). |
| Policy (tools/ci_checks.py) | all six checks pass. |

## 3. Fault-injection matrix (DESIGN 7.4), release run, 30 seeds

The release run compares every rate on its **point estimate** and every continuous bound as written
(`failed_gates(..., strict=True)`). The binomial 95 % relaxation (a `>= p` gate fails only when the count
is below the 2.5 % quantile of Binomial(n, p)) belongs to the 5-seed per-push subset alone. Continuous
bounds are compared on the median over seeds unless the row says "hard". *honesty* gates must hold
whatever the detection rate; *floor* gates pin the measured level of a pending row so that it cannot get
worse unnoticed (they are not targets).

| Gate | Kind | Target | Measured | Status |
|---|---|---|---|---|
| `mirror.tpr` | design | suggest flip TPR >= 0.95 at >= 0.8 mm asymmetry | 1/30 = 0.033 at 0.79 mm (detectability g median 1.4, 0/30 views at g >= their g_min (>= 11.56); gap median 3.0 against tau = 13.83) | calibration-pending |
| `mirror.fpr` | design | false flips <= 0.02 | 0/390 = 0.000 | pass |
| `mirror.undetermined_when_symmetric` | design | >= 0.9 | 29/30 = 0.967 | pass |
| `mirror.shape_after_confirm` | design | shape <= 1.1 x clean | max ratio 1.000 (5 seeds) | pass |
| `mirror.no_false_keep` | honesty | 'keep' on a mirrored view <= 0.30 (WP-15; else 'undetermined') | 0/30 = 0.000 | pass |
| `mirror.no_false_flip` | honesty | no flip suggested on an unmirrored view | 0/390 = 0.000 (largest gap 8.8 against tau = 13.83) | pass |
| `orientation_unbaked.tpr` | design | Q-ORIENT TPR >= 0.99 | 30/30 = 1.000 | pass |
| `orientation_unbaked.no_false_alarm` | honesty | no Q-ORIENT on a baked photo | 0/150 = 0.000 | pass |
| `exif_crop.focal` | design | focal error < 0.05 when views span >= 60 deg | median 0.280 (span 120 deg; 0/30 seeds within; EXIF overruled in 0/30 sets, photos-only sigma(ln f) median 0.29, largest |t| 2.07) | calibration-pending |
| `exif_crop.shape` | design | shape <= 1.2 x clean | median ratio 1.060 | pass |
| `exif_crop.focal_floor` | floor | focal error not worse than recorded (0.35 crop / 0.20 missing) | median 0.280 | pass |
| `exif_missing.focal` | design | focal error < 0.05 when views span >= 60 deg | median 0.112 (span 120 deg; 6/30 seeds within) | calibration-pending |
| `exif_missing.shape` | design | shape <= 1.2 x clean | median ratio 0.982 | pass |
| `exif_missing.focal_floor` | floor | focal error not worse than recorded (0.35 crop / 0.20 missing) | median 0.112 | pass |
| `exif_crop.focal_label` | honesty | H5: no view labelled focal 'measured' while > 15 % off | 0/150 = 0.000 | pass |
| `exif_missing.focal_label` | honesty | H5: no view labelled focal 'measured' while > 15 % off | 0/150 = 0.000 | pass |
| `exif_crop.no_false_overrule` | honesty | a correct EXIF focal overruled on <= 0.01 of the clean sets (focal.exif_reject_alpha: the stated false-alarm rate of the robust EXIF prior) | 0/60 = 0.000 (largest |t| 1.47; photos-only sigma(ln f) median 0.39) | pass |
| `exif_unobservable.c_focal_prior` | design | C-FOCAL-PRIOR raised when the focal is unobservable | 30/30 = 1.000; labels {'partial': 90} | pass |
| `exif_unobservable.never_measured` | honesty | H5: an unobservable focal is never labelled 'measured' | 0/90 = 0.000 | pass |
| `exif_unobservable.focal_floor` | floor | focal error on the unobservable set not worse than recorded (0.12; WP-23: 0.10) and no prior overruled | median 0.097; overruled 0/30 | pass |
| `selfie_near.q_near` | design | Q-NEAR on every selfie at 0.35 m | 90/90 = 1.000 | pass |
| `selfie_near.tier` | design | tier <= B | 30/30 = 1.000 {'C': 30} | pass |
| `selfie_near.distance` | design | z within 0.15 | median 0.025; 30/30 sets within | pass |
| `jaw_open.tpr` | design | expressive tag TPR >= 0.9 | expressive 28/30 = 0.933; non-neutral 29/30; tagged by {'jaw_angle': 26, 'mobile_chi2': 4} | pass |
| `jaw_open.identity` | design | neutral identity moved < 0.3 mm (hard: every seed) | landmark RMS median 0.55, max 0.99 mm; surface RMS median 0.33, max 0.74 mm; rigid-class landmarks median 0.47, max 1.21 mm | calibration-pending |
| `jaw_open.identity_floor` | floor | median identity shift <= 1.0 mm (recorded level, not a target) | 0.55 mm | pass |
| `smile.tpr` | design | expressive tag TPR >= 0.9 | expressive 0/30 = 0.000; non-neutral 2/30; tagged by {} | calibration-pending |
| `smile.identity` | design | neutral identity moved < 0.3 mm (hard: every seed) | landmark RMS median 0.16, max 0.53 mm; surface RMS median 0.12, max 0.48 mm; rigid-class landmarks median 0.18, max 0.56 mm | calibration-pending |
| `smile.identity_floor` | floor | median identity shift <= 0.5 mm (recorded level, not a target) | 0.16 mm | pass |
| `jaw_open.no_false_expressive` | honesty | no neutral view tagged 'expressive' | 0/150 = 0.000 ('mild': 6) | pass |
| `beauty_warp.tpr` | design | Q-RETOUCH TPR >= 0.8 with >= 3 clean views | pipeline (post-BA test against the LOVO consensus) 0/30 = 0.000; the same engine test on the final solve 0/30 = 0.000 | calibration-pending |
| `beauty_warp.identity` | design | identity bias <= 0.5 mm | RMS median 0.25, max 0.38 mm | pass |
| `beauty_warp.no_false_alarm` | honesty | Q-RETOUCH on <= 0.05 of the unwarped views (pipeline: the 4 other views of each warped set and every view of the clean studio, clean rear-phone, selfie, beard, 150 px and (release run) glasses and hair sets; and the engine test on the final solve) | pipeline 1/1110 = 0.001 (of which occluder-tagged / 150 px views 0/600 = 0.000); engine test 0/120 = 0.000 | pass |
| `off_axis_stereographic.q_wide` | design | Q-WIDE on the ultra-wide photo | 30/30 = 1.000 | pass |
| `off_axis_stereographic.model` | design | model virtual_stereo chosen >= 0.8 | 22/30 = 0.733 {'k1': 1, 'pinhole': 7, 'virtual_stereo': 22} | calibration-pending (within the binomial bound) |
| `off_axis_stereographic.shape` | design | shape < 1.0 mm extra | median +0.62 mm, max +3.02 mm | pass |
| `off_axis_rectilinear.q_wide` | design | Q-WIDE on the ultra-wide photo | 30/30 = 1.000 | pass |
| `off_axis_rectilinear.model` | design | model pinhole chosen >= 0.8 | 30/30 = 1.000 {'pinhole': 30} | pass |
| `off_axis_rectilinear.shape` | design | shape < 1.0 mm extra | median -0.01 mm, max +0.25 mm | pass |
| `beard.jaw_prior_driven` | design | beard -> jaw prior-driven | 30/30 = 1.000 (clean: {'constrained': 30}) | pass |
| `beard.tag_actions` | design | chin points dropped, jaw outline flagged outer_bound | dropped 30/30, flag 30/30 | pass |
| `glasses.tag_actions` | design | no iris scale, eye sigma x2 | no_iris_scale 30/30, eye sigma x2 30/30 | pass |
| `hair.tag_actions` | design | no silhouette above trichion | 30/30 = 1.000 | pass |
| `hair.points_dropped` | design | ear / temple / trichion points dropped (tr, t_L, t_R, sa_L, sa_R, sba_L, sba_R) | 30/30 = 1.000 | pass |
| `hair.scalp_inside_hull` | design | scalp inside hull | not evaluated (no hair silhouette input) | calibration-pending |
| `small_face.q_small` | design | Q-SMALL on every 150 px face | 150/150 = 1.000 | pass |
| `small_face.coverage` | design | coverage holds: 1-sigma coverage in [0.6, 0.76] | 0.885 (NEES/dof 0.38; clean sets 0.728; DESIGN factor 0.919) | calibration-pending |
| `small_face.calibration_noise` | honesty | chi2_red taken against the noise before the QA multiplier (m^2 x the solve's own when every view carries the multiplier m); sigma_rep factor above the deflation floor | chi2_red ratio 4.000-4.000; factor median 0.76 | pass |
| `small_face.not_overconfident` | honesty | 1-sigma coverage >= 0.6 and NEES/dof <= 1.25 | 0.885, 0.38 | pass |
| `gross_outliers.caught` | design | >= 0.95 of the outliers rejected | 231/240 = 0.963 | pass |
| `gross_outliers.inliers_lost` | design | <= 0.02 of the inliers lost | 24/4773 = 0.005 (clean sets: 29/5013 = 0.006) | pass |
| `gross_outliers.shape` | design | shape <= 1.1 x clean | median ratio 1.019 | pass |
| `definition_bias.nees` | design | NEES/dof with sigma_rep in [0.8, 1.25] | 1.023 (DESIGN factor: 0.804) | pass |
| `alarm.budget` | design | <= 0.1 spurious warn/block findings per clean photo | 4 on 150 photos of 30 sets {'Q-SMALL': 4} | pass |

### 3.1 Calibration-pending gates (issue notes), what FU-04 changed and what FU-03 closed

Each entry: gate, measured (30 seeds), cause, proposed fix. The list is `CALIBRATION_PENDING` in
`tests/test_fault_matrix.py`; `OPEN_HONESTY_VIOLATIONS` (failing honesty gates, which can never be listed
as calibration-pending) is empty. The release run fails when an entry of either list starts to pass, so
they cannot go stale.

1. `mirror.tpr` — 1/30 flips suggested (29 "undetermined", 0 "keep"); target TPR >= 0.95. **Unreachable
   at nominal detector noise.** FU-04 calibrated the test (below): the flip is suggested when the gap
   C0 - C1 exceeds tau = 13.83 (false-flip rate <= 1e-4 per view whatever the asymmetry) and the relative
   rule holds; a non-detection is "keep" only where the *complete* rule had 95 % power, i.e. at a
   detectability g >= g_min, computed per view (11.6 for 44 evenly loaded landmarks; the first FU-04
   version used the gap-only value 8.16, at which the engine finds 77 % of the flips: review finding,
   below). Through the pipeline the mirrored view reaches g 1.4 (median; gap 3.0) and no view of 30
   reaches its g_min. Raising the subject's asymmetry does not help: at 2.5 mm RMS (diagnostic, section
   3.2) g is 1.7 and 4/30 are flagged, because g is computed from the asymmetric part of the *4-view
   consensus*, which the symmetric shape prior shrinks. The condition under which the target holds is
   known from the engine test called with the true consensus (`tests/test_nuisances.py`): at half the
   nominal noise 15 of 40 mirrored views reach their g_min and 14 of them are flagged (27 of the 40 are
   flagged in all); at 0.2 x noise 40 reach it and 39 are flagged. Honest today: no flip on 390
   unmirrored views (largest gap 8.8 against 13.83), no "keep" on a mirrored view, and an unconfirmed
   mirrored view does not damage the shape (ratio to clean 0.99: the robust schedule down-weights it).
   Proposed: decide whether the row keeps "0.8 mm at nominal noise" (then it needs a detector with about
   half the DESIGN 4.4 sigmas, or the asymmetry estimated without the symmetry prior for this test), and
   measure on real detections.
2. `exif_crop.focal` — a +/-30 % wrong EXIF focal is still kept on this row: median focal error 0.280,
   0/30 sets within 5 %, although the views span 120 deg. Shape survives (1.06 x clean, bound 1.2). The
   robust EXIF prior of FU-03 (DESIGN 4.13: |t| > 2.576, photos-only sigma(ln f) <= 0.25, >= 3 views)
   fires on 0 of 30 sets: the photos-only sigma(ln f) is 0.29 (0.39 on the clean sets), largest |t| 2.07.
   At 0.6-1.5 m the photos alone do not constrain the focal under the declared noise (with the opt-in
   tangents on scheme-aligned scenes the sigma was 0.28 and 1 set was overruled). Where the photos carry the information the prior works
   (section 3.2). The rejected alternative (distance priors as evidence) is recorded in the FU-03 notes
   below. Fix for the target: none in the noise model; it needs closer or wider-baseline photos, or a
   calibrated focal.
3. `exif_missing.focal` — median focal error 0.112 (6/30 within 5 %) on the same
   120 deg sets without EXIF; labels read "partial", never "measured" (honest), and every set carries
   `C-FOCAL-PRIOR` (warn). Shape 0.98 x clean. Fix: as item 2.
4. `smile.tpr` — 0/30 views tagged "expressive" (2 "mild"). **Unreachable at nominal detector noise**: a
   2-4 mm mouth-corner motion adds 5-20 to a mobile-class chi2 whose null 99.9 % quantile is 42 (9
   landmarks, 18 dof), and the consensus absorbs part of it; the same at 0.2 x simulated noise (0/30),
   since the engine's declared noise does not shrink with the simulator's. Proposed: a dedicated mouth-width
   statistic against the consensus (4-8 mm width change against 1.8 mm declared: z 2.3-4.5, i.e. roughly
   half power at a 1e-3 false-alarm rate), or blendshape scores from the detector (DESIGN 4.9's primary
   route; the fallback needs inner-lip points, none in the anatomical44 scheme).
5. `jaw_open.identity`, `smile.identity` — the 44-landmark RMS shift against the clean twin is 0.55 mm
   (jaw; max 0.99; 1.03 / 2.57 before FU-04) and 0.16 mm (smile; max 0.53) against the hard 0.3 mm bound.
   The jaw result equals a perfect tagger's (diagnostic, section 3.2): the bound is not met because
   (a) tagging a view "expressive" on a *neutral* face moves the 44-landmark solution by 0.35 mm (median;
   0.76 max) at nominal noise - the tag drops six lip points and down-weights nine more in one of five
   views, so the comparison against the untagged clean twin has a noise floor above the bound; and
   (b) with the same tag in both solves the jaw opening itself still moves it 0.36 mm (the hinge angle is
   pulled towards 1.5 deg by its 3 deg prior and the chin points then pull the view's pose). DESIGN 4.9
   states the hard gate for the neutral region: the rigid-class landmarks move 0.47 mm (jaw) and 0.18 mm
   (smile) in the same comparison (reported next to the gate; the WP-15 unit test of the gate, with the same
   tags in both solves and noise-free or common-noise data, passes). The task-4 robust down-weighting of
   the mobile class (views with an elevated but untagged mobile chi2) was implemented and measured (in the first FU-04 run; not re-measured after the review): both
   medians were unchanged to three decimals with and without it and it moved clean sets by up to 0.26 mm, so
   it ships **off** (`pipeline.soft_mobile_downweight`). Proposed: gate the rigid-class shift against a
   same-tag twin (what DESIGN 4.9 words), widen the jaw prior of a view tagged by its jaw angle, and decide
   the 44-landmark bound on real data.
6. `beauty_warp.tpr` — 0/30 warped views flagged by the pipeline and by the engine test on the final solve.
   **Unreachable at nominal detector noise**: the warp (eyes +6 %, jaw -4 %) moves the eye-width ratio by
   0.7, the eye-corner pattern t by 0.8 and the bigonial ratio by 2.2 declared sigmas (medians) against the
   threshold 3. The eye corners are sharp junctions (isotropic 1.25 mm), which image tangents would not
   narrow either. The
   threshold was kept: |z| > 3 on two ratios and t > 3 is a false-alarm rate of 0.7 % per unretouched view
   under the declared noise (five tails of 0.135 %); measured 1 of 1110 unretouched views (0 of 600 with
   occluder or Q-SMALL multipliers). A 3 x stronger warp (eyes
   +18 %, jaw -12 %) is flagged on 6/30 (with 1 false alarm on the 120 other views of those sets). The
   identity bias is 0.25 mm RMS (max 0.38; bound 0.5 on the median: pass). Proposed: decide the row at nominal noise as for item 1.
7. `off_axis_stereographic.model` — `virtual_stereo` selected for 22/30 ultra-wide views (0.73; pinhole 7,
   k1 1); target 0.8. Not rejected at the binomial 95 % bound, but the point estimate is below the
   target, so it is listed (the selection code is unchanged). The selected model is
   recorded and flagged `C-MODEL-NOT-APPLIED` (23/30) but still not applied to the solve; shape cost
   median +0.62 mm (bound 1 mm: pass; worst seed +3.0 mm). The rectilinear row is correct on 30/30.
8. `hair.scalp_inside_hull` — **not evaluated**: the landmark pipeline has no hair silhouette; it needs
   ContourObs (stage D inputs). Reported as not evaluated, never as passed.
9. `small_face.coverage` — on 150 px faces the x2 down-weight widens the posterior and sigma_rep is
   conservative: 1-sigma coverage 0.885 (band 0.60-0.76), NEES/dof 0.38 (0.919 / 0.30 with the DESIGN
   factor). chi2_red against the noise before the multiplier is 4 x the solve's own on every set (every
   view carries the x2 multiplier) and the factor is 0.76, so the deflation does not cancel the caution
   of the down-weight (asserted by the honesty gate `small_face.calibration_noise`); what remains is the
   x2 multiplier itself, a WP-20 implementation choice without a DESIGN value. Not over-confident in
   position. Fix: calibrate `pipeline.downweight_sigma_mult` against detector noise at small face sizes,
   and re-measure the scale term on small faces.

**Changed by FU-04** (engine and pipeline; registered defaults with badge new and their source; as amended
by the FU-04 review):

- **Image tangents from the detections: implemented, opt-in, off by default** (`solve/noise.py`,
  `solve/reconstruct.py`, landmarks stage; `pipeline.image_tangents`). The anatomical44 scheme carries
  neighbour metadata (key `tangents`, provisional): lid points between the canthi, lip points between the
  cheilions, nasion on the dorsum (glabella-pronasale), the three extremal points whose slide direction
  the research note documents (menton / gnathion along the chin curve, zygion along orbitale-tragion,
  gonion along the mandibular border) and, added by the review, the three points the note types
  "extremal (profile)" (glabella, sublabiale, pogonion: along the midline profile between their midline
  neighbours): 16 landmarks. For pronasale, the alar, orbital, ear and cranial points the note documents
  no direction and no outline neighbours: none was invented, they keep the FU-01 isotropic rule (the WBS
  item "every extremal landmark" is narrowed; owner decision open). `mediapipe_478` has no such metadata
  and is unchanged. Per view the tangent is the unit chord between the *detected* neighbours with a
  separate direction confidence rho = exp(-2 (sigma_a^2 + sigma_b^2) / chord^2) (third column of the
  tangent array; a plain (N, 2) tangent keeps its old meaning "exact direction, any length": the first
  FU-04 version encoded rho in the vector length, which changed what non-normalised tangents meant). The
  covariance is the exact second moment of the error ellipse under that direction error (never tighter
  across the curve than the direction is known); for the kinds whose tangent sigma only encodes "free"
  (contour 1000 mm, brow 40 mm) the leak into the normal uses `noise.free_tangent_leak_mm` = 7.5 mm
  (before: a contour point with rho = 0.95 was declared 158 mm across its curve). Below rho = 0.5
  (`noise.tangent_min_rho`), with a hidden neighbour or on a pinned point the tangent is unknown. No
  declared sigma was changed.
- **Mirror test** (`solve/mirror.py`, solve stage). Noise = the noise the view is declared with (weights,
  QA multipliers) plus the projected covariance of the leave-one-view-out consensus (the evidence pooled
  over the other views). Null: gap ~ N(-4 g, 16 g), so sup_g P(gap > tau) = Phi(-sqrt(tau)):
  `mirror.flip_alpha` = 1e-4 gives tau = 13.83 (before: 2 sqrt(2 n_v) = 15.5 at 30 landmarks, without a
  stated rate). A flip is suggested when gap > tau and delta > 0.10 / 0.20 (unchanged). **Review fix:**
  "keep" needs the power of that complete rule, on costs capped at 3.035 sigma per landmark, to reach
  `mirror.keep_power` = 0.95: g_min is computed per view from the per-landmark moments of the capped
  costs (`mirror.rule_power`), 11.6 for 44 evenly loaded landmarks at delta 0.20 (WP-15 note "g ~12"),
  larger for a concentrated asymmetry or more landmarks (14.4 at 60, 17.9 at 80), 8.7 on a front
  camera; and a significant gap that the relative rule does not confirm is "undetermined"
  (`M-GAP-SIGNIFICANT`), never "keep". The first FU-04 version derived g_min = 8.16 from gap > tau
  alone; there the engine suggested the flip for 77 % of mirrored views and answered "keep" for 23 %.
  Monte Carlo through `mirror_test` (44 landmarks, rear camera, true noise, 400 mirrored views each):

  | g | predicted power | flip suggested | "undetermined" (significant gap / other) | "keep" |
  |---|---|---|---|---|
  | 8.3 (below g_min 12.8 of this pattern) | 0.766 | 312 = 0.780 | 57 / 31 | 0 |
  | 12.0 (below g_min) | 0.934 | 373 = 0.933 | 24 / 3 | 0 |
  | 14.2 (above g_min) | 0.970 | 389 = 0.973 | 10 / 0 | 1 |
  | 16.0 | 0.984 | 396 = 0.990 | 4 / 0 | 0 |

  No flip on 4 x 400 unmirrored views. The project status reports the summed detectability; there is
  no set-level decision (a flip is a property of one photo; deviation from the WBS wording "pool mirror
  evidence across views", owner decision open).
- **Expression re-tag** (`solve/expression.py`, solve stage). The DESIGN thresholds (reduced chi2 > 4 / > 9
  on 12 dof) are the 3e-6 and 1e-17 quantiles of the statistic's null, and a jaw opening does not reach the
  mobile class at all: the per-view hinge absorbs 3-6 deg of a 5-15 deg opening against its neutral prior
  and the rest goes into the pose. Now: (a) the capped chi2 of the mobile and jaw-dependent landmarks
  (full 2 x 2 Mahalanobis residuals against the view's neutral declared noise; a rejected landmark counts
  as 3.035 sigma, so one gross outlier cannot tag a view) against chi2 quantiles at
  `expression.retag_mild_alpha` 0.01 / `retag_expressive_alpha` 0.001; (b) the fitted jaw angle against
  the neutral population N(1.5 deg, 1 deg^2), with the exact null SD of a posterior mean, at
  `retag_mild_jaw_alpha` 0.05 / `retag_expressive_jaw_alpha` 0.005 (a 5 deg opening is 3.5 sigma of that
  population, so the row cannot be met at a smaller rate). Stated worst case: 0.6 % of neutral views
  tagged "expressive", 6 % "mild"; measured on the simulator, whose neutral jaw does not vary: 0/150 and
  6/150.
- **Q-RETOUCH**: unchanged threshold, now with its stated rate (item 6).

**The four combinations of noise axes and tangents** (same harness, 30 seeds, clean studio ring and the
"definition bias 1 mm" row; scheme metadata with 16 landmarks):

| Scene noise axes | Engine tangents | chi2_red | gamma | sigma_rep factor | config RMS (mm) | inliers rejected | NEES/dof, gate row | 1-sigma coverage, gate row | scale z RMS |
|---|---|---|---|---|---|---|---|---|---|
| random (WP-01 simulator) | off (**shipped; every gate**) | 0.720 | 0.854 | 0.755 | 2.405 | 29/5013 = 0.6 % | 1.023 | 0.722 | 1.07 |
| random (WP-01 simulator) | on (opt-in, misaligned) | 0.793 | 0.918 | 0.867 | 2.535 | **226/5013 = 4.5 %** | 1.045 | 0.712 | 1.12 |
| scheme-aligned (diagnostic) | off | 0.698 | 0.839 | 0.732 | 2.408 | 34/5013 = 0.7 % | 1.034 | 0.720 | 1.05 |
| scheme-aligned (diagnostic) | on (opt-in, best case) | 0.747 | 0.866 | 0.783 | 2.413 | 19/5013 = 0.4 % | 1.047 | 0.711 | 1.06 |

Reading. (i) **What a wrong tangent costs** (second row): if a detector's anisotropic noise is not
aligned with the scheme's directions, the tangent-derived noise rejects 4.5 % of good observations
(above the 2 % bound of the DESIGN 7.4 gross-outlier row) and the
shape is 5 % worse, while the reported uncertainty stays inside its bands (the chi2 / gamma factor absorbs
it). (ii) **What a right tangent gains** (rows 3-4): fewer good observations rejected (0.4 % against
0.7 %), chi2_red +0.05, the same shape error, bands held; the FU-02 factor is still needed (0.78).
chi2_red does not approach 1 and should not be expected to: the extremal points without a documented
direction are declared isotropic at 3.0 mm where the simulator draws 2.0 / 3.0, the hair point is
declared 8 mm where the simulator draws 2 mm, and the engine declares a detector floor the simulator does
not draw. None of these was shrunk to match the simulator. (iii) Rows 3-4 are **not evidence that the
metadata is right**: their noise axes are built from the same neighbour pairs. Whether a real detector
behaves like row 2 or row 4 is what the M7 per-index calibration has to measure; until then the switch
is off, the gates are those of row 1, and the choice is recorded as an open owner decision (DESIGN 4.4,
7.4). The per-push test `test_fu04_bands_hold_with_and_without_tangents` keeps the opt-in honest
(bands, orientation of the tangents, no extra rejections on aligned scenes).

Pending gates before and after (30 seeds; "before" = FU-03 run; both on the WP-01 simulator):

| Gate | Before FU-04 | After FU-04 | Status |
|---|---|---|---|
| `mirror.tpr` | 0/30 | 1/30 (g median 1.4, g_min >= 11.6) | pending: unreachable at nominal noise |
| `exif_crop.focal` | 0.280 (0/30 overruled) | 0.280 (0/30 overruled) | pending |
| `exif_missing.focal` | 0.112 | 0.112 | pending |
| `jaw_open.tpr` | 0/30 | **28/30 = 0.933** | **closed** |
| `jaw_open.identity` | 1.03 mm median, 2.57 max | 0.55 mm median, 0.99 max (= perfect tagger) | pending |
| `smile.tpr` | 0/30 | 0/30 | pending: unreachable at nominal noise |
| `smile.identity` | 0.16 mm median, 0.53 max | 0.16 mm median, 0.53 max | pending |
| `beauty_warp.tpr` | 0/30 | 0/30 | pending: unreachable at nominal noise |
| `off_axis_stereographic.model` | 22/30 | 22/30 | pending |
| `hair.scalp_inside_hull` | not evaluated | not evaluated | pending |
| `small_face.coverage` | 0.885 | 0.885 | pending |

**Golden result** (`tests/golden/pipeline_small/expected_result.json`; scene of `tests/test_pipeline.py`:
the WP-01 simulator as is, 5 % outliers). The first FU-04 version regenerated it with the tangents on
(a misaligned case: calibration chi2_red 1.66 -> 2.10, a new flag `F-VIEW-OUTLIERS`). With the default
off it was regenerated again and its summary is back at the FU-03 values: chi2_red 1.66, gamma 1.08,
flags `C-FOCAL-PRIOR`, `Q-NEAR`, `Q-SMALL`, eyes sigma_rep 1.79 mm, landmark RMS of the fit stages 3.32 /
1.09 / 0.84 mm (A / B / C), scale sigma 5.6 %.

**FU-03 notes kept for the record.** The robust EXIF prior tests each EXIF focal against the focal the
photos give on their own (focal *and* distance priors removed from the information). With the distance
priors left in as evidence the test overruled 17/30 of the wrong-EXIF sets (median focal error 0.17), but
also a *correct* EXIF on 30/30 small-face sets (cameras at 5-10 m against a 2 m distance prior), leaving
the focal 64 % wrong: a population distance guess must not overrule a recorded EXIF value. The post-BA
Q-RETOUCH test uses the noise the view is declared with in pass 2, not the base noise.

**Closed by FU-03** (each removed from the pending lists because it passes on the 30-seed point estimate;
numbers of the FU-03 run):

- **`exif_crop.focal_label` — the WP-23 release blocker (honesty, H5 / H12).** Before: 150/150 views of
  the wrong-EXIF sets were labelled focal "measured" while 28 % off, because sigma_post(ln f) < 0.10 was
  inherited from the EXIF prior (sigma_log 0.04). Now: 0/150. `solve.observability.camera_status` labels
  "measured" only when sigma_post < 0.10, the CAM-7 test holds (the solved value is the photos', not the
  prior's) and the photos alone reach 0.10 (`focal_prior_evidence`: sigma of ln f with the focal and
  distance prior rows removed from the stored information); a focal whose EXIF prior was overruled reads
  "partial". Consequence, stated plainly: a focal that is the EXIF value now reads "prior used" on every
  clean set too (150/150 clean views; before: "measured"), with an *info* `C-FOCAL-PRIOR`; tier S still
  accepts "EXIF-confirmed" separately. `exif_missing.focal_label` (0/150) and
  `exif_unobservable.never_measured` (0/90) keep passing.
- **`exif_unobservable.c_focal_prior`** — 30/30 (0/30 before). The observe stage raises `C-FOCAL-PRIOR`
  for every view whose focal label is not "measured" (severity info for an EXIF or calibrated prior that the photos do not contradict,
  warn for the ladder's guess; flag `C-FOCAL-PRIOR`; carried into result.json). The unobservable row is
  not worse: focal error 0.097 (0.10 before), nothing overruled (floor gate
  `exif_unobservable.focal_floor`).
- **`hair.points_dropped`** — 30/30 (0/30 before). The "hair" tag already dropped the ear points (t, sa,
  sba: registry region "ears"); the hairline-defined point (registry kind "hair": trichion) stayed in.
  The landmarks stage now resolves a class "hairline" from the kind metadata and drops it with the tag
  (`stages._occluder_drop_classes`, keyed on the tag's own `no_silhouette_above` flag).
- **`small_face.q_small`** — 150/150 (149/150 before; the strict xfail on seed 2313 is now a plain test).
  Q-SMALL is decided on the pose-independent face *width* (`stages.face_width_px`: scaled-orthographic
  scale of the observed anatomical landmarks against the prior mean x the prior's frontal landmark-box
  width, 155.5 mm), not on max(width, height) of the landmark box. **Side effects, all following from
  "face < 250 px wide" read literally:** (a) on the 150 px row the 60 profile views read 106-111 px
  (their 150 px box is the nose-to-occiput extent), i.e. below the 120 px reject size; the test project
  forces every photo in, and a forced-in face below the reject size is now down-weighted like one below
  the warn size (before it carried no multiplier at all); (b) 4 of 150 clean studio photos (faces
  238-249 px wide at 2.8-3.0 m) now carry Q-SMALL warn (0 before, when the 280-380 px box height was
  compared); (c) on the clean rear-phone twin 99 of 150 photos carry Q-SMALL (50 before), which makes its
  sigma_rep more conservative (section 4.1); (d) the golden scene of `tests/test_pipeline.py` (faces 68-148
  px wide in a 600 x 800 frame) has four faces below 120 px instead of one.

**Golden result regenerated by FU-03** (`tests/golden/pipeline_small/expected_result.json`; regenerated
again by FU-04, above), because of (d) and the label change: focal statuses "measured" x5 -> "prior_used" x5; flags gain `C-FOCAL-PRIOR`; the 68 px
photo p03 is now down-weighted x2 like the other four, so calibration chi2_red 1.43 -> 1.66, gamma
1.02 -> 1.08, region sigma_rep +16 % to +31 % (e.g. eyes 1.46 -> 1.79 mm), nose and chin projection
"constrained" -> "prior-driven", solved focal -0.3 %, landmark RMS of the fit stages 2.70 / 0.78 / 0.61 ->
3.32 / 1.09 / 0.84 mm (A / B / C), scale sigma 5.4 -> 5.6 %. The solve of the gate sets is unaffected by
the label change.

### 3.2 Diagnostic runs (not gated)

Run once for this report (`evaluate(SLOW_SEEDS, diagnostics=True)` in `tests/test_fault_matrix.py`):

| Condition | mirror flips | jaw tagged "expressive" | smile tagged "expressive" | retouch (pipeline / engine test) |
|---|---|---|---|---|
| studio ring, nominal noise (gated run) | 1/30 | 28/30 | 0/30 (2 "mild") | 0/30 / 0/30 |
| studio ring, 0.2 x simulated noise (WP-15 test condition) | 0/30 | 29/30 | 0/30 (1 "mild") | - / 0/30 |
| rear phone, nominal noise | 0/30 (g median 0.2) | - | - | - |
| studio ring, 2.5 mm asymmetry (FU-04) | 4/30 (g median 1.7; 0 views at their g_min; 0 false flips, 0 "keep" on 120 other views) | - | - | - |
| studio ring, warp 3 x (eyes +18 %, jaw -12 %; FU-04) | - | - | - | 6/30 / - (1 false alarm on 120 other views) |
| before FU-04, gated run | 0/30 | 0/30 | 0/30 | 0/30 / 0/30 |

The simulated noise scale does not change the engine's declared noise, so a quieter simulated detector
does not raise the detectability the pipeline computes (mirror, smile and retouch at 0.2 x noise are as at
nominal noise); the jaw is found at both. The WP-15 unit tests detect a mirrored view at reduced noise
because they call the engine tests with a covariance that matches the simulated noise and with the true
consensus: at 0.5 x noise 14 of the 15 mirrored views (of 40) that reach their g_min are flagged (27 of
the 40 in all), at 0.2 x noise 39 of 40. The DESIGN 7.4 mirror, smile and retouch targets therefore hold under no condition reachable
through the pipeline at the DESIGN 4.4 noise.

**Identity under a perfect tagger (FU-04).** RMS shift in mm between two solves of the same seed, after
similarity alignment, 30 seeds (median / max); "tagged" = the expressive view carries the user tag
"expressive"; "neutral twin" = the clean scene with the same view tagged:

| Comparison | jaw 5-15 deg: all 44 | jaw: rigid class | smile 2-4 mm: all 44 | smile: rigid class |
|---|---|---|---|---|
| pipeline (automatic re-tag) vs clean (**the gate**) | 0.55 / 0.99 | 0.47 / 1.21 | 0.16 / 0.53 | 0.18 / 0.56 |
| perfect tagger vs clean | 0.55 / 0.99 | 0.47 / 1.21 | 0.36 / 0.76 | 0.21 / 0.87 |
| perfect tagger vs neutral twin with the same tag (what the expression itself moves) | 0.36 / 0.80 | 0.35 / 0.94 | 0.03 / 0.50 | 0.04 / 0.16 |
| neutral twin with the tag vs clean (what the tag's down-weighting moves) | 0.35 / 0.76 | 0.23 / 0.88 | 0.35 / 0.76 | 0.23 / 0.88 |

Reading: for the jaw the automatic re-tag is as good as a perfect tagger; the tag itself costs 0.35 mm
against the untagged twin at nominal noise, which is why tagging a smile would make the smile gate worse
(0.16 -> 0.36), and why the 0.3 mm bound on all 44 landmarks against the clean twin is not reachable by
tagging. With the same tag in both solves a tagged smile leaves 0.03 mm (the WP-15 reading of the hard
gate holds); a tagged jaw opening still leaves 0.36 mm.

**Robust EXIF prior where the photos carry the information** (`task_exif_near`: five rear-phone views
over 120 deg at 0.30-0.35 m, the EXIF focal of every photo multiplied by a factor; 30 seeds; the engine's
nominal noise model):

| EXIF factor | photos-only sigma(ln f), median | abs(t) median / max | contradicted | overruled | focal error, median (all / overruled / kept) | labels | "measured" while > 15 % off |
|---|---|---|---|---|---|---|---|
| 1.0 (correct) | 0.084 | 0.33 / 1.68 | 0/30 | 0/30 | 0.028 / - / 0.028 | prior_used 150 | 0 |
| 0.7 (30 % short) | 0.066 | 4.31 / 5.93 | 30/30 | 30/30 | 0.148 / 0.148 / - | partial 150 | 0 |
| 1.3 (30 % long) | 0.104 | 2.56 / 3.69 | 15/30 | 6/30 | 0.285 / 0.108 / 0.288 | prior_used 120, partial 30 | 0 |

**Disclosure: the table above is the optimistic case.** The rig of `task_exif_near` has a true focal of
26 mm-equivalent, which is exactly the centre of the ladder's "phone, no focal data" prior
(`focal.phone_f35_mm`), i.e. of the fallback prior the solve is re-run under after a contradiction. The
focal errors after an overrule and the adoption counts were therefore measured with the alternative prior
placed on the truth. The same diagnostic with a true focal of 35 mm-equivalent (`NEAR_OFF_PRIOR_F35`; the
longest that keeps the whole head in the 1500 x 2000 frame at 0.30 m), where the fallback prior is 26 %
short of the truth (0.30 in ln f, 1.2 of its sigma 0.25), 30 seeds:

| EXIF factor (true 35 mm) | photos-only sigma(ln f), median | abs(t) median / max | contradicted | overruled | focal error, median (all / overruled / kept) | labels | "measured" while > 15 % off |
|---|---|---|---|---|---|---|---|
| 1.0 (correct) | 0.087 | 0.35 / 1.47 | 0/30 | 0/30 | 0.035 / - / 0.035 | prior_used 150 | 0 |
| 0.7 (30 % short) | 0.068 | 4.37 / 5.37 | 30/30 | 30/30 | 0.153 / 0.153 / - | partial 150 | 0 |
| 1.3 (30 % long) | 0.109 | 2.22 / 3.46 | 9/30 | 9/30 | 0.294 / 0.086 / 0.298 | prior_used 105, partial 45 | 0 |

(Both tables: run after the FU-04 review, shipped defaults.) On these 30 seeds the off-centre fallback does not change the picture for a
short EXIF (30/30 overruled, error 0.15 as at 26 mm) and no correct EXIF is contradicted; a long
EXIF is detected less often (9/30 against 15/30) and every detection is adopted. A tele lens (>= 50 mm) cannot be simulated at this range in
this frame (the head leaves the image), and at the ranges where it fits the photos do not constrain the
focal (section 3.1 item 2); an ultra-wide lens goes through the Q-WIDE path and was not measured. Neither
case is claimed.

Reading. (i) No false alarm on a correct EXIF (largest |t| 1.68 against 2.576; on the 60 clean sets of
the matrix 1.47). (ii) A 30 % short EXIF is always overruled, and the focal error halves (0.30 -> 0.15);
it does not reach 5 %: the solve under the ladder's phone prior is itself 15 % off at this range.
(iii) A 30 % long EXIF is detected in half of the sets and overruled in 6: in 9 sets the re-solve under
the phone prior stays within 15 % of the EXIF value (the wrong solution is a local valley of the
focal/distance trade-off) and the EXIF prior is kept; those sets read "prior used", never "measured",
and their `C-FOCAL-PRIOR` is raised at *warn* with `detail.exif_contradicted` (9/9 sets; FU-03 review:
before, the only finding on these sets was an info line that treated the EXIF as trusted, while the focal
was 29 % off).
(iv) The first version of the label rule (photos-only sigma < 0.10 alone) labelled 20 views of the kept
long-EXIF sets and 25 views of the overruled short-EXIF sets "measured" while more than 15 % off; the
shipped rule (plus CAM-7, and "partial" after an overrule) labels none. This diagnostic is what showed
that both tests are needed.

### 3.3 Alarm budget

30 clean studio-ring sets, 150 photos: 4 warn findings (budget <= 0.1 per photo: 15), all Q-SMALL on
views at 2.8-3.0 m whose face is just under 250 px wide: true positives of "face < 250 px wide" (as in the
FU-03 run). No flip suggestion (largest
gap on an unmirrored view 8.8 against the threshold 13.83), no "expressive" tag (6 of 150 neutral views
read "mild", which is not an alarm: it widens that view's lip sigmas x3), no `C-FOCAL-EXIF`, no Q-RETOUCH
on these sets. Every clean photo carries an *info* `C-FOCAL-PRIOR` (the focal is the EXIF's), which is not
an alarm. For comparison, the WP-01 rear-phone protocol (0.6-1.5 m, same frame) raises Q-NEAR on 60 and
Q-SMALL on 99 of 150 photos: true positives by the engine's thresholds (distance < 1 m, face < 250 px wide
in the working frame), and they are why that protocol is not the clean reference. Note: Q-SMALL is
measured in the working-copy frame, so a down-scaled working copy raises it on a photo that was large
enough when detected.

## 4. Honesty metrics (DESIGN 7.5), release run, 30 seeds

Pipeline as shipped. Every number is the one the pipeline reports: the landmark covariance is rebuilt
from the observe stage's own Sigma1 (gauge-projected, prior weight 1), bias form, calibration chi2_red /
gamma and factor, and its diagonal is asserted equal to the reported `sigma_rep_mm` squared on every run
(`tests/test_fault_matrix.py::honesty_of`); per-vertex sigma_n comes from the uncertainty stage; the scale
z uses the reported scale and its sigma. Landmark numbers are gauge-projected (DESIGN 7.3); the
definition-bias gate uses the "Definition bias 1 mm" row (a 1 mm isotropic bias shared by all views
instead of the simulator's per-kind bias). Point estimates, bands as written.

| Gate | Kind | Target | Measured | Status |
|---|---|---|---|---|
| `vertex.coverage` | design | 0.9-0.99 of measured-region vertices within 1.96 sigma_n | 0.9858 over 46562 vertices (z RMS 0.60; median sigma_n 3.7 mm vs median abs error 1.0 mm) | pass |
| `vertex.not_overconfident` | honesty | coverage >= 0.9 | 0.9858 | pass |
| `vertex.pre_wp23` | info | sigma_n as before WP-23 (`cov`, DESIGN factor, sigma_res x 1), same vertices | 1.0000 (z RMS 0.27; median sigma_n 7.1 mm) | reported |
| `landmark.nees` | design | NEES/dof in [0.8, 1.25] with 1 mm definition bias | 1.023 (clean sets 0.787; sigma_rep factor median 0.76) | pass |
| `landmark.coverage_1s` | design | aligned 1-sigma coverage in [0.6, 0.76] with 1 mm definition bias | 0.722 (clean sets 0.728) | pass |
| `landmark.not_overconfident` | honesty | coverage >= 0.6 and NEES/dof <= 1.25 (bias row and clean sets) | 0.722 / 1.023; 0.728 / 0.787 | pass |
| `landmark.design_factor` | info | the same covariance under the DESIGN 4.13 factor max(1, gamma^2, chi2_red) (not shipped) | NEES/dof 0.804, coverage 0.772 | reported |
| `false_confidence` | design | <= 0.05 of measured regions above 2 x their target | 0/104 = 0.000 {'cheeks': 2, 'chin': 2, 'cranium': 26, 'eyes': 29, 'nose': 16, 'nose_projection': 29} (worst error/target 1.71) | pass |
| `likeness.labels_invariant` | design | labels, k, sigma_rep, coverage, focal status and tier identical in likeness mode (H2), and not vacuously | 30/30 identical to the pipeline's report; widened solve moved landmarks by up to 2.5 mm (median); assessed on its own it would report different sigma_rep / k in 30/30 sets (sigma_rep by up to 70 %, median; labels in 21); refused without the standard solve 30/30 | pass |
| `scale.z_rms` | design | scale z RMS in [0.8, 1.25] | 1.070 over 30 sets (mean z -0.67; median sigma_zeta 0.051) | pass |

Measured vertices: kit regions whose ledger regions are all "measured" (eyes in 29 sets, nose in 16,
scalp via the cranium region in 26, cheeks in 2). False confidence is counted over the
measured ledger regions: region error = RMS of the aligned error over the region's coordinates, worst
error/target 1.71 (limit 2). 104 regions are labelled "measured" (105 in the FU-03 run; with the opt-in
tangents on scheme-aligned scenes it was 138: the lips, declared 1.5 mm across the lip line instead of
5.4 mm isotropic, became "measured" in 25 sets). Likeness mode is not exposed
by the pipeline; the gate drives `observability.likeness_mode_prior` with the pipeline's solve objects on
all 30 sets and compares against the pipeline's own report. It is not vacuous: assessed on its own, the
widened solve would report a different sigma_rep or k in 30/30 sets (sigma_rep up to 70 % larger at the
median, different labels in 21), and it is refused without the standard solve in 30/30. The focal labels
compared here are the FU-03 ones (photos-only sigma, the priors the solve used).

### 4.1 Landmark sigma_rep: FU-02 closed by option (i)

**What changed (in `face3d/pipeline/stages.py`, stage `observe`; DESIGN 4.13 / D-16 deviation recorded
there).** sigma_rep uses the factor max(gamma^2, min(1, chi2_red/kappa), chi2_red, 0.5)
(`assess(..., deflate=True)`, registered default `pipeline.sigma_rep_deflate`), and chi2_red and gamma are
taken against the noise **before** the QA sigma multipliers (Q-SMALL / Q-BLUR / Q-NEAR x2): gamma from
the held-out residuals whitened with the un-multiplied covariances, chi2_red rescaled by the share of
each view in the inlier chi^2 times its multiplier squared (`_calibration_noise`). Without a multiplier
both are the solve's own values. The result now carries `chi2_red` and `gamma` (calibration values),
`chi2_red_solve` and `inflation`. `tests/golden/pipeline_small/expected_result.json` was regenerated:
that scene carries Q-NEAR and Q-SMALL on its views, its calibration chi2_red reads 1.43 (solve 0.33) and
gamma 1.02 (0.57), so its region sigma_rep **grew** by 17-19 % (factor 1.43 against 1 before); the solve
itself is unchanged. (WP-23 numbers; FU-03 regenerated the file again, section 3.1.)

Mean NEES/dof and pooled aligned 1-sigma coverage, 30 seeds; "shipped" is the pipeline, "DESIGN" the
same covariance under max(1, gamma^2, chi2_red) (evidence only):

| Sets | chi2_red solve | chi2_red calibration | gamma | factor | NEES/dof (shipped) | coverage (shipped) | NEES/dof (DESIGN) | coverage (DESIGN) |
|---|---|---|---|---|---|---|---|---|
| Definition bias 1 mm, studio ring (**the gate**) | 0.71 | 0.72 | 0.86 | 0.76 | **1.023** | **0.722** | 0.804 | 0.772 |
| Clean, studio ring | 0.71 | 0.72 | 0.85 | 0.76 | 0.787 | 0.728 | 0.626 | 0.778 |
| Clean, rear phone (Q-NEAR / Q-SMALL x2) | 0.21 | 0.86 | 0.80 | 0.91 | 0.330 | 0.911 | 0.296 | 0.923 |
| Face 150 px (Q-SMALL x2) | 0.18 | 0.73 | 0.75 | 0.76 | 0.380 | 0.885 | 0.298 | 0.919 |
| Selfies 0.35 m (Q-NEAR) | 0.81 | 0.82 | 0.82 | 0.86 | 0.487 | 0.889 | 0.410 | 0.912 |

Numbers of the run after the FU-04 review (shipped defaults, WP-01 simulator). They equal the FU-03 run
within 0.002 (gate row then: NEES 1.022 / coverage 0.723): FU-04's shipped changes (detector thresholds)
do not touch the noise model. With the opt-in tangents the gate row reads 1.045 / 0.712 on the same
scenes and 1.047 / 0.711 on scheme-aligned scenes (section 3.1): inside the bands in both cases. The
deflation factor is 0.76.

Reading. The gate row is inside both bands (NEES 0.8-1.25, coverage 0.60-0.76); with the DESIGN factor
its coverage is 0.772, outside the band, and its NEES 0.804. The clean studio sets (per-kind
bias instead of the 1 mm row) read NEES 0.787, just below the band, i.e. conservative (not gated: the DESIGN 7.5 band is
stated for the 1 mm definition-bias row). Pooled NEES never exceeds 1.25 on any group; single sets
scatter (largest single-set NEES/dof 1.50 on the gate row, against a
chi-square standard deviation of 0.13 per set, so individual sets can be over-confident although the
population is calibrated). Sets with QA down-weights stay conservative under both factors (coverage
0.89-0.91): taking chi2_red before the multiplier keeps the factor near 0.75-0.9 there instead of at the
0.5 floor, so the remaining conservatism is the x2 multiplier itself (section 3.1, item 9).

Limits of this evidence: tier 1 only; `observability.deflation_min` 0.5 is uncalibrated; the factor was
chosen on FU-02's scorecard scenarios and confirmed here on different subjects, rigs and seeds, not on
real detections.

Scale: z RMS 1.07 on the clean sets (band 0.8-1.25) with a mean z of -0.67 (the reconstruction is
slightly small); 0.99 on clean rear-phone sets, 0.75 on selfies, 2.0 on 150 px faces (mean z -1.8: the
reported scale sigma does not cover the scale bias of small faces; section 3.1, item 9). The scale sigma is not affected by the factor change.

### 4.2 Per-vertex sigma_n: WP-19 note closed by recalibration

**What changed (stage `uncertainty`; DESIGN 4.15 note).** Sigma_X is the shape covariance `cov_shape`
(before: the full `cov`, which includes the scale direction that has its own sigma) times the sigma_rep
factor of section 4.1, and the regional residual sigma is `pipeline.sigma_res_scale` = 0.25 times
`fit.uncertainty.SIGMA_RES_MM`. The eleven regional values (literature warp residuals, DESIGN 4.15) are
unchanged; the multiplier is a new registered default with bounds [0, 1].

Calibration curve, pooled over 46 562 measured-region vertices of 30 sets (median |normal error|
1.0 mm; band 0.90-0.99; run after the FU-04 review):

| sigma_res scale | landmark covariance x factor | coverage at 1.96 sigma_n | z RMS | median sigma_n (mm) |
|---|---|---|---|---|
| 1 | `cov` x DESIGN factor (pre-WP-23) | 1.0000 | 0.27 | 7.1 |
| 0.25 | `cov` x DESIGN factor (pre-WP-23) | 0.9998 | 0.35 | 5.6 |
| 0 | `cov` x DESIGN factor (pre-WP-23) | 0.9997 | 0.36 | 5.5 |
| 1 | `cov_shape` x sigma_rep factor | 1.0000 | 0.36 | 5.7 |
| 0.5 | `cov_shape` x sigma_rep factor | 0.9938 | 0.51 | 4.2 |
| 0.35 | `cov_shape` x sigma_rep factor | 0.9889 | 0.57 | 3.9 |
| 0.25 | `cov_shape` x sigma_rep factor | 0.9858 | 0.60 | 3.7 |
| 0.15 | `cov_shape` x sigma_rep factor | 0.9831 | 0.63 | 3.6 |
| 0 | `cov_shape` x sigma_rep factor | 0.9812 | 0.65 | 3.5 |

Reading. With the pre-WP-23 covariance no value of sigma_res reaches the band (0.9997 even at
sigma_res = 0): the obstacle was the full covariance, not the residual term. With the shape covariance
the band is reached for multipliers of about 0.35 and below; 0.25 is shipped (coverage 0.9858, as in
the FU-03 run). The result is honest but still conservative: z RMS 0.60 and a median sigma_n of 3.7 mm
for a 1.0 mm error; coverage only moves from 0.981 to 0.994 over the whole range of the multiplier because the propagated
landmark covariance dominates (most measured vertices are on the scalp, labelled "measured" from the
single cranium landmark). A sharper sigma_n needs the gauge-projected reported covariance (Sigma1) in
the propagation and a per-vertex support rule, not a smaller sigma_res.

**Caveat, stated plainly.** The multiplier is fitted to synthetic subjects that the warp reproduces far
better than real faces (the literature residuals are 1-10 mm; here the whole normal error is 1 mm). On
real faces 0.25 x sigma_res is probably too small. It is badged new / provisional, and it must be
re-derived against scans before any claim on real data (H8); setting it to 1 restores the literature
values.

## 5. Scorecard v1 against the baseline (DESIGN 7.5 promotion rule)

`tests/golden/scorecard_v1.json`: engine v2 through `face3d.testbed.scorecard` with the baseline's seven
legacy scenarios, legacy prior settings and seeds 1000-1029 (BLAS threads pinned to 1). Seed-matched
medians (`scorecard.paired_medians`, 30 of 30 seeds usable in both cards):

| Scenario | config RMS v0 (mm) | v1 (mm) | change | NoW-7 RMS v0 | v1 | focal err v0 | v1 | distance err v0 | v1 | reprojection v0 (px) | v1 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| studio_ring_legacy | 3.459 | 3.347 | -3.2 % | 4.488 | 4.426 | 0.0122 | 0.0100 | 0.0340 | 0.0279 | 28.59 | 28.56 |
| rear_phone_legacy | 4.089 | 3.845 | -6.0 % | 5.039 | 4.904 | 0.0120 | 0.0073 | 0.0364 | 0.0263 | 17.58 | 17.56 |
| selfie_legacy | 6.988 | 6.123 | -12.4 % | 9.273 | 7.406 | 0.0265 | 0.0127 | 0.0522 | 0.0395 | 50.48 | 51.87 |
| camera_roll_legacy | 4.984 | 4.611 | -7.5 % | 6.909 | 6.020 | 0.0114 | 0.0078 | 0.0689 | 0.0314 | 22.36 | 21.25 |
| rear_phone_smooth | 4.091 | 3.928 | -4.0 % | 5.289 | 5.141 | 0.0100 | 0.0080 | 0.0378 | 0.0412 | 17.88 | 17.85 |
| rear_phone_nobias | 3.705 | 3.607 | -2.7 % | 4.654 | 4.552 | 0.0111 | 0.0072 | 0.0324 | 0.0300 | 17.75 | 18.01 |
| rear_phone_outliers | 4.716 | 4.503 | -4.5 % | 6.464 | 6.116 | 0.0128 | 0.0081 | 0.0472 | 0.0320 | 31.10 | 31.18 |

- No legacy scenario regresses in a shape metric (configuration RMS, NoW-7 RMS); no seed fails.
- Worse than the baseline by more than 2 % (reported, not shape metrics):
  `rear_phone_smooth:distance_rel_err` (0.0378 -> 0.0412, +9 %) and `selfie_legacy:rmse_px`
  (50.48 -> 51.87 px, +2.7 %; a fit residual, larger because the v2 solve no longer over-fits outliers).
- **Likeness-weighted error.** The baseline card stores no per-region errors, so E_like cannot be
  compared against v0 (the legacy engine is not available to regenerate it). The promotion check uses
  the two shape metrics the baseline has; E_like against v1 becomes possible once a card stores
  per-region RMS (follow-up for the scorecard format).
- The scorecard's NEES and coverage columns are the raw posterior covariance under the legacy prior
  settings (NEES/dof 2.1-3.4 in v1, 1.7-3.5 in v0): they are kept for continuity and are not the
  reported sigma_rep; the honesty gates of section 4 are.

## 6. Recorded decisions and known gaps

- **warp.alpha = 30** (WP-19): chosen on fold-gate and accuracy evidence, because the specified residual
  band (RMS/sigma in [0.5, 1]) is not reachable on the candidate grid (`face3d/geometry/rbf.py`,
  registered default `warp.alpha`, badge and evidence in its source string).
- **Coarse kits** (n <= 16) put two landmarks on one vertex, which makes the exact RBF rank-deficient;
  the default procedural kit is n = 24 (`face3d/model/procedural_head.py`).
- **Simulator gaps**: `detector_sim` does not draw the declared detector floor, draws the hair point
  (trichion) at the generic 2 mm, and draws its anisotropic noise along a random direction per landmark
  (the gates use it as is; the test harness can re-express that noise along the scheme's neighbour
  chords for diagnostics only, section 1). The procedural head has no lid, lip or outline curves, so the
  test bed has no independent ground truth for a detector's slide direction: whether the tangent metadata
  is right can only be measured on real detections (M7). `reconstruct_landmarks` takes tangents since FU-04
  (`PhotoLandmarks.tangents`); the legacy scheme has no neighbour metadata, so the scorecard is unchanged.
- **FU-04, not done / open** (each recorded where it is measured): the mirror, smile and retouch targets
  are unreachable at nominal noise (section 3.1 items 1, 4, 6: a decision on the rows is needed); the
  44-landmark identity bound cannot be met by tagging (item 5); the tangent metadata covers 16 of 44
  landmarks, is provisional and ships switched off (a wrong direction costs 4.5 % of inliers, section
  3.1); **three owner decisions are open**: (a) `pipeline.image_tangents` off by default, against the WBS
  item that asked for the tangents in the pipeline solve (DESIGN 4.4); (b) the item "every extremal
  landmark" narrowed to the points with a documented direction; (c) mirror evidence pooled through the
  consensus covariance only, without a set-level statistic (DESIGN 4.10); the new public
  functions of `face3d.solve` (`noise.image_tangents`, `mirror.derived_g_min`, `expression.retag_from_evidence`,
  ...) are not yet in the package export list, which another package owns.
- **Pipeline gaps found by the matrix** — closed by FU-03: the Q-RETOUCH residual step, the
  C-FOCAL-PRIOR finding and the focal-vs-EXIF flag (`C-FOCAL-EXIF`), the "hair" drop classes, Q-SMALL on
  the face width, the focal label inherited from a wrong EXIF prior. Still open: camera-model selection
  recorded but not applied (FU-03 task 6, optional, not done: the bundle has no per-view model hook that
  the pipeline could switch on without engine work in `solve/bundle.py`); likeness mode not exposed;
  Q-SMALL measured in the working frame; a geometric Q-ORIENT check (view RMS and roll) is not wired, so
  an unbaked orientation is caught only from the LandmarkSet metadata (`orientation_applied: false`;
  30/30).
- **Found by FU-03, not fixed here (engine files outside the package):** (i) the photos-only focal
  estimate is biased low on the matrix rigs (median -12 % on the rear-phone sets with the distance prior
  left in, about +/-20 % scatter without it), which is why a missing EXIF costs 11 % of focal; (ii) at
  0.30-0.35 m the re-solve under the ladder's phone prior can stay in the valley of a 30 % long focal
  (9 of 15 contradicted sets); (iii) the engine's retouch test flags 1 of 90 unretouched selfie views at
  0.35 m (strong perspective reads as eye enlargement); inside the 5 % bound, but it is the only false
  alarm of that test anywhere; (iv) a forced-in face below the reject size used to carry no down-weight
  at all (fixed in the landmarks stage).
- **Runtime budget: the default-run criterion is NOT met (no waiver recorded).** The WBS asks for a
  default run under 3 min and a slow run under 10 min. Measured after FU-03 (4 cores, BLAS pinned to one
  thread): default run `python -m pytest` 6 min 12 s (594 passed, 2 xfailed; WP-23 recorded 5 min 45 s
  with 584 passed, 3 xfailed); release run `python -m pytest -m slow` 5 min 58 s (met; 5 min 37 s at
  WP-23). FU-03 added ten tests to the default run, about 15 s in all (three pipeline runs for the
  near-range EXIF check and the seed-2313 Q-SMALL regression, the focal-evidence unit tests, the retouch
  wiring test); the pipeline stages themselves gained only linear algebra on stored matrices (no extra
  solve unless an EXIF focal is contradicted). After the FU-03 review fixes: 6 min 00 s (595 passed, 2 xfailed; one regression test added, the
  focal-evidence unit test cut from three seeds to one per condition; the release run additionally solves
  the 60 glasses / hair sets for the Q-RETOUCH false-alarm pool, the per-push subset does not). The
  default run is still above the WP-23 figure: the rule "keep the default suite time from growing" is
  recorded as not met, not waived. The remaining difference to the WP-23 figure was not
  attributed: the two timings were taken in different sessions on a shared machine, and the WP-23 tree
  could not be re-timed here. Of the default run the three WP-23 files take 1 min 25 s (the 5-seed
  fault matrix about 58 s, the alarm budget 9 s, the offline pipeline check 6 s); the tests of the
  earlier packages take about 4 min 45 s on their own, so the budget was exceeded before WP-23 and cannot
  be met from these files. The heaviest legacy tests: `test_observability.py::test_sigma_rep_honesty_on_testbed`
  28 s, the `test_contours.py` fixture 20 s, `test_warp_uncertainty.py::test_coverage_measured_regions_small`
  10 s; then a long tail of 3-8 s tests, so marking a few tests `slow` does not reach 3 min either. Open
  decision for the owners: move legacy tests under the `slow` marker, run the suite in parallel, or waive
  the criterion.
  **After FU-04 (and its review):** default run 6 min 37 s (605 passed, 1 xfailed; 6 min 18 s / 6 min 26 s
  on the two runs of the first FU-04 version; 595 + 2 tests before FU-04), release run 6 min 0 s (5 min 58 s
  before FU-04). FU-04 added nine tests to the default run and turned the strict xfail of the mirror row
  into a passing test: unit tests of the tangent, mirror and re-tag statistics, the mirror row at half
  noise (3 s), the Monte Carlo of the mirror rule through the engine added by the review (6 s), and six
  pipeline runs for the opt-in tangents (4 s); the solve stage also runs one more pass-2 bundle for every
  view whose tag the recalibrated re-tag changes (about 4 % of the neutral views, every jaw view). The rule
  "keep the default suite time from growing" is again recorded as **not met** (+25 s to +37 s against the
  two FU-03 figures on this shared machine, where two runs of the same tree differ by about 8 s), not waived.

## 7. Policy checks

`tools/ci_checks.py` (also `tests/test_policy_ci.py`, which plants a violation for each static check):
(a) no bpy / scipy / cv2 / torch / mediapipe / PIL import under `face3d/`; (b) no NumPy 1-only alias;
(c) every registered default has a valid badge and a source; (d) only `bridge.py` touches mesh or pixel
buffers, the manifest passes the store lint, every extension file carries the GPL SPDX header; (e) every
fixture with landmark or mesh data declares provenance synthetic / cc0 / consented; (f) a full synthetic
pipeline run with texture completes under `network_guard`. All pass.
