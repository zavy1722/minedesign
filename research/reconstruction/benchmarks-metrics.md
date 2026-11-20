# Benchmarks and metrics for face reconstruction accuracy

> Every published face-reconstruction error rests on three choices: alignment (landmarks, ICP, with or without scale), distance (scan-to-surface, Chamfer, nearest vertex) and crop; change one and numbers stop being comparable. NoW, the de facto identity-shape benchmark, is near saturation: a correctly scaled *average* FLAME face scores ≈1.5 mm mean, MICA ≈1.1 mm and the best entries ≈0.95 mm, so single-image methods remove only a quarter to two fifths of the mean face's error. REALY re-aligns each region and reorders methods, FaceScape adds yaw and focal-length sweeps, and Florence/MICC and Stirling/ESRC are older protocols whose numbers do not transfer. None scores absolute size, inter-feature configuration, lids, ears or likeness, so our tool reports a NoW-compatible number plus metric scale, regional signed error, configuration, profile and held-out-view checks. No harvest or draft existed: everything is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 0 📄 / 60 🧠 / 26 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Benchmarks**
- **NoW** (Sanyal, Bolkart, Feng & Black, CVPR 2019, with RingNet): ≈2,054 iPhone images of 100 adults in four conditions (neutral, expression, occlusion, selfie), with one neutral active-stereo (3dMD-type) scan per subject. Validation has 20 subjects; test has 80, with ground truth hidden behind a submission server. Expression images are scored against the *neutral* scan, so NoW measures expression-invariant identity shape. 🧠
- **NoW protocol.** The submitter supplies 7 landmarks on the prediction (4 eye corners, a nose point, 2 mouth corners). A similarity fit on these seeds a rigid refinement minimising scan-to-mesh distance. Each scan vertex is measured to the nearest point on the predicted *surface*; median, mean, std and a cumulative curve are reported. Scale is solved ("non-metrical"); MICA (ECCV 2022) added a metrical track without it. The procedure follows Feng et al., FG 2018. 🧠
- **REALY** (Chai et al., ECCV 2022): ≈100 Headspace/LYHM subjects, frontal and multi-view images, scans masked into nose, mouth, forehead and cheek. After a keypoint global alignment it re-aligns *each region* (region-aware ICP) and reports per-region mean nearest-point error and the average, arguing that whole-face ICP lets one region's error shift another's alignment. It also released the HIFI3D++ morphable model. 🧠 Exact correspondence rule ↔️.
- **Stirling/ESRC**: Di3D stereophotogrammetry scans (neutral and expressions, research licence) behind the FG 2018 in-the-wild reconstruction challenge (Feng, Huber, Kittler, Hancock et al.), with high- and low-quality image subsets scored as 3D-RMSE after landmark + ICP alignment. Recalled size ≈2,000 test images of ≈130 subjects ↔️.
- **FaceScape** (Yang et al., CVPR 2020): ≈938 subjects × 20 expressions (≈18,760 textured models) from a dense DSLR rig. Its benchmark extension (Zhu et al., IEEE TPAMI) scores Chamfer distance (mm), complete rate (%) and mean normal error, binned by **yaw and focal length**, the only major benchmark that probes perspective. Mostly East Asian subjects; research-only, by application. 🧠 Bin edges and set sizes ↔️.
- **Florence/MICC** (Bagdanov, Del Bimbo & Masi, 2011): 53 subjects, 3dMD scans, cooperative, PTZ and outdoor video. Two incompatible protocols: Tran et al. 2017 / Genova et al. 2018 crop ground truth to ≈95 mm around the nose tip and report point-to-plane error after ICP (≈1.5–2 mm for 2018-era methods) ↔️; VRN/PRNet/3DDFA-style papers report NME in % of outer inter-ocular distance (≈3–6 %) ↔️.
- **AFLW2000-3D** (Zhu et al., CVPR 2016): 2,000 in-the-wild images whose "ground truth" is a 3DMM fit, scored as 68-landmark NME over bounding-box size. It measures agreement with another fitter, not shape. 🧠
- **Newer:** DAD-3DHeads (CVPR 2022; dense head annotations, Chamfer and pose metrics) and the Pixel3DMM benchmark (2025; NeRSemble multi-view ground truth, neutral *and* posed expressions). Adoption by late 2026 unknown. ↔️

