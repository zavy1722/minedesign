# Math for landmark-driven mesh fitting

> Landmark-driven head fitting is a coarse-to-fine stack of least-squares problems. Similarity Procrustes (SVD) sets pose and scale, and a PCA prior is solved as Tikhonov least squares. A polyharmonic (thin-plate) RBF warp absorbs the residual landmark offsets. Surface-aware refinement follows: bilaplacian displacement, ARAP, or non-rigid ICP when a target surface exists. Cameras and landmarks are solved jointly by Levenberg–Marquardt on whitened residuals, with robust IRLS weights and priors added as residual rows. The traps are sign conventions (Procrustes reflections, and the 3D biharmonic kernel sign, a live bug in this repo's engine), conditioning, gauge freedom, and priors that pull the likeness toward the average face.
>
> Evidence status: 9 ✅ / 18 📄 / 29 🧠 / 4 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Similarity Procrustes**
- **Closed form.** Unweighted similarity alignment is closed-form [1]: centre both sets, SVD the cross-covariance, take the rotation from the singular vectors with a determinant correction against reflections; scale and translation follow. 📄
- **Translation.** Once R and s are known, t = μ_dst − s·R·μ_src [1][5]. ✅
- **Umeyama form** (dst ≈ sRx + t): Σ = (1/n)Σ ỹᵢx̃ᵢᵀ = UDVᵀ; S = diag(1, 1, sign(det U·det V)); R = USVᵀ; s = tr(DS)/σ²_src; ε² = σ²_dst − tr(DS)²/σ²_src. R is unique only if rank Σ ≥ 2, so at least 3 non-collinear points are needed. 🧠
- **Weights.** Scalar per-point weights keep the closed form; two-sided or anisotropic weighting generally needs iteration [2]. 📄
- **Generalized Procrustes** is iterative because the mean is re-estimated on every pass [2][4]. ✅
- **Scale is asymmetric.** s(A→B) ≠ 1/s(B→A), and noise in the *source* biases s low. Horn's symmetric scale, ‖Ỹ‖/‖X̃‖, avoids this. 🧠

**Thin-plate / polyharmonic RBF**
- **Form.** TPS is a closed-form non-rigid interpolant: an affine part plus radial kernels. In 2D the kernel is U(r) = r² ln r [6][7], and current landmark-registration pipelines use it [7][8]. ✅
- **Bending energy.** TPS minimises ∫‖Hess f‖²_F subject to Σwᵢ = 0 and Σwᵢcᵢ = 0. The energy is a quadratic form in the landmark displacements, whose eigenvectors are Bookstein's principal warps [6]. 📄
- **Noisy landmarks.** K + λI turns interpolation into approximation; as λ→∞ the map becomes affine [6][7]. ✅ (2D)
- **3D kernel.** In 3D the bending-energy kernel is U(r) = r. A patent uses it for a 3D TPS-style model [23]. 📄 The dimension rule comes from Duchon's polyharmonic splines. 🧠
- **Sign trap.** −r, not r, is the conditionally positive definite kernel (order 1). With Kᵢⱼ = ‖cᵢ − cⱼ‖, the smoothing system is therefore **K − λI**, and bending energy = −wᵀKw. For r³ (order 2, + sign), K + λI is correct. Multiquadric behaves like r. 🧠
- **Smoothness against extrapolation.** φ = r has a C⁰ cone at each centre, and its non-affine part decays like 1/distance. r³ is C², but its non-affine part grows away from the landmarks and swings the back of the head. 🧠
- **Ambient-space warp.** An RBF warps space, not the surface. It drags together points that are near in space but far apart along the surface: the two lips, the two lids, ear and scalp. 🧠

**Laplacian, biharmonic, ARAP**
- **Established family.** Linear variational and Laplacian (differential-coordinate) deformation is mature and well surveyed [18][21][22]. ✅
- **Biharmonic deformation** solves the bi-Laplace equation. With identity handles it does *not* reproduce a surface that is not already biharmonic [19]. 📄 So solve for the displacement d = x − x₀, not for positions. 🧠
- **Bounded biharmonic weights** minimise Laplacian energy under bound constraints [20]. 📄
- **Cotan Laplacian.** wᵢⱼ = ½(cot αᵢⱼ + cot βᵢⱼ), L = D − W, with lumped mass M. Harmonic energy ‖∇d‖² leaves kinks or dimples at point handles; the bilaplacian dᵀLM⁻¹Ld is smooth there. Obtuse triangles give negative weights. Position-based Laplacian editing is not rotation-invariant. 🧠
- **ARAP** (Sorkine & Alexa 2007) alternates a local step, the best rigid fit per cell (a Procrustes problem), with a global linear solve [9][10]. 📄 An implementation guide exists [12]. 📄
- **ARAP equations:** E = ΣᵢΣⱼ wᵢⱼ‖(x′ᵢ − x′ⱼ) − Rᵢ(xᵢ − xⱼ)‖². Local step: Sᵢ = Σwᵢⱼeᵢⱼe′ᵢⱼᵀ = UΣVᵀ, Rᵢ = VUᵀ with a determinant fix. Global step: Lx′ = b, bᵢ = Σⱼ(wᵢⱼ/2)(Rᵢ + Rⱼ)(xᵢ − xⱼ). L is fixed, so factor it once. 🧠
- **Spikes.** Standard ARAP spikes at point handles; a 2025 higher-order variant targets this [13]. 📄
- **Scaling.** ARAP resists real between-person scaling. Run it after the similarity and RBF stages, or allow a scale per cell (as-similar-as-possible). 🧠

**Non-rigid ICP**
- **Stiffness schedule.** Optimal-step NICP lowers stiffness from high to low, moving from global to local deformation, and works with any regulariser that has a stiffness knob [14]. Face-scan tracking and face capture also anneal stiffness and landmark weights [16][17]. ✅
- **Black-box optimisers** have a tiny convergence basin and fail on incomplete surfaces unless the starting point is almost perfect [14]. 📄 A statistical NICP variant also exists [15]. 📄
- **Amberg's model:** a 3×4 affine Xᵢ per vertex; E = E_d + αE_s + βE_l, with E_s = ‖(M⊗G)X‖²_F (M the incidence matrix, G = diag(1, 1, 1, γ)). Each inner step is one sparse linear least-squares solve. Reject pairs on boundaries, or where normals differ by more than about 45–60°. 🧠

**PCA prior, robust losses, LM**
- **PCA prior as Tikhonov.** The model is x = x̄ + U·diag(σ)·β with β ~ N(0, I). For Aβ ≈ b with noise σₙ, β* = (AᵀA + σₙ²I)⁻¹Aᵀb: Tikhonov with λ = σₙ². Solve it with SVD filter factors dₖ/(dₖ² + λ). 🧠
- **Typical set.** Real faces have ‖β‖² ≈ k ± √(2k); weak-data MAP fits have ‖β‖ ≪ √k (the "average face" look). Monitor k_eff = Σdₖ²/(dₖ² + λ). 🧠
- **Robust weights.** IRLS with σ = 1.4826·MAD. Constants for 95% efficiency: Huber 1.345σ, Cauchy 2.385σ, Tukey 4.685σ. Non-convex losses need a good start or graduated non-convexity. 🧠 (Huber 1.345 and Tukey 4.685 confirmed by [27]; Cauchy 2.385 and the MAD factor not confirmed.)
- **LM step:** (JᵀWJ + μ·diag(JᵀWJ))δ = −JᵀWr. Nielsen update: on success μ ← μ·max(⅓, 1 − (2ρ−1)³), ν ← 2; on failure μ ← μν, ν ← 2ν; start μ₀ = τ·max diag, τ = 10⁻⁶–10⁻³ [25][26]. The normal equations square cond(J); beyond about 10⁸, use QR or lstsq on [√W·J; √μ·D]. 📄 (Nielsen update rule confirmed in [25][26]; the τ range and the conditioning threshold were not confirmed.)
- **Rotation and projection:** R ← exp([δ]×)R with ∂(Rp)/∂δ = −[Rp]×; ∂(u, v)/∂(X, Y, Z) = (f/Z)·[[1, 0, −X/Z], [0, 1, −Y/Z]]; estimate log f. 🧠
- **Gauge.** Uncalibrated multi-view landmarks leave a 7-DoF similarity unobservable; absolute size needs a metric measurement or prior. 🧠

## Numbers & reference tables

**Table 1: Deformation operators**

| Method | Energy | Solve | At point handles | Face-fitting role | Status |
|---|---|---|---|---|---|
| Similarity Procrustes | Σ‖y − (sRx + t)‖² | 3×3 SVD | n/a | initial pose and scale | 📄 [1] |
| RBF φ = r (3D) | ∫‖∂²f‖² over ℝ³ | dense (n+4)²; evaluation O(n·m) | C⁰ cone; far field → affine | global template warp | 🧠 (2D TPS ✅ [6][7]) |
| Biharmonic (displacement) | ∫(Δd)² | sparse SPD | smooth | on-surface refinement | 📄 [19] |
| ARAP | Σ‖e′ − Rᵢe‖² | per-cell SVD + one prefactored solve | spikes [13] | keep feature shape | 📄 [9][13] |
| NICP | affine per vertex + stiffness | sparse least squares per step | n/a | a target scan or photogrammetry mesh exists | ✅ [14][16][17] |
| PCA/3DMM | ½‖β‖² + data | k×k (FLAME k ≤ 300) | global | plausible base; fills unseen areas | 🧠 |

**Table 2: RBF kernels**

| Dim | φ(r) | Minimises | CPD order, sign | Smoothing system | Status |
|---|---|---|---|---|---|
| 2 | r² ln r | ∫‖Hess f‖² | 2, + | K + λI | ✅ [6][7] |
| 3 | r | ∫‖∂²f‖² | 1, − | **K − λI** | 📄 kernel [23], 🧠 sign |
| 3 | r³ | ∫‖∂³f‖² | 2, + | K + λI | 🧠 |
| any | exp(−(r/ε)²) | none | PD | K + λI; ill-conditioned for large ε | 🧠 |

**Table 3: Robust losses** (r = whitened residual; c in units of σ)

| Loss | IRLS weight | c at 95% efficiency | Convex | Status |
|---|---|---|---|---|
| Huber | min(1, c/\|r\|) | 1.345 | yes | 📄 [27] |
| Cauchy | 1/(1 + r²/c²) | 2.385 | no | 🧠 |
| Geman–McClure | c⁴/(c² + r²)² | — | no | 🧠 |
| Tukey | (1 − r²/c²)² inside c, 0 outside | 4.685 | no | 📄 [27] |

**Table 4: Perspective cue against distance.** The ratio is Z/(Z − Δz), with Δz ≈ 0.10 m from nose tip to ear plane (assumed; adults are roughly 0.09–0.12 m). 🧠

| Camera to ear plane, Z (m) | 0.3 | 0.5 | 0.75 | 1.0 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|---|---|
| Nose-tip plane magnification relative to ear plane | 1.50 | 1.25 | 1.15 | 1.11 | 1.07 | 1.05 | 1.03 |

Beyond ~1.5 m, landmarks barely separate focal length from distance, so an EXIF focal prior is required. Below ~0.5 m, distortion is large but makes the focal length estimable.

## Applying this to photo→3D face sculpting in Blender

1. **Units and scale.** Use a millimetre scene, but solve in normalised units (centred, landmark RMS radius 1) so λ and weights are scale-free. Absolute size needs one real measurement, such as a ruler-measured pupillary distance. Without it, label the result "proportions only".
2. **Camera match.** Compute f_px = f_mm·W_px/sensor_mm and set **Sensor Fit** explicitly. Auto applies the sensor width to the longer image side, so a portrait photo whose f_px was computed from its width will not line up. Use Shift X/Y for cropped principal points.
3. **Mirrored selfies.** Front cameras often save mirrored images. Run Procrustes without the determinant fix: if det R < 0 or the L/R labels are swapped, flip the photo.
4. **Capture.** Neutral expression, lips closed, eyes forward. Take frontal, both three-quarter and both profile views from 1–2 m, and keep the EXIF. Close selfies inflate the nose (Table 4).
5. **Stage the fit as shape keys** on unchanged topology: PCA → RBF → refine → silhouette. The artist can then dial each stage. Add detail on Multires above the fitted base.
6. **Vertex-group masks.** Keep eyeballs, mouth bag and teeth rigid, and give lids and lips their own constraints. The back of the head has no landmarks, so its shape comes only from the prior and the affine part.
7. **Checks after each stage:** landmark RMS (mm); per-view reprojection (px); profile-silhouette overlay (nose, chin, forehead); minimum per-vertex Jacobian determinant (folds); lip/lid interpenetration; k_eff (a prior-dominated, generic face).
8. **Common failures:**
   - Lips or lids glued together by the Euclidean warp. Fix: closed-mouth capture, or region-split warps.
   - Cones at constrained vertices. Fix: bilaplacian energy, and constraints spread over the 1-ring.
   - Jawline points treated as fixed vertices.
   - Nose and chin depth taken from frontal views only.
9. **Blender tools** (🧠, version-sensitive): the Laplacian Deform modifier and Corrective Smooth for manual fixes; Surface Deform to transfer the fit to a denser sculpt mesh; the Elastic Deform brush (regularised Kelvinlets) for nudges.

## Algorithmic implications

**Pipeline:**
1. 2D landmarks, then PnP against the mean template.
2. Bundle adjustment with priors and Huber IRLS (`face3d.solve.bundle`).
3. Umeyama alignment.
4. Optional PCA fit, annealing λ from 100× down to 1×.
5. Regularised RBF warp of the residuals.
6. Bilaplacian displacement refinement (`laplacian_deform`).
7. Optional ARAP or ASAP polish.
8. Per-view silhouette fit, with residuals along the normal.

**Contour landmarks.** Jaw and cheek outline points hit different vertices at each yaw: re-select the silhouette vertex every iteration ("landmark marching") or use point-to-line residuals. 🧠

**Engine bug, reproduced numerically here** 🧠
- **Where:** `face3d/geometry/rbf.py` adds `+smoothing·I` for φ = r ("biharmonic") and for the multiquadric.
- **Evidence:** with 60 face-scale landmarks (mm, 2 mm noise), K's restricted eigenvalues ran from −13 to −479. λ = 20–200 gave RMS landmark residuals of 10–426 mm and up to 10⁴× the bending energy of exact interpolation. With −λI, residual and energy stayed monotone (1.3–2.8 mm).
- **Fix:** negate λ for these kernels.
- **Missing test:** the existing test (`err_smooth > err_exact`) passes on the broken output. Add one checking that bending energy falls as λ rises.
- **Keep r as the default kernel:** 150 mm out, the non-affine displacement was ~3 mm for r against ~15 mm for r³, and r³ kept diverging further out.

**Suggested defaults** (all 🧠; d_ip = interpupillary distance in px)

| Quantity | Default |
|---|---|
| 2D σ: sharp points / soft points (brows, nasion) | 0.01–0.02·d_ip / 0.03–0.05·d_ip |
| 2D σ: contour points | 0.03·d_ip along the normal; ≥0.15·d_ip along the tangent |
| Huber c | 1.345σ (efficient) to 3σ (engine default) |
| Focal prior σ(log f) | 0.05–0.10 with EXIF; 0.35 without (engine) |
| 3D population prior | 4–8 mm per axis (engine 8 mm); also anchors the gauge |
| Symmetry pairs / midline | 1.5–2 mm / 1–1.5 mm (see anatomy/facial-asymmetry.md) |
| PCA | β ~ N(0, 1), λ = σₙ², clamp \|βₖ\| ≤ 3 as a safety only |
| RBF smoothing | λᵢ = α·σᵢ², α from 10⁻³ to 10⁻¹ in normalised units; per-landmark (K ∓ αΣ)w + Pa = y |
| Laplacian constraint weight | 10²–10⁴ after mass normalisation (engine 10³) |
| NICP stiffness α / landmark β | 50 → 20 → 5 → 2 → 0.8 → 0.5 → 0.35 → 0.2 / 5 → 2 → 0.5 → 0 (recalled menpo3d defaults) |
| LM | τ = 10⁻³ (10⁻⁶ with a good start); ‖g‖∞ < 10⁻⁸; 50–100 iterations |
| Central finite-difference step | ε^(1/3)·max(\|x\|, 1) ≈ 6·10⁻⁶ |
| Fold threshold | det J_warp > 0.2 per vertex |

**Uncertainty and solvers.** Report the per-landmark covariance (JᵀWJ)⁻¹ so the UI can flag poorly constrained depth, such as the nose and chin in frontal-only sets. Blender bundles numpy but not SciPy (🧠). CG on the bilaplacian converges slowly because its conditioning grows like h⁻⁴. Warm-start it from the RBF result, or use a reduced basis (`face3d.mesh.reduced`).

## Disagreements, myths & open questions

- ↔️ **Closed-form or iterative Procrustes?** Both, depending on the case. Unweighted and scalar-weighted problems are closed-form [1]; two-sided or anisotropic weighting [2] and GPA [2][4] iterate.
- ↔️ **Which kernel for 3D TPS: r² ln r [6] or r [23]?** Dimension decides: r is the 3D biharmonic kernel. Codebases still mix all three kernels.
- ↔️ **ARAP or biharmonic?** ARAP keeps feature shape but resists proportion change and spikes [13]. Biharmonic is smooth but not rotation-aware. No face comparison exists in this library.
- ↔️ **How strong should the prior be?** Too strong gives a generic face; too weak passes detector noise through. Its effect on likeness is unmeasured here.
- **Myths:**
  - "More landmarks means more accuracy." Dense or contour points are correlated, so inflate their σ.
  - "Procrustes scale is true size." It is only relative.
  - "LM beats Gauss–Newton." LM is damped Gauss–Newton.
- **Open questions:**
  - the 2025 smooth-ARAP formulation [13];
  - head-to-head errors of RBF + Laplacian against NICP and 3DMM on photo-only input;
  - landmark-detector error distributions, which decide between Huber and Cauchy;
  - whether 2025–2026 learned dense correspondence obsoletes sparse landmarks.

## Sources

1. [1] Procrustes Analysis with Deformations: A Closed-Form Solution by Eigenvalue Decomposition — https://arxiv.org/pdf/2206.14528 — paper — 2022
2. [2] Springer s12518-020-00306-7 (weighted similarity transformation) — https://link.springer.com/article/10.1007/s12518-020-00306-7 — paper — 2020
3. [3] NIST J. Res. 124.028 (Procrustes/similarity) — https://nvlpubs.nist.gov/nistpubs/jres/124/jres.124.028.pdf — official docs — 2019
4. [4] NIST Bernal notes on Procrustes — https://math.nist.gov/~JBernal/kujustf.pdf — official docs — n.d.
5. [5] MPI Virtual Humans 2023, Lecture 03.2: Procrustes — https://virtualhumans.mpi-inf.mpg.de/VH23/slides/pdf/Lecture_03_2_Procrustes.pdf — slides — 2023
6. [6] Bookstein, Principal Warps: Thin-Plate Splines and the Decomposition of Deformations — https://members.cbio.mines-paristech.fr/~jvert/svn/bibli/local/Bookstein1989Principal.pdf — paper — 1989
7. [7] BrainMorph — https://arxiv.org/pdf/2405.14019 — paper — 2024
8. [8] CABLD — https://arxiv.org/pdf/2411.17845 — paper — 2024
9. [9] Sorkine & Alexa, As-Rigid-As-Possible Surface Modeling — https://diglib.eg.org/handle/10.2312/SGP.SGP07.109-116 — paper — 2007
10. [10] Same paper, full record — https://diglib.eg.org/items/e0b21a71-350e-41e7-a586-3bfa526ed21c/full — paper record — 2007
11. [11] Jacobson et al. 2012 ("jacobson12fast"; title unconfirmed) — https://users.cs.utah.edu/~ladislav/jacobson12fast/jacobson12fast.pdf — paper — 2012
12. [12] Implementing ARAP Shape Manipulation and Surface Flattening (JGT) — https://www-ui.is.s.u-tokyo.ac.jp/~takeo/papers/takeo_jgt09_arapFlattening.pdf — paper — 2009
13. [13] arXiv 2501.10335 (smooth/higher-order ARAP, per summary) — https://arxiv.org/html/2501.10335v1 — paper — 2025
14. [14] Amberg, Romdhani, Vetter, Optimal Step Nonrigid ICP Algorithms for Surface Registration — https://shapemodelling.cs.unibas.ch/gravis-literature/publications/2007/CVPR07_Amberg.pdf — paper — 2007
15. [15] Statistical non-rigid ICP (ibug) — https://ibug.doc.ic.ac.uk/media/uploads/documents/statistical_non_rigid_icp.pdf — paper — n.d.
16. [16] Densely tracking sequences of 3D face scans — https://arxiv.org/pdf/1709.04295 — paper — 2017
17. [17] arXiv 2003.08583 (face capture, annealed weights) — https://arxiv.org/pdf/2003.08583 — paper — 2020
18. [18] Botsch & Sorkine, linear variational mesh deformation survey — https://cg.cs.tu-dortmund.de/publications/2008-survey.pdf — paper — 2008
19. [19] libigl Python tutorial ch. 3 (biharmonic deformation) — https://libigl.github.io/libigl-python-bindings/tut-chapter3 — docs — n.d.
20. [20] Jacobson et al., Bounded Biharmonic Weights — https://homes.cs.washington.edu/~jovan/papers/jacobson-2011-bbw.pdf — paper — 2011
21. [21] Sorkine, Laplacian Mesh Processing — https://www.cs.princeton.edu/courses/archive/fall10/cos526/papers/sorkine05.pdf — paper — 2005
22. [22] A Revisit of Shape Editing Techniques — https://arxiv.org/pdf/2103.01694 — paper — 2021
23. [23] USPTO patent 9330206 (U(r) = r, 3D) — https://image-ppubs.uspto.gov/dirsearch-public/print/downloadPdf/9330206 — patent — n.d.
24. [24] Polyharmonic spline (power kernel r^β, CPD order ⌈β/2⌉) — https://Www.Wikipedia.org/wiki/Polyharmonic_spline — reference — n.d.
25. [25] Madsen, Nielsen & Tingleff, Methods for Non-Linear Least Squares Problems, 2nd ed. — https://www2.imm.dtu.dk/pubdb/pubs/3215-full.html — official docs — 2004
26. [26] GSL multifit_nlinear nielsen.c (Nielsen damping update) — https://git.stg.centos.org/source-git/gsl/blob/2d5f50cfd2a1fdeaae06be7e1dbdbf009ee5897e/f/multifit_nlinear/nielsen.c — source code — n.d.
27. [27] robustbase psi functions vignette (Huber k=1.345, Tukey k=4.685 for 95% efficiency) — https://mirror.linux.duke.edu/pub/cran/web/packages/robustbase/vignettes/psi_functions.pdf — docs — n.d.

**Further reading (by name, not yet linked):** Umeyama, IEEE TPAMI 1991; Horn, JOSA A 1987 (quaternions); Gower 1975 (GPA); Dryden & Mardia, *Statistical Shape Analysis*; Duchon 1977; Wahba, *Spline Models for Observational Data*; Carr et al., SIGGRAPH 2001 (RBF surfaces); Sorkine et al., "Laplacian Surface Editing", 2004; Botsch et al., *Polygon Mesh Processing*; Sharp & Crane 2020 (nonmanifold Laplacian); Finnendahl, Schwartz & Alexa, "ARAP Revisited"; Blanz & Vetter 1999; Li et al. 2017 (FLAME); Zhu et al., CVPR 2015 (landmark marching); Madsen, Nielsen & Tingleff 2004; Triggs et al. 2000 (bundle adjustment); Huber, *Robust Statistics*; Barron, CVPR 2019; Yang et al. 2020 (GNC); de Goes & James 2017 (Kelvinlets).

## Verification log (2026-11-20)

- **3D kernel r, order 1, sign and K − λI rule** — unconfirmed. Search results [24] support CPD order ⌈β/2⌉ (order 1 for r) but no source states the sign (−1)^⌈β/2⌉ or the K − λI smoothing form. Kept 🧠. https://Www.Wikipedia.org/wiki/Polyharmonic_spline
- **Nielsen LM damping update, τ 1e-6 to 1e-3** — confirmed for the update rule (μ·max(1/3, 1−(2ρ−1)³), ν=2) via the booklet record and the GSL implementation; τ range unconfirmed. Badge 📄. https://www2.imm.dtu.dk/pubdb/pubs/3215-full.html ; https://git.stg.centos.org/source-git/gsl/blob/2d5f50cfd2a1fdeaae06be7e1dbdbf009ee5897e/f/multifit_nlinear/nielsen.c
- **95% efficiency constants** — Huber 1.345 and Tukey 4.685 confirmed (📄); Cauchy 2.385 and σ = 1.4826·MAD unconfirmed (🧠). https://mirror.linux.duke.edu/pub/cran/web/packages/robustbase/vignettes/psi_functions.pdf
- **Blender ships numpy but not SciPy (4.x/5.x)** — unconfirmed for current releases. Only 2019-era forum and tracker posts say SciPy is not bundled; no current official statement found. Kept 🧠. https://devtalk.blender.org/t/can-3rd-party-modules-ex-scipy-be-installed-when-an-add-on-is-installed/9709
