# Separating identity from expression

> A 3D morphable model (3DMM) writes a face as mean + identity basis·β + expression basis·ψ (plus an articulated jaw in FLAME); the split is a statistical convention learned from different data, not anatomy, and the two subspaces overlap. From one photo, a slight smile, parted jaw or squint is partly absorbed as a wider mouth, longer chin or smaller eyes. Fitting several photos with one shared β and a per-photo ψ separates the *varying* part of expression, but a *constant* offset (a habitual smile in every photo) is separable only if one photo is tagged neutral and a prior pins its ψ near 0. The recipe: capture a relaxed neutral, trust only expression-stable regions (nasal dorsum, forehead, orbital rims, ears) on expressive photos, fit expression per photo, hand off ψ = 0 with the jaw closed, and use expressive photos for teeth, rig shapes and extra angles, never for lips or lids.
>
> Evidence status: 0 ✅ / 0 📄 / 49 🧠 / 13 ↔️ — 🧠 items are queued for web verification.

*No web harvest existed for this topic, so nothing here is web-sourced. Where a sibling note in this library cites a source for the same claim, it is named in backticks.*

## Key facts

**How models encode the split**
- **Blanz & Vetter (1999)** built PCA from 200 *neutral* scans, with no expression. BFM 2009 is also neutral-only, so expression must be added from another dataset. 🧠
- **The additive BFM pipelines** take expression deltas from FaceWarehouse. Each delta is computed against that subject's own neutral scan, then PCA is run on the deltas. FaceWarehouse has about 150 subjects with about 20 expressions each. Deep3DFaceRecon uses 80 identity and 64 expression components; 3DDFA_V2 uses 40 and 10. 🧠 (component counts also in `single-image-regression.md`)
- **FLAME** has 300 shape (β) and 100 expression (ψ) components, roughly in SD units (`multi-view-fitting.md`). Identity PCA comes from ≈3,800 CAESAR scans; expression PCA from 4D sequences (D3DFACS plus own captures) *after* removing identity, jaw/neck/eye rotation (linear blend skinning) and pose correctives, so jaw opening is articulation (θ_jaw), not ψ. 🧠
- **Multilinear models** (Vlasic et al. 2005; FaceWarehouse bilinear tensor) make expression depend on identity (a wide mouth smiles wider). Additive models apply one delta to everyone, so person-specific expression shape leaks into β or stays as residual; how much that matters is ↔️.
- **Implicit/neural heads** (ImFace, NPHM, MonoNPHM) keep identity in a canonical neutral space plus an expression deformation field; they neutralise by setting the expression code to 0 and inherit the same zero-point ambiguity. 🧠
- **FACS blendshape rigs** (ARKit/MediaPipe 52) are semantic, non-orthogonal, bounded to [0, 1]: good for neutralising by subtraction, not identity models. 🧠 (sourced in `anatomy/facs-expressions.md`)

**Why the problem is ill-posed**
- **Confounded directions** vary both between people and between expressions: mouth width, vermilion height, lower-face height (jaw), palpebral aperture, brow height, cheek fullness, nasolabial depth. 🧠
- **ψ = 0 means "what training subjects did when told *neutral*."** A consistent resting expression is then coded as identity: down-turned corners, frontalis tone, or apart lips. That is *correct* for likeness if it is habitual and wrong if it was momentary. 🧠
- **Gauge freedom (derivation).** With shared β and per-view ψ_v, the change β → β+Δ, ψ_v → ψ_v − c (for every view) leaves the geometry unchanged wherever U_id·Δ = U_exp·c. Only priors break the tie. A neutral-tagged photo with a tight ψ prior is the anchor. 🧠
- **How learned regressors fight leakage** 🧠: RingNet's shape-consistency loss (and NoW, which scores expression images against neutral scans); DECA's detail-consistency loss, which swaps person-specific detail codes between same-person photos and conditions wrinkles on ψ and jaw; EMOCA's emotion-consistency loss on top of DECA's frozen identity encoder; MICA's neutral-only output from ArcFace features (expression-robust per its authors; sourced in `identity-embeddings.md`); SMIRK's augmented-expression cycle loss.
- **ArcFace-type embeddings are expression-*robust*, not -invariant.** Broad smiles and open mouths lower genuine-pair similarity. Do not score likeness on an expressive photo against a neutral render. 🧠