**Metric mechanics**
- **Direction.** Scan→mesh ignores junk geometry where the scan has no points; mesh→scan is inflated by scan holes; Chamfer averages both. Papers mix sums and means, squared and unsquared distances and ×10³ scalings, so "Chamfer" does not compare across papers. 🧠
- **Nearest vertex vs nearest surface.** Measuring to the nearest *vertex* adds a lateral offset averaging ≈0.35 × edge length (triangular-lattice arithmetic), in quadrature with the true error. On FLAME's ≈3–6 mm level-0 edges that is ≈1–2 mm, larger than the signal. Always measure point-to-triangle. 🧠
- **Alignment optimism.** ICP minimising the error you report absorbs part of the shape error; similarity alignment hides scale error completely; per-region alignment hides configuration error (a correctly shaped nose sitting 2 mm low). A landmark-only alignment is the pessimistic counterpart. 🧠
- **Heavy tails.** NoW mean/median ≈1.2–1.25 against 1.18 for a half-normal (`single-image-regression.md`). Report median, mean, std, p90/p95 and fractions within 1 and 2 mm; a vertex mean is an area mean only if the scan is uniformly sampled. 🧠
- **Normals.** Angular error after low-pass captures the plane and form errors a MatCap shows and millimetre metrics underweight; FaceScape's is the only standard normal metric. 🧠
- **2D metrics on the input images** (landmark NME, silhouette IoU, LPIPS) are fit residuals, not accuracy; only **held-out views** test generalisation. 🧠
- **Identity-embedding similarity** is a texture-dominated, scale-blind likeness proxy (`identity-embeddings.md`). 🧠

**State of the art and noise floor**
- NoW (non-metrical): scaled mean face ≈1.53 mm mean; DECA ≈1.09/1.38 mm median/mean; MICA ≈0.90/1.11; best 2023–25 entries ≈0.75–0.8/≈0.95. Gaps under ≈0.1 mm are protocol noise. 🧠 (sourced in `single-image-regression.md`)
- REALY method averages run ≈1.5–2.2 mm; the mouth varies most between methods. ↔️
- Stereophotogrammetry vendors (3dMD, Di3D) claim sub-0.5 mm accuracy on rigid targets; repeat captures of a live face differ by ≈0.3–1 mm RMS (micro-expression, breathing, lip seal, hair), so ground truth itself is uncertain by ≈0.3–0.5 mm. ↔️
- **No public benchmark** scores few-photo multi-view consumer capture, absolute size, lids and ears, or perceived likeness. 🧠

## Numbers & reference tables

**Table 1: Benchmark cards**

| Benchmark | Ground truth | Subjects / images | Conditions | Alignment | Metric | Blind to | Status |
|---|---|---|---|---|---|---|---|
| NoW (2019) | neutral active-stereo scan | 100 / ≈2,054 | neutral, expression, occlusion, selfie | 7 lm → rigid; scale solved (metrical track: none) | scan→surface median/mean/std, mm | size, local regions, ears | 🧠 |
| REALY (2022) | Headspace scans, region masks | ≈100 | frontal + multi-view | keypoints, then per-region ICP | per-region mean nearest-point, mm | inter-region configuration, size | ↔️ |
| Stirling/ESRC FG 2018 | Di3D scans | ≈130 / ≈2,000 | HQ and LQ in-the-wild | 7 lm + ICP | 3D-RMSE, mm | size, regions | ↔️ |
| FaceScape (2020; TPAMI ext.) | 68-camera multi-view stereo | ≈938 × 20 expressions | lab and wild; yaw and focal bins | ICP-type | Chamfer mm, complete rate %, normal error | likeness; skews East Asian | ↔️ |
| Florence/MICC (2011) | 3dMD | 53 | cooperative / PTZ / outdoor video | ICP (± scale), 95 mm crop | point-to-plane mm, or NME % | protocol-dependent | ↔️ |
| AFLW2000-3D (2016) | 3DMM fit (pseudo-GT) | 2,000 images | in the wild, large pose | none (2D) | 68-lm NME, % bbox | true shape | 🧠 |

**Table 2: NoW anchors** (mm, non-metrical; splits differ by row, see `single-image-regression.md`). Skill = 1 − mean/1.53.

