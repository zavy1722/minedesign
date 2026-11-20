# Public 3D face scan datasets

> Public 3D face data comes in four families: static identity scans (Headspace, FRGC, Bosphorus, FaceBase, NoW), static expression sets (FaceScape, FaceWarehouse, BU-3DFE), 4D sequences (BU-4DFE, BP4D, D3DFACS, CoMA, VOCASET, FaMoS, 4DFAB) and calibrated multi-view video (Multiface, NeRSemble, RenderMe-360, Ava-256). Nearly all are non-commercial and research-only, released after an application that usually needs an institutional signatory, and the scans behind the big morphable models (CAESAR for FLAME, MeIn3D for LSFM) are not freely available. Populations are narrow: FaceScape is mostly Chinese, Headspace mostly white British, the MPI and TUM sets mostly young Europeans, and only Headspace shows the cranium, because subjects wore tight caps. In this project, datasets serve local validation and, where the licence allows, prior estimation; they are never shipped, and the add-on reads them through user-supplied adapters that declare units, axes, landmark convention and licence. No harvest or earlier draft existed for this topic, so every item is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 2 📄 / 39 🧠 / 41 ↔️ — 🧠 items are queued for web verification; 6 claim groups checked on 2026-11-20 across two passes (see Verification logs); pass 2 changed no badges because the confirmed parts sat on facts already marked ↔️ or only partly settled the claim.

## Key facts

Counts, capture and licence per dataset are in Table 1; these bullets cover what the table cannot.

- **Headspace is the only cranium source.** University of York with Alder Hey Children's Hospital, Liverpool. Subjects wore tight caps on a 3dMD head rig, so the vault survives; metadata covers age, sex, self-declared ethnicity, glasses and beard. 1,519 is the full-set count (3dMD head system, tight latex caps) and 1,212 the LYHM subset 📄 [3].
- **REALY ground truth is ≈100 Headspace subjects**, so priors built with Headspace (LYHM, HIFI3D++) leak into REALY scores (lib: `benchmarks-metrics.md`). 🧠
- **Model scans are not public.** LSFM (MeIn3D, ≈9,663 scans) and BFM (200) release only models. CAESAR, whose ≈3,800 heads trained FLAME identity, is sold, and its head sampling is coarse. 🧠
- **FaceScape is the richest static set.** It ships a topologically uniform base mesh, 4K displacement and texture maps, a bilinear model, landmark indices and calibrated multi-view images for part of the set. Its TPAMI benchmark bins test images by yaw and focal length, which no other benchmark does. 🧠
- **FaceWarehouse is coarse.** Kinect v1 gives smooth surfaces with no pores; its value is the per-person FACS-like blendshapes and bilinear tensor. 🧠
- **Raw vs registered 4D.** BU-4DFE and BP4D are raw per-frame meshes with no correspondence. CoMA, VOCASET and FaMoS are registered to FLAME (5,023 vertices, metres). D3DFACS fed FLAME's expression space. 🧠 FaMoS (released with TEMPEH) is the largest registered 4D set and adds calibrated images. ↔️
- **Multiface is the open one.** Under CC BY-NC 4.0 [2] with download scripts, it is the only calibrated set with tracked meshes an unaffiliated developer can get without applying. 🧠
- **Multi-view video ≠ scans.** NeRSemble, RenderMe-360 and Ava-256 give calibrated images and fitted FLAME or tracked meshes, not scanner ground truth. 🧠
- **AFLW2000-3D and 300W-LP are not scans.** Their "3D" is a 3DMM fitted to 2D landmarks: fine for landmark tests, useless for millimetres. 🧠
- **Recurring scan artefacts.** These show up on every scanner:
  - spikes or holes at hair, brows and lashes;
  - specular holes at the cornea;
  - no inner mouth;
  - occluded ears;
  - holes under the chin and in the nostrils;
  - ridges where camera pods meet;
  - lighting baked into textures. 🧠