**Anatomy of a usable neutral**
- **Definition:** no active action unit (AU); mandible at physiological rest (2–4 mm interincisal freeway space); lips lightly touching without mentalis (AU17) or pressing (AU24); primary gaze; upper lid margin ≈1–2 mm below the upper limbus (MRD1 ≈ 3.5–5 mm). 🧠
- **Incisor display at rest** is about 1–4 mm. Vig & Brundo give means of about 1.9 mm for men and 3.4 mm for women, falling with age. If display is repeatable across sessions it is identity (short lip or vertical maxillary excess), not expression. 🧠
- **Resting lip gap.** A gap of more than about 3–4 mm (lip incompetence) is identity. Forcing the lips shut recruits mentalis, which gives a dimpled "golf-ball" chin and a flattened labiomental fold. That chin is an *expression*. Exact threshold ↔️.
- **Expression-stable regions:** nasal bridge and dorsum, forehead above the brows (except under AU1/2/4), orbital rims, zygion, ears, cranial vault. Expression-robust 3D face recognition is built on them (Chang–Bowyer–Flynn nose regions; Bronstein et al. isometric expressions). 🧠
- **Mobile regions:** lips and commissures, malar soft tissue, nasolabial fold, lower lid, brows, chin pad, everything jaw-dependent. 🧠
- **Isometry.** Skin deformation under expression is roughly isometric (geodesics preserved) except at the mouth opening and at fold formation. This justifies ARAP-style neutralising outside the lips. ↔️ (an approximation; skin also slides over fat pads)
- **Wrinkles.** Only lines visible in a relaxed neutral are identity (static lines). Dynamic lines belong to expression shapes or detail maps. 🧠

**Using several expressions**
- **Shared identity with per-frame expression is the standard** in video trackers (metrical-tracker, VHAP; `multi-view-fitting.md`), personalised-rig work (Weise 2011, Bouaziz 2013, Ichim 2015, Garrido 2016) and Deng et al. 2019's confidence-weighted image-set aggregation. 🧠
- **Benefit:** averages per-photo noise, adds viewing directions; smiles reveal teeth, dental arch and smile line. **Cost:** unmodelled expressions pull β toward the *mean expression of the set*. 🧠
- **No quantified gain** of expression-diverse over neutral-only photo sets exists in this library. 🧠 (open)

## Numbers & reference tables

**Table 1 — Model bases** (component counts; identity data / expression data).

| Model | Identity | Expression | Jaw | Data (identity / expression) | Form | Status |
|---|---|---|---|---|---|---|
| BFM 2009 | 199 | none | – | 200 neutral adults / – | linear | 🧠 |
| BFM + FaceWarehouse (Deep3D) | 80 | 64 | in ψ | as above / ≈150 subj × ≈20 expr | additive | 🧠 |
| 3DDFA_V2 | 40 | 10 | in ψ | as above | additive | 🧠 |
| FLAME 2017/2020 | 300 | 100 | joint + LBS | ≈3,800 CAESAR / 4D (D3DFACS + own) | additive + articulated | 🧠 |
| FaceWarehouse bilinear | ≈50 | ≈25–47 | in tensor | 150 subj / 150 subj | multiplicative | ↔️ |

**Table 2 — Rest ("neutral") reference values.** Population: adults, mostly Western samples.

| Quantity | Typical | Units | Note | Status |
|---|---|---|---|---|
| Interincisal freeway space at rest | 2–4 | mm | ≈ 1.1–2.4° of jaw rotation (Table 4) | 🧠 |
| Upper incisor display at rest | 1–4 (M ≈ 1.9, F ≈ 3.4) | mm | Vig & Brundo; falls with age | 🧠 |
| Resting interlabial gap, competent | 0–3 | mm | >3–4 mm = incompetent lips (identity) | ↔️ |
| MRD1 (lid margin to corneal light reflex) | 3.5–5 | mm | below 2 mm = ptosis or squint | 🧠 |
| Mouth width (ch–ch) at rest | 45–58 | mm | Farkas-type norms; M > F | 🧠 |
| Condyle to lower-incisor radius | ≈100 | mm | Bonwill triangle ≈ 4 in | 🧠 |