| Entry | Median | Mean | Skill vs mean face | Status |
|---|---|---|---|---|
| Average FLAME, no scale fit | – | ≈1.92 | – | 🧠 |
| Average FLAME, scale fitted | – | ≈1.53 | 0 % | 🧠 |
| DECA (test) | ≈1.09 | ≈1.38 | ≈10 % | 🧠 |
| MICA | ≈0.90 | ≈1.11 | ≈27 % | 🧠 |
| Best 2023–25 (e.g. TokenFace) | ≈0.75–0.8 | ≈0.95 | ≈38 % | ↔️ |
| Late-2026 leader | unknown | unknown | – | ↔️ |

**Table 3: REALY region errors** (frontal track, mm, ranges recalled across Deep3D, DECA, 3DDFA_V2, HRN, 3DDFA-V3)

| Region | Range | Note | Status |
|---|---|---|---|
| Nose | ≈1.6–2.0 | depth-driven; similar across methods | ↔️ |
| Mouth | ≈1.3–2.5 | biggest spread; expression leakage | ↔️ |
| Forehead | ≈1.8–2.5 | weak landmark support, hairline | ↔️ |
| Cheek | ≈1.0–1.6 | smooth, easiest | ↔️ |
| Average | ≈1.5–2.2 | HRN-class ≈1.5–1.6 at the low end | ↔️ |

**Table 4: Metric definitions** (d = unsigned distance; P = GT points; M = prediction surface)

| Metric | Definition | Trap | Our use | Status |
|---|---|---|---|---|
| Scan→mesh (S2M) | d(p, M), p ∈ P | ignores prediction outside crop | NoW-compatible headline | 🧠 |
| Mesh→scan | d(m, scan) | inflated by holes; cap at 5 mm | signed sculpt heatmap | 🧠 |
| Chamfer | ½(mean S2M + mean M2S), unsquared | definitions vary | report with formula | 🧠 |
| Hausdorff / p95 | max / 95th percentile | max is one outlier | p95 only | 🧠 |
| F-score@τ | harmonic mean of precision and recall within τ | τ-dependent | τ = 1 and 2 mm | 🧠 |
| Normal error | angle between normals after low-pass | needs matched smoothing | per region, degrees | 🧠 |
| Landmark error | 3D mm or 2D % IOD | definition bias | configuration, held-out views | 🧠 |
| Scale error | s − 1 from similarity fit; % error of ex–ex, n–gn | invisible on NoW | always reported | 🧠 |

**Table 5: Error budget and floors**

| Source | Size | Status |
|---|---|---|
| Nearest-vertex bias (mean lateral offset) | 0.35 × edge; FLAME level 0 ≈1–2 mm | 🧠 (arithmetic) |
| Scanner accuracy, rigid target (vendor claims) | ≈0.1–0.5 mm | ↔️ |
| Live-face repeat capture | ≈0.3–1 mm RMS, worst at lips and cheeks | ↔️ |
| Benchmark gaps that are noise | ≲0.1 mm | 🧠 |
| Mean-face per-point σ (half-normal, σ = mean/0.798) | ≈1.9 mm | 🧠 (derived) |
| MICA per-point σ (same model) | ≈1.4 mm | 🧠 (derived) |

**Table 6: Proposed acceptance targets for our tool** (design defaults; adult face crop with a scan; weights from `anatomy/face-perception-likeness.md` Table B)