- **Typical licence terms.** Non-commercial research only, no redistribution, signed by an academic institution: FaceScape, Headspace, BU-3DFE/4DFE/BP4D, FaceWarehouse, NeRSemble, D3DFACS (FaceScape [1] and Headspace [3] checked: non-commercial, signed agreement; Headspace needs a university employee's signature). 📄 Students usually need a supervisor's signature ↔️.
- **MPI sets.** CoMA, VOCASET, FaMoS, NoW and FLAME need a website account and click-through non-commercial licence; individuals can register. Commercial FLAME use is negotiated separately. ↔️
- **Derived works are covered.** Most licences extend to trained models and PCA bases, so a prior learned from the data inherits non-commercial terms. ↔️
- **Use restrictions.** FaceScape lets only a listed subset of subjects appear in publications, and agreements forbid re-identification. ↔️ Binghamton has charged fees for some sets (BP4D+). ↔️

## Numbers & reference tables

**Table 1. Dataset catalogue** (subjects in people; volume in models, sequences or frames)

| Dataset (year) | Kind | Subjects | Volume | Capture | Registered topology | Population, ages | Licence / access | Badge |
|---|---|---|---|---|---|---|---|---|
| Headspace (≈2015–17) | static head + cranium | ≈1,212–1,519 | 1 neutral per subject | 3dMD head, tight cap | raw; LYHM registrations | mostly white British, child–elderly | academic, signed agreement (York) | ↔️ |
| FaceBase 3D Facial Norms | static face | ≈2,400 | 1 per subject + measurements | 3dMDface | landmarks only | European ancestry, ≈3–40 y | controlled DUA; norms public | ↔️ |
| FRGC v2.0 (2005) | static face | 466 | 4,007 scans | Minolta Vivid laser, 640×480 range | none | US, mostly young | research licence | 🧠 |
| Bosphorus (2008) | static, pose/occlusion/AU | 105 | ≈4,666 scans | structured light | 24 landmarks | mostly Turkish/European | research licence | 🧠 |
| CAESAR (2002) | whole body | ≈4,400 | 1 per subject | Cyberware laser | none | US, NL, IT adults 18–65 | purchased | 🧠 |
| FaceScape (2020) | static expressions | 938 (CVPR paper [5]; 847 in the public release [1]) | 20 each = 18,760 [5] | DSLR array ≈60–70 cams (68 per paper [5]) | uniform base mesh + 4K displacement | mostly Chinese, ≈16–70 y [5] | NC research, application | ↔️ |
| FaceWarehouse (2014) | static expressions | 150 | 20 each = 3,000 | Kinect v1 RGB-D | 11,510 verts, 74 lm | mixed, 7–80 y | NC research, emailed agreement | 🧠 |
| BU-3DFE (2006) | static expressions | 100 (≈56 F/44 M) | 25 each = 2,500 | 3dMD | raw, 83 landmarks | mixed, White majority, 18–70 y | research agreement, Binghamton | 🧠 |
| BU-4DFE (2008) | 4D posed | 101 (≈58 F/43 M) | 606 seq ≈100 frames, 25 fps | Di3D | raw, ≈35k verts per frame | mixed, 18–45 y | research agreement, Binghamton | 🧠 |
| BP4D-Spontaneous (2014) | 4D spontaneous, AU-coded | 41 | 8 tasks each | Di3D | raw | 18–29 y | research agreement; BP4D+ (≈140) fee ↔️ | 🧠 |
| D3DFACS (2011) | 4D FACS AUs | 10 | ≈519 AU sequences, 60 fps | 3dMD dynamic | raw (FLAME fits exist ↔️) | small, European | academic request | ↔️ |
| CoMA (2018) | 4D extreme expressions | 12 | 12 seq each, 20,466 meshes | 3dMD 60 fps | FLAME 5,023 verts | European adults | MPI NC account | 🧠 |
| VOCASET (2019) | 4D speech | 12 | 480 seq, 60 fps | 3dMD | FLAME | European adults | MPI NC account | 🧠 |
| FaMoS (2023) | 4D expressions, head rotations | 95 [6] | 28 seq each, ≈600k frames [6] | 3dMD multi-view 60 fps | FLAME + calibrated images | mostly European | MPI NC account | ↔️ |
| 4DFAB (2018) | 4D, 4 sessions over ≈5 y | 180 | >1.8 M meshes | DI4D | raw | mixed | NC, Imperial | ↔️ |
| Multiface (2022) | multi-view video | 13 | ≈40 (v1) / 150–160 (v2) cams (paper says 150, GitHub README says 160) [4], 2048×1334, 30 fps | Mugsy domes | tracked meshes + UV textures | Meta volunteers | CC BY-NC 4.0, open download | ↔️ |
| NeRSemble (2023) | multi-view video | >220 | 16 cams [7], ≈7.1 MP, ≈73 fps, >4,700 seq | machine-vision rig | FLAME tracking (later releases) | mostly young European | NC, EULA application [7] | ↔️ |
| RenderMe-360 (2023) | multi-view video | ≈500 | 60 cams, ≈2448×2048 | dome | FLAME fits | Asia-recruited ↔️ | NC application | ↔️ |
| Ava-256 (2024) | multi-view + headset | 256 | dome ≈80 cams ↔️ | Codec Avatar Studio | tracked | varied | CC BY-NC-type ↔️ | ↔️ |
| NoW (2019) | benchmark | 100 | 2,054 images | 3dMD neutral scans | raw, 7 lm | Germany-recruited | MPI NC account | 🧠 |
| Florence/MICC (2011) | benchmark | 53 | scans + video | 3dMD | raw | Italian | research | 🧠 |

**Table 2. Noise floor of the ground truth** (mm, one standard deviation, typical adult face at the working distance)

| Capture | Surface noise σ | Landmark repeatability | Notes | Badge |
|---|---|---|---|---|
| 3dMD / Di3D stereophotogrammetry | ≈0.2–0.5 | ≈0.5–1.5 (well-defined points); ≈2–4 (gonion, pogonion, tragion) | pod seams; hair, lashes | ↔️ |
| Dense DSLR multi-view stereo (FaceScape) | ≈0.1–0.4 | as above | displacement maps hold sub-mm detail | ↔️ |
| Structured-light / laser line (Minolta, Bosphorus) | ≈0.2–0.5 static | ≈1–2 | motion during sweep | ↔️ |
| Kinect v1 RGB-D (FaceWarehouse) | ≈1–4 | ≈2–3 | grows with distance squared | 🧠 |
| Whole-body laser (CAESAR) | several mm sampling | ≈2–5 | holes under chin, at hair | ↔️ |
| Multi-view video fits (NeRSemble, RenderMe) | method-dependent, ≈1–2 | n/a | GT is a reconstruction, not a scan | ↔️ |

**Table 3. Loader facts** (verify on the files themselves)

| Source | Units | Up axis | Topology | Badge |
|---|---|---|---|---|
| FLAME family (CoMA, VOCASET, FaMoS) | metres | +Y, face toward +Z | 5,023 verts | 🧠 |
| 3dMD / Di3D exports (Headspace, BU, NoW scans) | mm | varies by rig | raw, 50k–200k+ verts | ↔️ |
| FaceScape | check: mm-scale expected | check | own uniform mesh ≈26k verts | ↔️ |
| BFM-era files | µm or mm depending on version | +Y | 53,490 (2009) | ↔️ |
| Blender | 1 unit = 1 m by default | +Z, front view looks toward +Y | n/a | 🧠 |

## Applying this to photo→3D face sculpting in Blender

- **What datasets are for here.** Testing the solver and calibrating expectations, not sculpting assets: a likeness of one consenting person needs only their photos and a permissively licensed template. 🧠
- **Access reality.** Unaffiliated artists usually cannot sign FaceScape, Headspace or Binghamton agreements, but can download Multiface and register for the MPI sets. Whether a personal art project counts as "non-commercial research" is unclear; assume not until the licence says so. ↔️
- **Validation recipe.** Take a subject with calibrated views and a mesh (FaceScape multi-view, FaMoS or Multiface). Feed the engine 3, 5 and 9 views. Align the result with 7 landmarks plus similarity (NoW style), then ICP. Report scan-to-mesh error per region: nose, mouth, eyes, forehead, cheeks, jaw. 🧠
  - Rough targets: 3DMM fit from ≥5 calibrated views ≈1–1.5 mm mean; photogrammetry ≈0.3–0.7 mm; any number below ≈1.5× the scan σ in Table 2 is noise. ↔️
- **Importing scans.**
  - Blender's OBJ importer defaults (forward −Z, up Y) turn Y-up files into Z-up. Then check scale with the outer-canthus distance (ex–ex, adult ≈85–100 mm): a reading of ≈0.09 means metres and ≈90 means millimetres; set it so 1 Blender unit is 1 m. 🧠
  - Clean up: Merge by Distance at about 0.01 mm, and delete loose islands (floaters, lash spikes). Keep holes open: filled holes look like data. 🧠
- **Using a scan as reference.** Decimate to ≈300k–500k faces, give it a semi-transparent material or show it as wireframe in front, and use it as a Shrinkwrap target or a visual overlay, not as the sculpt base. Retopologise or wrap to the add-on's quad template. 🧠
- **What to measure against a scan.** Compare these linear distances: ex–ex, en–en, al–al (nose width), ch–ch (mouth width), n–sn, sn–gn, zy–zy, go–go. Also compare the mid-sagittal profile curve. Eye, nose and mouth widths off by more than ≈1–2 mm are visible to anyone who knows the face (lib: `likeness-mistakes.md`, `anthropometric-norms.md`). ↔️
- **Common traps.**
  - Hair. Headspace caps still add a few millimetres over the scalp, and other datasets lose the cranium entirely; take back-of-head shape from LYHM/UHM statistics or head length and breadth norms. ↔️
  - Eyebrows and lashes inflate the brow ridge and lids; sculpt the brow from bone landmarks, not from scan surface. 🧠
  - Neutral is not neutral: lips parted, brows raised. FaceScape's and FaceWarehouse's "neutral" are reference poses, not relaxed faces (lib: `expression-neutralization.md`). ↔️
  - Baked lighting and specular in dataset textures; never use them as albedo. 🧠
  - FaceWarehouse geometry is too smooth for detail work; use FaceScape displacement maps only to judge how deep pores and wrinkles run (sub-millimetre), not to transfer detail. 🧠
- **Population.** Children appear only in Headspace, FaceWarehouse (7+), FaceBase (3+) and the LSFM model; darker skin is sparse everywhere. For under-represented subjects, rely on more views, not a stronger prior. ↔️

## Algorithmic implications

- **Dataset adapter schema.** Every source declares `units`, `up_axis`, `forward_axis`, `handedness`, `topology_id`, `landmark_convention` (68 iBUG, 74 FaceWarehouse, 83 BU-3DFE, 7 NoW, …), `licence_id`, `commercial_ok`, `redistribution_ok`, `population_tags`, `capture_tech`. The engine refuses to export a prior or fitted basis whose provenance includes `commercial_ok=false` unless the user switches to research mode. 🧠
- **Unit sanity check.** Compute ex–ex (or en–en, ≈28–36 mm) on the loaded landmarks. Snap the scale factor to the nearest of {10⁻⁶, 10⁻³, 10⁻², 1, 10³}, and abort if it lands outside the 0.6–1.4× band of the expected value. 🧠
- **Ground-truth noise model.** Set σ_gt per `capture_tech` from Table 2. In benchmarks, report error together with σ_gt. In fitting to scans, use a robust (Huber or Geman-McClure) residual with scale ≈2·σ_gt. 🧠
- **Region weights when fitting to scans** (defaults, tune on held-out data) ↔️:
  - skin core (cheeks, forehead, nose dorsum, chin): 1.0;
  - lips: 0.7 (vermilion seam 0.3);
  - eyebrows: 0.3;
  - lids and lashes: 0.2;
  - ears: 0.2;
  - inner mouth, eyeballs, nostrils: 0;
  - scalp: 0 everywhere except Headspace, where it gets 0.5 with an outward cap/hair offset of 1–5 mm treated as one-sided.
- **Landmark prior σ.** For Procrustes-aligned adults (scale removed), ≈2–4 mm in-plane per landmark and ≈3–6 mm in depth for pronasale, pogonion, glabella and gonion. Inner canthi and alae are tighter, ≈1.5–3 mm. Derive these from licensed data where you can; otherwise sample them from published anthropometric means and SDs (lib: `anthropometric-norms.md`). ↔️
- **Population mismatch.** Use a mixture prior with components per training population, chosen by fit likelihood rather than user-declared ethnicity, with a manual override. Widen σ by 1.3–1.5× when no component fits (a guess, consistent with `awesome-lists-resources.md`). ↔️
- **Leakage guard.** Tag every subject ID used in any prior. The evaluator refuses to report on overlapping subjects, for example REALY (Headspace) against a HIFI3D++- or LYHM-based prior. 🧠
- **Expression checks.** Train small detectors for lip seal, brow raise and smile on the shape deltas of FaceScape or FaceWarehouse expressions where licensed, or on FLAME expression directions. Flag non-neutral input photos before fitting identity. 🧠
- **Time.** Store each loader's licence-text hash and download date; datasets get withdrawn or relicensed. 🧠

## Disagreements, myths & open questions

- **Myth: "a scan is ground truth."** Scans carry 0.2–4 mm noise depending on capture, hair artefacts and a non-neutral "neutral". Errors under ≈0.5 mm against 3dMD ground truth cannot be resolved. ↔️
- **Myth: "a large N means representative."** LSFM is ≈80 % White, CAESAR has adults only, FaceScape is mostly Chinese. 🧠
- **Myth: AFLW2000-3D or 300W-LP gives 3D accuracy.** Both are fitted pseudo-ground truth. 🧠
- **Contested: whether derived models escape the licence.** Most agreements say no; lawyers differ on whether PCA statistics are copyrightable (lib: `ethics/licences-tos.md`). ↔️
- **Contested: whether multi-view video sets replace scans** (NeRSemble, RenderMe-360, Ava-256). Their geometry is reconstructed, so millimetre claims on them are method-dependent. ↔️
- **Open:**
  - what is still distributed in late 2026 (D3DFACS hosting, Binghamton fees, FaceScape server, Headspace terms);
  - whether a permissive (CC BY) metric head-scan set now exists;
  - whether synthetic heads can replace scans in priors;
  - exact FaMoS, Multiface, NeRSemble and RenderMe-360 counts.

## Sources

Numbered sources added in the 2026-11-20 verification pass:

1. FaceScape project page and licence terms: https://nju-3dv.github.io/projects/FaceScape
2. Multiface README (fork mirroring facebookresearch/multiface; CC BY-NC 4.0): https://github.com/jackzhousz/multiface
3. Liverpool-York Head Model / Headspace page, University of York: https://www-users.york.ac.uk/~np7/research/LYHM
4. Wuu et al., Multiface, arXiv:2207.11243: https://arxiv.org/abs/2207.11243
5. Yang et al., FaceScape, arXiv:2003.13989: https://arxiv.org/abs/2003.13989
6. FaMoS dataset record (TIB): https://service.tib.eu/ldmservice/dataset/bibtex/famos-dataset
7. The NeRSemble 3D Head Avatar Benchmark (TUM): https://kaldir.vc.cit.tum.de/nersemble_benchmark/

No earlier harvest existed, so all other items remain unverified.

**Further reading (by name, not yet linked)**
- Yang et al., FaceScape, CVPR 2020; Zhu et al., FaceScape benchmark, IEEE TPAMI
- Dai, Pears, Smith & Duncan, LYHM/Headspace, ICCV 2017
- Cao et al., FaceWarehouse, IEEE TVCG 2014
- Yin et al., BU-3DFE, FG 2006; Yin et al., BU-4DFE, FG 2008
- Zhang et al., BP4D-Spontaneous, IVC 2014; BP4D+, CVPR 2016
- Cosker, Krumhuber & Hilton, D3DFACS, ICCV 2011
- Ranjan et al., CoMA, ECCV 2018
- Cudeiro et al., VOCA/VOCASET, CVPR 2019
- Bolkart, Li & Black, TEMPEH/FaMoS, CVPR 2023
- Li et al., FLAME, SIGGRAPH Asia 2017
- Wuu et al., Multiface, 2022
- Kirschstein et al., NeRSemble, ACM TOG 2023
- Pan et al., RenderMe-360, NeurIPS 2023
- Martinez et al., Codec Avatar Studio (Ava-256), NeurIPS 2024
- Cheng et al., 4DFAB, CVPR 2018
- Sanyal et al., NoW, CVPR 2019; Chai et al., REALY, ECCV 2022
- Phillips et al., FRGC, CVPR 2005; Savran et al., Bosphorus, 2008; Bagdanov et al., Florence 2D/3D, 2011
- Robinette et al., CAESAR final report, 2002
- Weinberg et al., 3D Facial Norms (FaceBase)
- Booth et al., LSFM, CVPR 2016; Paysan et al., BFM, AVSS 2009
- Farkas, Anthropometry of the Head and Face, 1994

## Verification log (2026-11-20)

- Licence terms (FaceScape, Headspace, NeRSemble, Binghamton non-commercial and signed; Multiface CC BY-NC 4.0; derived models covered): partly confirmed. FaceScape non-commercial with signed agreement [1]; Headspace non-commercial with agreement signed by a university employee [3]; Multiface CC BY-NC 4.0 [2]. NeRSemble, Binghamton and the derived-model clause: unconfirmed. FaceScape also found to have 847 subjects released versus 938 in the paper [1].
- Multiface (13 identities, 2048x1334, tracked meshes, CC BY-NC 4.0): confirmed [4][2]. Camera count contested: about 40 (v1) / 150 (v2) in the paper, 40-160 in the README. "Download without application" unconfirmed.
- Headspace (1,519 scans, 3dMD head, tight caps; LYHM from 1,212): confirmed [3]. "About 100 Headspace subjects in REALY" and population mix: unconfirmed.
- Noise floor (3dMD sigma 0.2-0.5 mm, landmark repeatability 0.5-1.5 mm, Kinect 1-4 mm): unconfirmed. Validation studies report mean errors mostly under 1 mm on mannequins (https://pmc.ncbi.nlm.nih.gov/articles/PMC6005204) but give no sigma figures.

## Verification log, pass 2 (2026-11-20)

- FaceScape (938 subjects x 20 expressions = 18,760 models; DSLR rig; topologically uniform; ages 16-70): confirmed [5] https://arxiv.org/abs/2003.13989. Paper states 68 DSLR cameras (30 at 8K frontal, rest 4K), consistent with the 60-70 range. Not confirmed: ~26k-vertex base mesh, 4K displacement maps in this source, calibrated multi-view subset, "mostly Chinese". Table badge stays ↔️ because of the 847-subject public release [1].
- FaMoS (95 subjects x 28 sequences, ~600k meshes, 60 fps): partly confirmed by a dataset record [6] https://service.tib.eu/ldmservice/dataset/bibtex/famos-dataset; FLAME topology, TEMPEH link and "largest registered set" unconfirmed. Badge stays ↔️.
- NeRSemble (16 cameras, FLAME tracking, access by request form): partly confirmed [7] https://kaldir.vc.cit.tum.de/nersemble_benchmark/. Not confirmed: >220 subjects, ~7.1 MP, ~73 fps, >4,700 sequences, EULA wording. Badge stays ↔️.