**Table 3 — How expressions bias identity measurements.** Magnitudes are order-of-magnitude expert estimates for a posed, moderate (C–D) expression. Verify before using them as priors.

| Expression (AU) | Region | Biased measurement | Typical shift | Status |
|---|---|---|---|---|
| Social smile (AU12 ± AU6) | mouth | ch–ch width | +15–30 % (≈ +8–15 mm) | ↔️ |
| AU12 | upper lip | visible vermilion height | −20–40 %; lip stretches thin | 🧠 |
| AU6 / strong AU12 | lower lid, malar | fissure height; cheek height | fissure −10–50 %; malar up ≈2–5 mm | 🧠 |
| AU12 | nose | alar base width | +1–3 mm; tip may drop | ↔️ |
| AU25/26 (lips part, jaw drop) | lower face | sn–me height, chin projection | ≈ +1.9–2.1 mm per degree at menton; chin moves back | 🧠 |
| AU1+2 | brow, forehead | brow height, forehead height | brow +3–10 mm | 🧠 |
| AU4 | glabella | inter-brow distance, brow height | brows down 2–5 mm and inward | 🧠 |
| AU18/22 (pucker, funnel) | mouth | width, lip projection | width −20–40 %; lips +5–10 mm forward | 🧠 |
| AU17 / forced lip seal | chin | soft-tissue chin, labiomental fold | fold flattens, chin pad bunches | 🧠 |
| Speech visemes | mouth, jaw | all lip landmarks | bilabials press (AU24); vowels open 5–15 mm | 🧠 |

**Table 4 — Jaw rotation to opening (mm).** Derived as chord = 2r·sin(θ/2); pure hinge only (past ≈20–25 mm the condyle also translates). Radii are 🧠, arithmetic exact.

| θ_jaw | 1° | 2° | 3° | 5° | 10° | 15° | Status |
|---|---|---|---|---|---|---|---|
| r = 100 mm (incisor) | 1.7 | 3.5 | 5.2 | 8.7 | 17.4 | 26.1 | 🧠 |
| r = 120 mm (menton) | 2.1 | 4.2 | 6.3 | 10.5 | 20.9 | 31.3 | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Brief the subject.** Say "breathe out, let your jaw hang a hair, lips just touching, look at the dot at eye level"; never "relax and smile". Shoot a burst or 5 s clip per view and pick the most relaxed frame. Repeat the frontal neutral at the start and end of the session, because tone drifts.
2. **Shoot an expression set separately** (frontal plus one 3/4): closed smile, teeth smile, jaw open ≈20 mm, brows up, brows down, pucker, squint. It feeds the rig and the teeth and gives the fitter varied, *modelled* expressions.
3. **Audit every photo before sculpting.** Run MediaPipe blendshapes (uncalibrated; `facs-expressions.md`). Against the set median, compare mouth width, stomion gap, palpebral height and brow-to-pupil distance, each divided by inter-ocular distance (IOD), plus left vs right lip corners. Flag deviations above ≈5 %.
4. **Blender layout.** `Basis` = identity (β, ψ = 0, jaw 0); one diagnostic shape key per photo (`fit_IMG_0123`) holding its fitted ψ and jaw; camera-matched photo backgrounds. Check overlays with that photo's key at 1.0, but sculpt identity only in `Basis`, and only in regions the photo can vouch for.
5. **Trust map for an expressive photo.** Trust nose bridge and dorsum, forehead, orbital rims, ears, cranial outline, and gonion if the mouth is closed; a smiling profile is fine for nasal projection. Do not trust mouth width, lip fullness, nasolabial depth, cheek volume, lower lid or chin pad.
6. **Hand-neutralise a smile when no neutral exists** (AU12 reversed): commissures down, medial and slightly forward; soften the nasolabial fold; drop the malar mass 2–4 mm; lower the lower lid 1–2 mm; restore upper vermilion height. Work with symmetry **off**, because smiles are asymmetric. Better: fit an ARKit-style 52-shape rig on the template to the photo, zero the weights and keep the residual. Label the result "estimated neutral" (fidelity ↔️).
7. **Common failures.** Averaging smiling and neutral photos gives a "slightly smug" Basis. A lips-apart profile becomes a long chin; squint photos give small eyes; forced lip seal reads as a weak chin. Dynamic crow's feet and nasolabial creases get baked into neutral detail. An asymmetric habitual smile gets mirrored.
8. **Talking footage.** Take pauses, not bilabial frames: /m b p/ press the lips (AU24) and thin the vermilion.