| Region | Weight | RMS target (mm) | p95 (mm) | Status |
|---|---|---|---|---|
| Eyes, lids, canthi | 1.0 | ≤1.0 | ≤2.0 | 🧠 |
| Brows, supraorbital | 0.9 | ≤1.2 | ≤2.5 | 🧠 |
| Lips, perioral | 0.8 | ≤1.0 | ≤2.0 | 🧠 |
| Nose (projection) | 0.7 | ≤1.2 (≤1.5) | ≤2.5 | 🧠 |
| Forehead, cheeks | 0.6 | ≤1.5 | ≤3.0 | 🧠 |
| Jaw, chin | 0.6 | ≤2.0 | ≤4.0 | 🧠 |
| Ears, cranium | 0.1–0.2 | ≤3.0 | ≤6.0 | 🧠 |
| Global face crop (NoW-style) | – | median ≤0.8, mean ≤1.0 | – | 🧠 |
| Metric scale, with reference | – | ≤1.5 % | – | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Build a small ground-truth set before tuning.** One to three consenting sitters, each with a reference scan (structured light or a multi-camera photogrammetry burst, `reconstruction/photogrammetry-heads.md`) plus same-day photos shot to the add-on's protocol. Scan twice, ten minutes apart: that RMS is your floor; don't chase errors below it. 🧠
2. **Match units first.** FLAME is in metres, scans and the engine in millimetres. A 1000× mismatch or a mirrored import (negative scale) is the commonest "huge error"; apply transforms before measuring. 🧠
3. **Align twice and report both.** (a) Landmark-only Umeyama on endocanthion ×2, exocanthion ×2, nasion and subnasale, with scale fixed when the fit claims metric size: keeps configuration and size errors. (b) Rigid ICP on stable regions (forehead, nasal bridge, zygomas), as in clinical superimposition, seeded by (a). NoW-style similarity + ICP is only for comparing with papers. 🧠
4. **Signed heatmap on the sculpt.** Geometry Nodes: *Geometry Proximity* (target = scan) gives nearest point and distance; *Sample Nearest Surface* gives the scan normal there; sign = sign((position − nearest) · normal), positive meaning too much clay. Store as an attribute and display via Attribute → Map Range → diverging ramp at ±2 mm with a grey ±0.3–0.5 mm deadband (the floor). For a quick unsigned view, the *Vertex Weight Proximity* modifier (Geometry, Face) works. Mask points >5 mm away or nearest to a scan-hole border. Node names are version-sensitive. 🧠
5. **Fix in perceptual order** (Table 6): configuration (landmark errors after alignment a), then lids, brows and lips, then the nose profile, then broad planes. A low global RMS can hide a 2 mm lid error that ruins the likeness. 🧠
6. **Without a scan** (the usual case): leave-one-view-out reprojection (fit N−1 photos, measure landmarks and silhouette on the held-out one); camera-matched overlays of every solved view including both profiles; profile-contour distance in mm, scaled by measured inter-ocular distance (IOD) or a ruler; identity-embedding ceiling ratio on clay renders; a blind six-face lineup judged by people who know the sitter (chance 17 %, target ≥80 %). 🧠
7. **Expect** ≈1–1.5 mm mean from any single-image regressor and ≈1.2 mm shape RMS from a 5-view landmark-only engine fit (`camera-pose-solving.md` simulations). Only silhouette, profile and sculpting passes get below ≈0.8 mm median; eyes, mouth interior, ears and the back of the head stay worst. 🧠
8. **Scan pitfalls:** hair, beard and brows read as surface; eyeballs are noisy; lips may be parted; the scan may predate a weight change. Crop or exclude, and log it. 🧠

## Algorithmic implications

- **New module `face3d/eval/`** (numpy only): `closest_points(P, V, F)` with a uniform-grid broad phase over triangle bounding boxes and Ericson's exact closest-point-on-triangle test; sign from the angle-weighted pseudo-normal (Bærentzen & Aanæs) to avoid flips at edges; returns distance, signed distance, closest point and face id. 🧠
- **`align(pred, gt, mode)`**, modes `landmarks`, `rigid_icp`, `similarity_icp` (NoW-compatible), `region`. Seed with `face3d/geometry/procrustes.py::umeyama` on the 7 NoW or 6 stable landmarks; point-to-plane ICP, 10 % trimming, 5–10 mm correspondence cap, 60° normal-agreement gate, ≤30 iterations, 1e-4 mm tolerance. 🧠
- **`surface_report(d, region_labels, area_w)`**: area-weighted median, mean, std, RMS, p90, p95, F@0.5/1/2 mm and signed bias per region. Region labels live on the template and reach GT points via the nearest aligned template vertex. Always print the Chamfer formula used. 🧠
- **Configuration**: `procrustes_rmse` over 20–30 anatomical landmarks after landmark-only alignment, plus per-landmark error vectors in a Frankfort-aligned frame. **Scale**: similarity s − 1 and % error of ex–ex, n–gn, zy–zy and t–t against measurements; |s − 1| > 3 % flags "scale unreliable". **Normals**: smooth both surfaces to ≥9 mm wavelength, then per-region angle statistics. 🧠
- **Likeness score** = region-weighted RMS (Table 6), reported *beside*, never instead of, the NoW-style median. Perceptual weights steer evaluation and guidance, never the data term. 🧠
- **Priors from benchmark numbers** (half-normal model, σ = mean/0.798): a MICA-type regressor as shape prior gets σ ≈ 1.4 mm along the normal, raised to 2.5–3 mm for nose tip, chin and orbit depth; the population prior after similarity alignment averages σ ≈ 1.9 mm per surface point. A fit within ≈1 mm RMS of the mean face is prior-dominated: warn and request another view. 🧠
- **Held-out-view gate**: accept a sculpt or refinement step only if held-out landmark (% IOD) and silhouette errors do not rise; flag a view whose held-out error exceeds 2× its in-sample error. 🧠
- **CI on `face3d/synthetic.py` subjects**: assert median S2M, scale error and configuration RMS per camera configuration so solver regressions show up as numbers. 🧠