## Algorithmic implications

- **Per-view expression block.** `face3d/solve/bundle.py` currently solves *one* static landmark set X for all views, so any expression difference becomes reprojection residual or a biased X. Add X_v = X + D·ψ_v + J(θ_v), with X shared and ψ_v, θ_v per view beside R, t. D is a low-rank landmark-space expression basis (K ≈ 10–20), sampled from FLAME's expression basis at the landmark vertices or from a FACS delta set. J is a jaw hinge about the bicondylar axis, roughly 10–13 mm anterior to tragion. 🧠
- **Gauge anchor.** Use a soft constraint Σ_{v∈N} ψ_v / |N| ≈ 0 over neutral-tagged views N, with σ ≈ 0.1 SD. If N is empty, warn: "identity uncertain along expression-confounded directions." Do not report sub-mm mouth or lid measurements in that case.
- **Confound diagnostic.** Whiten U_id and U_exp at the landmarks (and silhouette points), orthonormalise each to Q_id and Q_exp, and take the SVD of Q_idᵀQ_exp. Singular values near 1 mark directions that only neutral capture or priors can fix. Show the artist per-measurement posterior σ ("mouth width ± x mm").
- **Do not orthogonalise expression against identity.** Doing so pushes all shared variance into β (expression leakage by construction). Keep both bases and let priors and multi-view data decide. ↔️
- **Region-aware weights.** Per landmark, σ_eff = σ_px · m(class, view-tag), applied via `ViewObs.weights` (weight = 1/m²). Multipliers m are design defaults; tune on held-out views:

| Landmark class | Examples | Neutral | Mild | Expressive | Status |
|---|---|---|---|---|---|
| Rigid | nasion, pronasale, subnasale, endocanthion, tragion, ear points | 1 | 1 | 1–1.5 | 🧠 |
| Semi-mobile | exocanthion, alare, lateral brow, gonion | 1 | 1.5–2 | 2–3 | 🧠 |
| Mobile | cheilion, labrale sup/inf, stomion, lid margins, medial brow | 1 | 3 | 5–10 or drop | 🧠 |
| Jaw-dependent | pogonion, gnathion, menton, jaw contour | 1 | 3 (1 if θ_v fitted) | drop (1 if θ_v fitted) | 🧠 |

- **Priors** (🧠; consistent with `multi-view-fitting.md` Table 5): ψ_v ~ N(0, 0.3²) on neutral-tagged views, N(0, 1) on expressive ones; eyelid parameters σ ≈ 0.2 on neutral views; β ~ N(0, 1), flag |β| > 3. θ_jaw on neutral views: mean 0 (closed), σ ≈ 1–1.5°, i.e. ≈ 2–2.6 mm at the incisors, enough to cover the freeway space; the sibling note's 2–3° is more permissive (↔️ design choice).
- **View tagging as an EM loop** (🧠, thresholds uncalibrated; log them per run). Tag from blendshape scores: neutral if all relevant scores < ≈0.1–0.15, mild if mouthSmile/jawOpen/squint scores are 0.15–0.4, otherwise expressive. Fit, re-tag by ‖ψ_v‖ (< 0.5 SD neutral, 0.5–1.5 mild, > 1.5 expressive), refit; at most 3 rounds.
- **Fitting schedule:** (1) rigid pose from rigid landmarks; (2) β from neutral views with ψ held tight; (3) add expressive views with free ψ_v, θ_v; (4) silhouette and dense terms; (5) hand off ψ = 0, θ = 0, eyelids at rest.
- **Detail** only from neutral views; otherwise split it DECA-style into static (identity) and ψ-conditioned (expression) parts. 🧠
- **Personalised correctives (optional).** After β converges, deformation-transfer the template expression shapes and add a Laplacian-regularised per-subject residual from the expression set; freeze them so later identity refits stop re-absorbing expression error. 🧠
- **Export** `Basis` plus ARKit-named shape keys (deformation transfer); store per-photo ψ_v, θ_v as JSON for provenance.

## Disagreements, myths & open questions

- **Myth: "the 3DMM separates identity and expression."** Only relative to its training data's idea of neutral; the bases overlap and a constant offset is unidentifiable. 🧠
- **Myth: "more photos of any expression always help."** Only with per-view expression and a neutral anchor; a static-shape fitter averages the expressions. ↔️
- **Additive vs identity-dependent expression models.** Multilinear and personalised rigs fit better, but they add parameters that can absorb identity. ↔️
- **2D/GAN "neutralise this smile" editors** produce plausible but *invented* neutrals that drift in identity. Never use them as a likeness reference. 🧠
- **Reversal error.** Smile reversal by linear deltas leaves mm-level error because fat pads slide and folds form non-linearly. The typical size is unquantified. ↔️
- **"Neutral" itself.** Resting tone, habitual asymmetry and lip competence vary from person to person and between sessions. FACS treats each person's own neutral as the baseline (`facs-expressions.md`). 🧠
- **Open:** how much expression-diverse sets improve identity over 3–5 neutral views (unquantified here), and which 2025–2026 regressors best resist leakage on NoW's expression subset (needs verification).

## Sources

No harvest existed for this topic; no URLs are cited. Sibling notes cite sources for overlapping claims: `reconstruction/single-image-regression.md` (DECA, MICA, SMIRK, NoW), `reconstruction/identity-embeddings.md` (MICA/ArcFace expression robustness), `reconstruction/multi-view-fitting.md` (VHAP and metrical tracking, prior table), `anatomy/facs-expressions.md` (AUs, ARKit/MediaPipe 52).

**Further reading (by name, not yet linked)**
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999; Paysan et al., BFM 2009, AVSS 2009
- Cao et al., "FaceWarehouse", IEEE TVCG 2014; Vlasic et al., "Face Transfer with Multilinear Models", SIGGRAPH 2005
- Li, Bolkart, Black, Li, Romero, "Learning a model of facial shape and expression from 4D scans" (FLAME), SIGGRAPH Asia 2017
- Egger et al., "3D Morphable Face Models — Past, Present and Future", ACM TOG 2020
- Lewis et al., "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004; Li, Weise, Pauly, "Example-Based Facial Rigging", SIGGRAPH 2010
- Weise et al., SIGGRAPH 2011; Bouaziz, Wang, Pauly, SIGGRAPH 2013; Ichim, Bouaziz, Pauly, SIGGRAPH 2015; Garrido et al., ACM TOG 2016 (personalised rigs)
- RingNet/NoW (Sanyal et al., CVPR 2019); DECA (SIGGRAPH 2021); EMOCA (CVPR 2022); MICA (ECCV 2022); SMIRK (CVPR 2024)
- Deng et al., "…From Single Image to Image Set", CVPR-W 2019; Tewari et al., "FML", CVPR 2019
- ImFace (CVPR 2022); NPHM (CVPR 2023); D3DFACS (Cosker et al., ICCV 2011)
- Bronstein, Bronstein, Kimmel, "Three-Dimensional Face Recognition", IJCV 2005; Chang, Bowyer, Flynn, TPAMI 2006
- Ekman, Friesen, Hager, FACS manual, 2002; Vig & Brundo, "The kinetics of anterior tooth display", J Prosthet Dent 1978; Farkas, Anthropometry of the Head and Face, 1994