## Disagreements, myths & open questions

- **Whole-face vs per-region alignment** ↔️: NoW averages away local errors, REALY hides misplacement between regions. Report both, plus landmark-only alignment.
- **Chamfer vs scan-to-mesh** ↔️: some papers (KaoLRM-type, `single-image-regression.md`) report Chamfer-style numbers on NoW data that are not leaderboard-comparable.
- **Myth: "lower NoW error means better likeness."** NoW is scale-free, neutral-only and whole-face; REALY reorders methods. ↔️
- **Myth: "a detail layer improves accuracy."** DECA's detail map leaves NoW unchanged (1.18 → 1.19 mm median; verified in `single-image-regression.md`). Detail matters perceptually, not metrically. 🧠
- **Myth: "AFLW2000-3D NME is 3D accuracy."** Its ground truth is a fit. 🧠
- **Myth: "the scan is truth."** Repeat scans differ by ≈0.3–1 mm and include hair and eyeball noise. ↔️
- **Demographics** ↔️: NoW (recruited in Germany, probably mostly European), REALY (UK Headspace) and FaceScape (mostly East Asian) differ; how rankings shift with ancestry and age is unknown.
- **Open:** late-2026 NoW and REALY leaders; Pixel3DMM benchmark adoption; the 3D just-noticeable displacement per region (Haig 1984 tested 2D); a validated map from regional millimetres to lineup accuracy; a benchmark for 3–9 consumer photos with perspective and metric scale.

## Sources

No input files existed, so no URLs are cited. Sourced versions of the overlapping NoW numbers live in `reconstruction/single-image-regression.md` and `reconstruction/generative-3d-heads.md`.

**Further reading (by name, not yet linked)**
- Sanyal, Bolkart, Feng & Black, RingNet and the NoW benchmark ("Learning to Regress 3D Face Shape and Expression from an Image without 3D Supervision"), CVPR 2019
- Chai et al., "REALY: Rethinking the Evaluation of 3D Face Reconstruction", ECCV 2022
- Feng, Huber, Kittler, Hancock et al., "Evaluation of Dense 3D Reconstruction from 2D Face Images in the Wild", FG 2018
- Yang et al., FaceScape, CVPR 2020; Zhu et al., FaceScape benchmark, IEEE TPAMI
- Bagdanov, Del Bimbo & Masi, "The Florence 2D/3D Hybrid Face Dataset", 2011
- Zielonka, Bolkart & Thies, MICA, ECCV 2022; Feng et al., DECA, SIGGRAPH 2021
- Zhu et al., 3DDFA and AFLW2000-3D, CVPR 2016; Jackson et al., VRN, ICCV 2017; Feng et al., PRNet, ECCV 2018
- Tran et al., "Regressing Robust and Discriminative 3D Morphable Models with a Very Deep Neural Network", CVPR 2017; Genova et al., "Unsupervised Training for 3D Morphable Model Regression", CVPR 2018
- Dai, Pears, Smith & Duncan, LYHM/Headspace craniofacial model, ICCV 2017
- Lei et al., HRN, CVPR 2023; Martyniuk et al., DAD-3DHeads, CVPR 2022; Giebenhain et al., Pixel3DMM, 2025; Kirschstein et al., NeRSemble, TOG 2023
- Tatarchenko et al., "What Do Single-view 3D Reconstruction Networks Learn?", CVPR 2019
- Besl & McKay, ICP, 1992; Chetverikov et al., trimmed ICP, 2002; Umeyama, TPAMI 1991
- Ericson, *Real-Time Collision Detection*, 2004; Bærentzen & Aanæs, angle-weighted pseudonormal, IEEE TVCG 2005
- Haig, "The effect of feature displacement on face recognition", Perception 1984
