# Consent, privacy, law & licensing

> Area guide for artists and engineers building a likeness-accurate, sculpt-ready 3D head of a **consenting** person from photos in Blender. Three topic notes cover four legal layers: publicity and personality rights; biometric and data-protection law; digital-replica and deepfake law; and copyright, model licences and platform terms. Every claim here is drawn from the notes and their data tables. Corrections from each note's verification log (2026-11-20) are already applied. **This is not legal advice.** Most statutory figures are still 🧠 expert knowledge and must be checked against the statute before anyone relies on them.
>
> Status as of 2026-11-20.

## What this area covers

- **Whether you may make the head at all, and for which uses.** Consent tiers, written releases, minors, deceased subjects, celebrities, sexual deepfakes, post-mortem terms, digital-replica statutes, the EU AI Act. See [consent-likeness-law](./consent-likeness-law.md).
- **What the pipeline's data legally is, and how long you may keep it.** Photos, landmarks, 3DMM coefficients, fitted meshes, iris textures and recognition embeddings under BIPA, CUBI, Colorado, CCPA and GDPR. Also covers local versus cloud processing, retention, and cleaning a .blend before it leaves your machine. See [biometric-privacy](./biometric-privacy.md).
- **Whose permission you need besides the subject's.** Photographer copyright, the licence of every model, dataset and template, how the GPL applies to Blender add-ons, the Extensions platform rules, and the bans on scraping social platforms. See [licences-tos](./licences-tos.md).

**Not covered yet** (gaps listed in the notes): marketplace policies for real-person models (Sketchfab, CGTrader, Etsy, Printables); vendor terms for uploading faces (MetaHuman, generative-3D services); KeenTools' EULA; detailed coverage of Canada, Australia, Brazil, South Korea and Japan.

## How to use this area

- **Badges.** ✅ verified by at least two sources or confirmed in a verification log. 📄 single-sourced. 🧠 expert knowledge, not yet checked against a source. ↔️ contested or time-sensitive. A resolution marked **(editor)** is this README's own synthesis across notes, not a claim from any note.
- **Corrections override the text.** Each note ends with a verification log, and where the log corrects the body, the log wins. This README already uses the corrected values.
- **The engine constants are policy defaults, not statistical priors.** No value in this area carries a sigma. Tune the defaults with counsel for each jurisdiction.
- **Artists:** start with the [checklist](#artist-checklist-blender), then read the note for your use tier.
- **Engineers:** see [`../_raw/requirements_ethics.md`](../_raw/requirements_ethics.md) for the engine requirements, and the machine-readable tables in `../data/consent-likeness-law.json`, `../data/biometric-privacy.json` and `../data/licences-tos.json`.

| Note | ✅ | 📄 | 🧠 | ↔️ |
|---|---|---|---|---|
| [consent-likeness-law](./consent-likeness-law.md) | 1 | 5 | 52 | 25 |
| [biometric-privacy](./biometric-privacy.md) | 3 | 2 | 58 | 13 |
| [licences-tos](./licences-tos.md) | 0 | 3 | 65 | 29 |

None of the three notes had a web harvest behind it. Only the claims named in each verification log were source-checked; everything else is 🧠 or ↔️.

## Core principles

**Consent and likeness**

1. **Consent is necessary but not sufficient.** Three permission chains must all be clean: the subject's consent, the copyright in each photograph, and the licence of every model, dataset and template that touches the fit. A release from the subject cures none of the other two, and it does not cure tattoo copyright or a duty to disclose realistic fakes. 🧠 [consent-likeness-law](./consent-likeness-law.md), [licences-tos](./licences-tos.md)
2. **Classify the use before you capture anything.** The tiers are personal, portfolio or social, commercial, and replica (rig, expressions, voice, AI training). Each tier needs everything the one below it needs, plus more. Only the personal tier can rely on the GDPR household exemption, and BIPA has no household exemption at all. 🧠 [consent-likeness-law](./consent-likeness-law.md), [biometric-privacy](./biometric-privacy.md)
3. **The release must be written, specific to each use, and revocable.** It should list what is captured, the allowed derivatives, media, territory, duration, fee and named cloud processors. AI training is a separate opt-in that defaults to no. It sets banned uses, explains withdrawal, and handles death. Re-consent before any new use, following the SAG-AFTRA and AB 2602 logic. 🧠 [consent-likeness-law](./consent-likeness-law.md). A BIPA-grade release also meets CUBI and most GDPR explicit-consent tests. 🧠 [biometric-privacy](./biometric-privacy.md)
4. **Likeness accuracy and legal exposure rise together.** Realistic game avatars lost in court (*Keller*, *Hart*, *No Doubt*), while composites and look-alikes won (*Kirby*, *Lohan*). Stylisation is no safe harbour: in *White v. Samsung*, merely evoking a person was enough. 🧠 [consent-likeness-law](./consent-likeness-law.md)
5. **Tool makers can be liable too.** Tennessee's ELVIS Act covers distributing technology whose "primary purpose or function" is producing an individual's likeness without authorisation. 📄 Whether a general-purpose fitter falls under that is contested; a shipped celebrity preset might. ↔️ So the add-on ships no named real-person presets or sample data. 🧠 [consent-likeness-law](./consent-likeness-law.md)
6. **Minors and the deceased need someone else's signature.**
   - Minors need guardian consent plus the child's assent. Establish age by attestation, never by ML age estimation, which is itself biometric processing. 🧠
   - The deceased need estate consent for commercial work, because post-mortem rights run 10–100 years depending on jurisdiction. 🧠

   [consent-likeness-law](./consent-likeness-law.md)
7. **Never put a realistic real person's head on sexual content without specific documented consent.** It is criminal under US federal law (TAKE IT DOWN, 2025), in most US states, in the UK and in France. 🧠 [consent-likeness-law](./consent-likeness-law.md)
8. **The federal NO FAKES Act is advancing but not law.** A revised bill, S. 4591, was introduced on 20 May 2026 and cleared Senate Judiciary on 18 June 2026; no floor or House vote has been found. 📄 Its 2025 terms (70-year renewals, liability for products "primarily designed" to replicate people) were not re-checked. 🧠 [consent-likeness-law](./consent-likeness-law.md)
9. **EU AI Act Art. 50 transparency duties apply from 2 Aug 2026.** ✅ The Digital Omnibus gives generative systems already on the market until 2 Dec 2026, and only for the Art. 50(2) marking duty. 📄 Classical least-squares fitting is probably not an "AI system", but neural landmark detectors and regressors probably are. ↔️ [consent-likeness-law](./consent-likeness-law.md)
10. **Disclose realistic public renders.** Add a visible credit ("Digital likeness of X, made with consent") plus IPTC digital-source-type metadata or C2PA Content Credentials. ↔️ [consent-likeness-law](./consent-likeness-law.md), [biometric-privacy](./biometric-privacy.md)

**Biometric data**

11. **Treat every derived artifact as biometric.** BIPA excludes photographs but not geometry measured from them (*Rivera v. Google*, *Patel v. Facebook*). 🧠 Whether a likeness mesh never used for recognition is regulated is contested: *Zellmer v. Meta* requires the data to be able to identify someone, and the try-on rulings are mixed. ↔️📄 A high-likeness head is identifying by design. [biometric-privacy](./biometric-privacy.md), [consent-likeness-law](./consent-likeness-law.md)
12. **GDPR: a fitted head is biometric by capability, but Art. 9 is triggered by purpose.** That is the mainstream EDPB and ICO reading. ✅ The ICO adds a caveat: using biometric data to learn about someone or treat them differently is likely identification. ✅ [biometric-privacy](./biometric-privacy.md)
13. **Recognition embeddings are the highest-risk artifact.** Keep them in RAM, compare them 1:1 only against the same project's reference photos, and persist only the cosine scores and the model hash. Never build 1:N search. 🧠 [biometric-privacy](./biometric-privacy.md), [consent-likeness-law](./consent-likeness-law.md)
14. **Local processing removes the developer, not the operator.** With no telemetry, the add-on developer neither collects nor processes the data. Every duty then falls on whoever runs the tool on someone else's face. Under BIPA, a "private entity" includes individuals. 🧠↔️ [biometric-privacy](./biometric-privacy.md)
15. **Any cloud step is a disclosure.** Mesh to MetaHuman, hosted generators, render farms and AI upscalers must each be named in the release, and their retention and training terms read. 🧠 [biometric-privacy](./biometric-privacy.md), [consent-likeness-law](./consent-likeness-law.md)
16. **Most leaks are accidental.** Typical routes are crash reports with face crops, analytics carrying landmark arrays, "send to support" buttons, and cloud inference hidden inside a dependency. 🧠 [biometric-privacy](./biometric-privacy.md)
17. **Deletion is triggered by purpose, with deadlines.**
    - Colorado: delete at the earliest of purpose met, 24 months after last interaction, or 45 days after the data is no longer needed (extendable by 45 days). 📄
    - BIPA: delete when the purpose is met or within 3 years of last interaction, whichever comes first. 🧠
    - CUBI: delete no later than 1 year after the purpose expires. 🧠

    [biometric-privacy](./biometric-privacy.md)
18. **BIPA exposure is now per person, not per scan.** The 2024 amendment (P.A. 103-0769) counts repeat collection from one person by one method as a single violation, and the Seventh Circuit held it retroactive in *Clay v. Union Pacific* (1 Apr 2026). ✅ It also accepts electronic signatures. 📄 [biometric-privacy](./biometric-privacy.md), [consent-likeness-law](./consent-likeness-law.md)
19. **There is no "anonymise" button.** Smoothing or quantising a mesh that still looks like the person does not de-identify it. 🧠 [biometric-privacy](./biometric-privacy.md)
20. **Pseudonymise, and clean the .blend before it leaves your machine.** A .blend stores image paths, packed images, previews and `.blend1` backups. 🧠 [biometric-privacy](./biometric-privacy.md)

**Copyright, licences and platforms**

21. **The licence on the weights or assets decides, not the code licence.** FLAME, BFM, InsightFace packs, dlib-68 and BiSeNet weights are non-commercial even inside MIT or BSD code. ONNX conversion, quantising or fine-tuning does not change that. 🧠 [licences-tos](./licences-tos.md)
22. **Default stack: MediaPipe → own numpy fitter → MPFB2 CC0 base → Multires.** MPFB2's CC0 status is confirmed. 📄 FLAME, BFM, DECA, MICA and InsightFace stay opt-in: the user downloads them under their own registration, and the project is flagged non-commercial. 🧠 [licences-tos](./licences-tos.md)
23. **Licensing the add-on.** The Blender manual requires extension add-ons to be GPL-3.0-or-later and bundled assets to be CC0. 📄 A bpy-free numpy engine can be MIT or Apache-2.0. 🧠 The GPL does not reach the meshes, .blend files or renders the tool produces. 🧠 [licences-tos](./licences-tos.md)
24. **Measure, don't copy.** Fitting landmarks and silhouettes extracts facts and carries low risk. Projecting or baking texture reproduces the photographer's pixels, so it needs a known rights basis. 🧠↔️ [licences-tos](./licences-tos.md), [consent-likeness-law](./consent-likeness-law.md)
25. **The subject's consent is not the photographer's licence.** The photographer owns the copyright, and a subject's camera roll is full of photos their friends took. 🧠 [licences-tos](./licences-tos.md)
26. **No scraping.** Instagram, Facebook, X, TikTok and LinkedIn all forbid automated collection. The clean route is the subject's own "Download your information" export plus each photographer's permission. 🧠 [licences-tos](./licences-tos.md)
27. **A CC licence clears copyright, not likeness.** CC 4.0 §2(b)(1) excludes publicity, privacy and personality rights. 🧠 [licences-tos](./licences-tos.md)
28. **Keep copyright metadata and strip location data.** Knowingly removing copyright management information is actionable under DMCA §1202, so keep the Artist and Copyright fields. Strip GPS and serial numbers. 🧠 [licences-tos](./licences-tos.md) (Reconciled with the biometric note in [C2](#cross-topic-contradictions-and-resolutions).)

## Quick-reference tables

All values come from the notes or their data tables. Statutes and licences change, so check the source before relying on any of them.

### Q1 · Key dates

| Date | Event | Badge | Note |
|---|---|---|---|
| 2008 | Illinois BIPA enacted | 🧠 | [CL](./consent-likeness-law.md) |
| 2024-03-21 / 07-01 | Tennessee ELVIS Act signed / effective | 📄 | [CL](./consent-likeness-law.md) |
| 2024-08-01 | EU AI Act in force | 🧠 | [CL](./consent-likeness-law.md) |
| 2024-08-02 | BIPA SB 2979 signed (one violation per person; e-signatures) | 📄 | [CL](./consent-likeness-law.md) |
| 2024-12-04 | Instagram Basic Display API retired | ↔️ | [LT](./licences-tos.md) |
| 2025-01-01 | California AB 2602 / AB 1836 effective | ↔️ | [CL](./consent-likeness-law.md) |
| 2025-02-02 | AI Act Art. 5 bans apply, including untargeted face scraping | 🧠 | [CL](./consent-likeness-law.md), [BP](./biometric-privacy.md) |
| 2025-05-19 | TAKE IT DOWN Act signed | 🧠 | [CL](./consent-likeness-law.md) |
| 2025-07-01 | Colorado HB 24-1130 biometric duties apply (deletion rule 📄; effective date not separately checked) | 🧠 | [BP](./biometric-privacy.md) |
| 2025-09-01 | China AI-content labelling mandatory | 🧠 | [CL](./consent-likeness-law.md) |
| 2026-01-01 | Texas TRAIGA (HB 149) amends CUBI | ↔️ | [BP](./biometric-privacy.md) |
| 2026-04-01 | *Clay v. Union Pacific*: BIPA amendment retroactive (7th Cir.) | ✅ | [BP](./biometric-privacy.md) |
| 2026-05 | TAKE IT DOWN platform removal duties (FTC) | 🧠 | [CL](./consent-likeness-law.md) |
| 2026-05-20 | NO FAKES revised as S. 4591 | 📄 | [CL](./consent-likeness-law.md) |
| 2026-06-10 | EU Code of Practice on AI-content marking reported finalised (voluntary) | 📄 | [CL](./consent-likeness-law.md) |
| 2026-06-18 | NO FAKES cleared Senate Judiciary (one source says 26 Jun) | 📄 | [CL](./consent-likeness-law.md) |
| 2026-08-02 | AI Act Art. 50 transparency applies (50(1), 50(3), 50(4) unchanged) | ✅ | [CL](./consent-likeness-law.md) |
| 2026-12-02 | Omnibus grace ends for Art. 50(2) marking (generative systems on the market before 2 Aug 2026) | 📄 | [CL](./consent-likeness-law.md) |
| 2027-01 | Next CCPA CPI adjustment due | 🧠 | [BP data](../data/biometric-privacy.json) |

### Q2 · Retention and response deadlines

| Rule | Value | Badge | Note |
|---|---|---|---|
| BIPA destruction | when the purpose is met or 3 yr after last interaction, whichever is first | 🧠 | [BP](./biometric-privacy.md) |
| BIPA limitation period | 5 yr (*Tims*, 2023) | 🧠 | [BP](./biometric-privacy.md) |
| CUBI destruction | ≤1 yr after the purpose expires | 🧠 | [BP](./biometric-privacy.md) |
| Colorado HB 24-1130 | earliest of purpose met / 24 months after last interaction / 45 days after no longer needed (+45 days extension) | 📄 | [BP](./biometric-privacy.md) |
| GDPR breach notice | 72 h | 🧠 | [BP](./biometric-privacy.md) |
| GDPR subject-request reply | 1 month (+2 months extension) | 🧠 | [BP](./biometric-privacy.md) |
| GDPR consent withdrawal | as easy as giving it (Art. 7(3)); erasure right applies | 🧠 | [CL](./consent-likeness-law.md) |
| Quebec biometric database | 60 days' notice to the regulator before going live | 🧠 | [BP](./biometric-privacy.md) |
| TAKE IT DOWN removal | 48 h after a valid request | 🧠 | [CL](./consent-likeness-law.md) |

### Q3 · Damages, fines and exposure

| Law or rule | Figure | Badge | Note |
|---|---|---|---|
| Cal. Civ. Code §3344 / §3344.1 | ≥ USD 750, or actual damages + profits | 🧠 | [CL](./consent-likeness-law.md) |
| Cal. AB 1836 (deceased replica) | ≥ USD 10,000, or actual damages | 🧠 | [CL](./consent-likeness-law.md) |
| Illinois BIPA | USD 1,000 negligent / 5,000 reckless per violation; one violation per person per method since 2024 | 🧠 / ✅ (counting) | [BP](./biometric-privacy.md) |
| Texas CUBI | ≤ USD 25,000 per violation (Attorney General only) | 🧠 | [BP](./biometric-privacy.md) |
| CCPA administrative fine | USD 2,500 / 7,500 intentional or minors (≈2,663 / 7,988 in 2025) | 🧠 | [BP](./biometric-privacy.md) |
| CCPA breach damages | USD 100–750 per consumer per incident (≈107–799 in 2025) | 🧠 | [BP](./biometric-privacy.md) |
| GDPR upper tier | EUR 20M or 4 % of worldwide turnover, whichever is higher | 🧠 | [CL](./consent-likeness-law.md), [BP](./biometric-privacy.md) |
| AI Act Art. 50 breach | EUR 15M or 3 % of turnover | 🧠 | [CL](./consent-likeness-law.md) |
| AI Act Art. 5 breach | EUR 35M or 7 % of turnover | 🧠 | [CL data](../data/consent-likeness-law.json) |
| TAKE IT DOWN prison | ≤2 yr (≤3 if the victim is a minor) | ↔️ | [CL](./consent-likeness-law.md) |
| 17 U.S.C. §504(c) | USD 750–30,000 per work; ≤150,000 if wilful (needs timely registration) | 🧠 | [LT](./licences-tos.md) |
| DMCA §1203 (removing copyright info) | USD 2,500–25,000 per violation | 🧠 | [LT](./licences-tos.md) |
| X terms, liquidated damages | USD 15,000 per 1M posts accessed in 24 h | ↔️ | [LT](./licences-tos.md) |
| India draft label (Oct 2025) | ≥10 % of display area | ↔️ | [CL](./consent-likeness-law.md) |

**Enforcement benchmarks** (all 🧠, [BP](./biometric-privacy.md); Clearview also in [LT](./licences-tos.md)):

| Matter | Amount |
|---|---|
| In re Facebook (Tag Suggestions), 2021 | USD 650M |
| Rivera v. Google (Photos face grouping), 2022 | USD 100M |
| Boone v. Snap (AR lenses), 2022 | USD 35M |
| Texas v. Meta, 2024 | USD 1.4B |
| Texas v. Google, 2025 | USD 1.375B |
| Clearview AI: Italy, Greece, France (2022) / Netherlands (2024) | EUR 20M each / EUR 30.5M |
| Clearview AI: UK ICO (2022) | GBP 7.5M (↔️, appeals) |

### Q4 · Post-mortem publicity terms ([CL](./consent-likeness-law.md))

| Jurisdiction | Term after death | Badge |
|---|---|---|
| California | 70 yr (§3344.1) | 🧠 |
| New York | 40 yr (§50-f) | 🧠 |
| Tennessee | 10 yr, then while used (lapses after 2 yr of non-use) | 🧠 |
| Indiana / Oklahoma | 100 yr | 🧠 |
| Texas / Illinois | 50 yr | 🧠 |
| Florida | 40 yr | 🧠 |
| Washington | 10 yr (individual) / 75 yr (personality) | ↔️ |
| Ohio / Pennsylvania / Virginia | 60 / 30 / 20 yr | ↔️ |
| Germany (KUG §22) | 10 yr, relatives' consent | 🧠 |
| NO FAKES (proposed) | 10 yr, renewable up to 70 (2025 terms) | ↔️ |

### Q5 · Pipeline artifacts: conservative classification ([BP](./biometric-privacy.md), [data](../data/biometric-privacy.json))

| Artifact | Data class | BIPA | GDPR | Default handling | Badge |
|---|---|---|---|---|---|
| Source photos | `PERSONAL_IMAGE` | excluded | personal data | external encrypted folder, EXIF stripped after copying the intrinsics whitelist (Q8, C3) | 🧠 |
| Per-photo landmarks (68–478 pts) | `BIOMETRIC_GEOMETRY` | likely face-geometry scan | biometric-capable | session cache only | ↔️ |
| 3DMM shape coefficients | `BIOMETRIC_GEOMETRY` | likely (compact template) | biometric-capable | project only, consent-scoped | ↔️ |
| Fitted mesh / sculpt | `BIOMETRIC_GEOMETRY` | contested | biometric-capable; Art. 9 by purpose | consent-scoped | ↔️ |
| Albedo with iris detail | `LIKENESS_ASSET` | possible "iris scan" | biometric-capable | consent-scoped | ↔️ |
| Recognition embedding | `BIOMETRIC_TEMPLATE` | identifier / information | biometric; 1:1 ≈ confirming identity | never persisted | 🧠 |
| Population prior (mean + PCA) | `AGGREGATE_PRIOR` | none if aggregate | not personal if truly aggregate | bundle only if the dataset licence allows | 🧠 |

### Q6 · Component licence matrix ([LT](./licences-tos.md), [data](../data/licences-tos.json))

Corrections from sibling notes are applied and flagged.

| Component | Code | Weights / data | Commercial | Ship how | Badge |
|---|---|---|---|---|---|
| MediaPipe Face Landmarker (478 pts + 52 blendshape scores) | Apache-2.0 | Apache-2.0 per model card (official card not retrieved) | yes | optional download, SHA-256 pinned | ↔️ |
| MediaPipe canonical face OBJ (468 vertices with UVs) | Apache-2.0 | n/a | yes | LT says bundle with NOTICE; see C7 | 🧠 / ↔️ |
| ONNX / ONNX Runtime / NumPy | Apache-2.0 / MIT / BSD-3 | n/a | yes | wheel; NumPy comes with Blender | 🧠 |
| MPFB2 / MakeHuman | GPL-3.0-or-later | CC0 base and targets; some packs CC-BY | yes | bundle the CC0 parts only (see C7) | 📄 |
| ICT-FaceKit | MIT | MIT | unclear | after a licence check | ↔️ |
| SAM / SAM 2 | Apache-2.0 | Apache-2.0 | yes | download | 🧠 |
| dlib 68-point | BSL-1.0 | iBUG 300-W, non-commercial | no | never | 🧠 |
| InsightFace packs (buffalo_l, antelopev2) | MIT | non-commercial; paid licence on request | no | never (user download) | 🧠 here; 📄 in [identity-embeddings](../reconstruction/identity-embeddings.md) |
| 3DDFA_V2 | MIT | BFM + 300W-LP, non-commercial | no | never | 🧠 |
| DECA / EMOCA / MICA | MPI non-commercial | FLAME | no | never | 🧠 |
| FLAME 2017–2023 | n/a | MPI non-commercial; registration; no redistribution | via licence | never | 🧠 |
| FLAME 2023 Open | n/a | CC BY 4.0 (attribution); texture model CC BY-NC-SA 4.0 | yes, geometry with attribution | user download (CC BY is not CC0) | ↔️ in LT; 📄 in [flame-model](../reconstruction/flame-model.md) (see C6) |
| BFM 2009/2017/2019 | n/a | Basel non-commercial; signed agreement | via agreement | never | 🧠 |
| BiSeNet face-parsing | MIT | CelebAMask-HQ, non-commercial | no | never | 🧠 |
| Ultralytics YOLO(-face) | AGPL-3.0 | AGPL-3.0 | copyleft or paid | avoid | 🧠 |
| Depth Anything V2 | Apache-2.0 | Small: Apache-2.0; Base/Large: CC BY-NC 4.0 | Small only | Small, download | ↔️ |
| FFHQ / CelebA | n/a | CC BY-NC-SA 4.0 / research only | no | never | 🧠 |

### Q7 · Use tier → required consent ([CL](./consent-likeness-law.md), [BP](./biometric-privacy.md))

| Tier | Examples | Extra requirements on top of the tier below | Badge |
|---|---|---|---|
| Personal | own or family head, never shared | GDPR household exemption; BIPA has none, but risk is low | 🧠 |
| Portfolio / social | public, non-commercial | written release with a publish scope; the household exemption is lost on publication (*Lindqvist*) | 🧠 |
| Commercial | client portrait, game asset, ad, stock, 3D print | commercial and print scopes; licence-clean stack; known photo rights for textures; re-confirm every 12 months | 🧠 |
| Replica | rig, expressions, voice, AI training | `RIG_ANIMATE` and `AI_TRAINING` scopes, each described specifically (SAG-AFTRA / AB 2602 logic) | 🧠 |

### Q8 · EXIF field policy (resolved; see C2 and C3)

| Field | Action | Why | Badge | Note |
|---|---|---|---|---|
| FocalLength, FocalLengthIn35mmFilm, Make, Model, PixelX/YDimension | copy to the solver sidecar | camera intrinsics, sensor lookup | 🧠 | [BP](./biometric-privacy.md) |
| Orientation | apply to the pixels, then record in the sidecar | correct rotation | 🧠 | [BP](./biometric-privacy.md) |
| Artist, Copyright (photographer) | **keep**; also copy to the rights sidecar and glTF `extras` | DMCA §1202 | 🧠 | [LT](./licences-tos.md) |
| OwnerName (camera owner; may be the subject) | move to the consent record | names people | 🧠 | [BP](./biometric-privacy.md) |
| GPS* | drop | location of the subject | 🧠 | [BP](./biometric-privacy.md), [LT](./licences-tos.md) |
| BodySerialNumber, LensSerialNumber | drop | device identifiers | 🧠 | [BP](./biometric-privacy.md) |
| MakerNote | drop | opaque; may hold serials or face boxes | 🧠 | [BP](./biometric-privacy.md) |
| ThumbnailImage | drop | a second copy of the face | 🧠 | [BP](./biometric-privacy.md) |
| DateTimeOriginal | optional | flags photos taken years apart | 🧠 | [BP data](../data/biometric-privacy.json) |

### Q9 · Photograph copyright terms ([LT](./licences-tos.md))

| Jurisdiction | Term | Badge |
|---|---|---|
| US (photos since 1978) | life + 70 yr; work for hire 95 yr from publication / 120 yr from creation | 🧠 |
| EU / UK, Canada, Japan | life + 70 yr | 🧠 |
| Germany / Austria, simple photos (*Lichtbilder*) | 50 yr | 🧠 |
| Italy / Spain, simple photos | 20 / 25 yr | 🧠 |
| China | life + 50 yr | ↔️ |
| India | 60 yr from publication | 🧠 |

### Q10 · Platforms ([LT](./licences-tos.md))

| Platform | Automated collection | Sanctioned route for the subject's own photos | Badge |
|---|---|---|---|
| Instagram, Facebook, Threads | no | Accounts Center › Download your information | 🧠 |
| X | no, without prior written consent | account archive | ↔️ |
| TikTok, LinkedIn, Pinterest | no | the platform's data export or data request | 🧠 |
| Flickr | API terms apply | the per-photo licence (which excludes publicity rights) | 🧠 |

### Q11 · Add-on policy defaults (merged and resolved)

| Parameter | Default | Badge | Note |
|---|---|---|---|
| Minimum self-consent age | 18 yr; below that, guardian consent + child assent | 🧠 | [CL](./consent-likeness-law.md) |
| Commercial consent re-confirmation | every 12 months | 🧠 | [CL](./consent-likeness-law.md) |
| Cache TTL (crops, heatmaps, per-photo landmarks) | 0 days, i.e. session-only (max 30) | 🧠 | [BP](./biometric-privacy.md) |
| Raw-photo deletion after the purpose ends | due ≤45 days, one logged +45-day extension (90 days at most) **(editor; see C1)** | 📄 (Colorado) | [BP](./biometric-privacy.md), [CL](./consent-likeness-law.md) |
| Hard cap since last interaction | 730 days (replaces CL's 3 yr) | 📄 (Colorado 24 months) | [BP](./biometric-privacy.md) |
| Retention after purpose (CUBI bound) | 365 days, an outer bound only | 🧠 | [BP](./biometric-privacy.md) |
| Expiry warning | 30 days before | 🧠 | [BP](./biometric-privacy.md) |
| Embeddings | RAM only; 1:1; persist score + model hash | 🧠 | [BP](./biometric-privacy.md), [CL](./consent-likeness-law.md) |
| Network / telemetry | off / off | 🧠 | [BP](./biometric-privacy.md) |
| `AI_TRAINING`, `CLOUD_PROCESSING` scopes | off | 🧠 | [CL](./consent-likeness-law.md) |
| Faces auto-fitted per photo | 1, chosen by the user | 🧠 | [CL](./consent-likeness-law.md) |
| Visible disclosure on realistic public renders | on | ↔️ | [CL](./consent-likeness-law.md) |
| Named real-person presets or sample data | never | 🧠 | [CL](./consent-likeness-law.md) |
| Unknown `commercial_ok` | treated as false | 🧠 | [LT](./licences-tos.md) |
| Photo `rights_basis = unknown` | fit allowed with a warning; texture bake, packing and export blocked | 🧠 | [LT](./licences-tos.md) |
| URL or social import | disabled | 🧠 | [LT](./licences-tos.md) |
| Add-on / engine licence | GPL-3.0-or-later / MIT or Apache-2.0 | 📄 / 🧠 | [LT](./licences-tos.md) |

## Artist checklist (Blender)

**Before the shoot**
- [ ] Classify the use tier (Q7). If it is personal, keep it personal: publishing changes the tier. [CL](./consent-likeness-law.md)
- [ ] Get a written, dated, signed release, scoped to the tier and stored apart from the data. It should list:
  - the artifacts (photos, landmarks, camera solve, mesh, sculpt, textures, renders, prints, likeness scores);
  - one tick-box each for sculpt, texture, publish, commercial, animation rig, 3D print, each named cloud service, and training;
  - an end date and the withdrawal terms.

  [BP](./biometric-privacy.md), [CL](./consent-likeness-law.md)
- [ ] For a minor, get the guardian's signature plus the child's assent. For a deceased subject, get the estate's (Q4). Never default a minor to a combination that is animatable, public and realistic. [CL](./consent-likeness-law.md)
- [ ] For a celebrity likeness, keep it to private practice. Do not sell STLs, prints or mods of a recognisable star. [CL](./consent-likeness-law.md)

**Photos**
- [ ] Shoot the reference yourself (see `../blender/reference-camera-setup.md`), or log every image's photographer and rights basis: self-shot, subject selfie, photographer licence, CC licence with version, or unknown. [LT](./licences-tos.md)
- [ ] Get social photos only through the subject's own data export. Never scrape, never bulk-download while logged in, never take the subject's password. [LT](./licences-tos.md)
- [ ] Group photos: fit only the consenting subject; never fit bystanders. [CL](./consent-likeness-law.md)

**Import and fitting**
- [ ] Before stripping anything, copy the focal length, 35 mm equivalent, make, model, dimensions and orientation into a sidecar. Then drop GPS, serial numbers, MakerNote and the thumbnail. Keep the Artist and Copyright fields (Q8). [BP](./biometric-privacy.md), [LT](./licences-tos.md)
- [ ] Name folders, files, datablocks and custom properties with a subject ID, never the person's name. [BP](./biometric-privacy.md)
- [ ] Use a licence-clean stack for anything that may go commercial: MediaPipe, the numpy fitter, and the MPFB2 CC0 base. A FLAME, BFM, InsightFace or dlib component makes the project non-commercial. [LT](./licences-tos.md)
- [ ] Process locally. Every cloud step must be named in the release. [BP](./biometric-privacy.md)

**Texturing and sculpting**
- [ ] Project or bake textures only from photos with a known rights basis. Eyeballing a photo in the viewport counts as study. [LT](./licences-tos.md)
- [ ] Iris-detailed albedo is consent-scoped: it may count as an "iris scan". [BP](./biometric-privacy.md)
- [ ] In commercial work, license, omit or alter tattoos and logos. Don't recreate a specific photo's pose, expression and lighting in the finished piece. [CL](./consent-likeness-law.md), [LT](./licences-tos.md)
- [ ] Build expression shape keys or a rig only if the release includes animation. [CL](./consent-likeness-law.md)

**Saving and sharing a .blend**
- [ ] Unpack or remove reference images, clear the camera Background Images and image empties, and purge orphan data. [BP](./biometric-privacy.md)
- [ ] Set the file preview (Preferences › Save & Load) to None. Delete `.blend1…N` backups and the autosave and `quit.blend` files in the temp folder. [BP](./biometric-privacy.md)
- [ ] Never store ArcFace or any other embedding vector in custom properties. [BP](./biometric-privacy.md)
- [ ] Never ship packed photos inside a sold .blend. [LT](./licences-tos.md)

**Publishing and export**
- [ ] Add a visible credit to realistic renders ("Digital likeness of X, made with consent"), plus IPTC digital-source-type metadata or C2PA (`c2patool`). [CL](./consent-likeness-law.md)
- [ ] Write `likeness.consent_id`, `likeness.synthetic=true` and `likeness.scopes` into custom properties, so they reach glTF `extras` on export. [CL](./consent-likeness-law.md)
- [ ] Include `ATTRIBUTION.txt` for any CC-BY asset, including FLAME 2023 Open if it was used. [LT](./licences-tos.md), [flame-model](../reconstruction/flame-model.md)
- [ ] Never put the head on sexual, political or endorsement content unless the release names that use. [CL](./consent-likeness-law.md)

**Closing, expiry and withdrawal**
- [ ] When the project closes, start the deletion clock for raw photos and caches (Q11). [BP](./biometric-privacy.md)
- [ ] On withdrawal or expiry, delete every class of data, including backups and remote copies. Log the date and hashes, and keep the signed release as proof. [BP](./biometric-privacy.md)

## Cross-topic contradictions and resolutions

| # | Conflict | Resolution |
|---|---|---|
| C1 | **Retention clocks disagree.** [CL](./consent-likeness-law.md) sets a 90-day reminder after the project closes and a 3-year hard cap (BIPA). [BP](./biometric-privacy.md) sets 365 days after the purpose ends (CUBI) and a 730-day cap. But Colorado (📄) and BIPA (🧠) both make *purpose met* the trigger, and Colorado requires deletion within 45 days of the data no longer being needed. So BP's 365-day default does not satisfy Colorado. | **(editor)** End the purpose per data class: raw photos and caches at project close; likeness assets at the consent `expires_at`. Deletion is due 45 days after the purpose ends, with one logged 45-day extension; that makes 90 days the outer bound, which matches CL's 90-day figure. 730 days since last interaction is the absolute cap. 365 days serves only as a CUBI bound when no tighter rule applies. |
| C2 | **EXIF Artist and Copyright.** [BP](./biometric-privacy.md) says "drop or move to consent record (names people)". [LT](./licences-tos.md) says preserve them (DMCA §1202). | **(editor)** Artist and Copyright name the *photographer*, a rights holder, not the subject. Keep them in the working copy, in the rights sidecar and in glTF `extras`. Move only OwnerName, and any field naming the subject, to the consent record. |
| C3 | **Keep EXIF or strip it.** Reconstruction and Blender notes say to keep the original files and their EXIF for the solver (e.g. `../reconstruction/multi-view-fitting.md`, `../blender/reference-camera-setup.md`). [BP](./biometric-privacy.md) says to strip EXIF on import. | Whitelist the intrinsics into the sidecar at ingest (as BP itself specifies), then strip. Originals go to an external encrypted folder under the C1 clock, and the .blend references only the stripped working copies. |
| C4 | **Two consent schemas.** [CL](./consent-likeness-law.md) uses bitflags (`CAPTURE…AI_TRAINING`). [BP](./biometric-privacy.md) uses a scope set (`sculpt, texture, …, identity_check, train`) plus a `subject_is_user` bypass. | **(editor)** Merge them into one schema, adding `TEXTURE` and `IDENTITY_CHECK` to CL's flags. Replace the bypass with `signer_role = self`: self-capture still produces a record, so export provenance works. Full mapping in `../_raw/requirements_ethics.md`. |
| C5 | **AI Act Art. 50 timing.** [BP](./biometric-privacy.md) has "due 2 Aug 2026, with 2025 Omnibus delay proposals" (↔️), and `../reconstruction/identity-embeddings.md` says the same. | Use [CL](./consent-likeness-law.md)'s verified version: applies from 2 Aug 2026 (✅). The grace period to 2 Dec 2026 covers only Art. 50(2) and only pre-existing generative systems (📄). Art. 50(4) deepfake disclosure is not delayed. |
| C6 | **FLAME 2023 Open.** [LT](./licences-tos.md) marks it unconfirmed (↔️). At least six sibling notes confirmed CC BY 4.0 from the official licence page (📄): `../reconstruction/flame-model.md`, `../reconstruction/3dmm-overview.md`, `../blender/blender-face-addons.md`, `../reconstruction/multi-view-fitting.md`, `../community/awesome-lists-resources.md`, `../reconstruction/sota-2025-2026.md`. | Adopt the sibling 📄 status. The geometry is commercial-OK with attribution. The texture model is CC BY-NC-SA 4.0. Its contents (bases, masks, UVs) are still unconfirmed. Do not bundle it in an Extensions zip, because CC BY is not CC0; the user downloads it. All other FLAME versions stay non-commercial. |
| C7 | **What may be bundled.** [LT](./licences-tos.md) Table 1 marks MPFB2 "bundle: yes" and the MediaPipe canonical OBJ "yes, with NOTICE". But LT's own verified correction (📄) says assets bundled in an extension must be CC0, so some MPFB2 packs (CC-BY) and the Apache-2.0 OBJ do not qualify. | Bundle only the CC0 MPFB2 base and targets. Whether the 468-vertex OBJ counts as a non-CC0 "asset" is an open question (↔️): until a platform reviewer confirms, keep it out of the zip, or carry only Apache-2.0 index tables in code with a NOTICE. |
| C8 | **Runtime downloads.** [LT](./licences-tos.md) plans "download on demand, SHA-256 pinned" for MediaPipe weights, with the platform rule unconfirmed (🧠). `../blender/blender-extensions-packaging.md` (📄) lists "requiring externally downloaded components" as not allowed. | **(editor)** The core pipeline must run end to end with no download at all: manual or imported landmarks, the numpy engine and the CC0 template. Detector downloads are optional, behind the `network` permission, `bpy.app.online_access` and a licence click-through. Confirm with the platform before upload. |
| C9 | **Why non-commercial weights can't ship.** `../blender/blender-extensions-packaging.md` says non-commercial terms are GPL-incompatible. [LT](./licences-tos.md) says separate data files are "mere aggregation", and it is the assets' own no-redistribution clauses plus the Extensions policy that bar them. | The outcome is the same either way: never bundle them. Cite LT's reasoning. |
| C10 | **ELVIS Act wording.** The digest and an earlier draft paraphrased it as "particular, identified individual". | The verified text says "an individual's" (📄, [CL](./consent-likeness-law.md)). Whether a general fitter is covered remains ↔️. |
| C11 | ***Zellmer v. Meta*.** [CL](./consent-likeness-law.md)'s log says it is "unconfirmed (not in results)". [BP](./biometric-privacy.md)'s log confirms it from the opinion (requires identification capability). | Use BP's sourced reading. The mesh question stays ↔️, and both notes say to assume coverage. |
| C12 | **Non-commercial model in a commercial project.** `../reconstruction/identity-embeddings.md` says "warn". [LT](./licences-tos.md) and [CL](./consent-likeness-law.md) say "block commercial export". Identity-embeddings also gates embeddings with a tick-box. | Warn when the model is enabled, and block at `COMMERCIAL` export (fail closed). A tick-box is not a consent record: identity scoring needs `IDENTITY_CHECK` in the ConsentRecord. |
| C13 | **Is disclosure mandatory?** [CL](./consent-likeness-law.md) treats it as mandatory for neural-pipeline output in the EU (↔️) but also says classical fitting is probably not an AI system (↔️). | Turn the visible disclosure on by default for every realistic public render (cheap, and it also answers deception statutes such as France 226-8). Record whether any ML component touched the result, so the metadata can be accurate. |
| C14 | **BIPA 2024 amendment.** BP's original claim that "courts split" on retroactivity. | Corrected to the 7th Circuit holding it retroactive (✅); state courts are unverified. Model exposure per person in federal court. |

## Open questions (time-sensitive)

- NO FAKES floor and House action, pre-emption scope and final terms ([CL](./consent-likeness-law.md)).
- Whether a likeness mesh, 3DMM coefficients or an iris texture are "face geometry", "templates" or an "iris scan", and at what iris resolution ([BP](./biometric-privacy.md)).
- Whether Art. 50 reaches classically fitted CGI, and whether 3D renders count as deepfakes ([CL](./consent-likeness-law.md), [BP](./biometric-privacy.md)).
- BIPA retroactivity in state courts, TRAIGA's carve-outs, the December 2025 US executive order, India's final IT Rules, Denmark's likeness right, a UK personality right ([CL](./consent-likeness-law.md), [BP](./biometric-privacy.md)).
- MediaPipe's official model-card licence; the Extensions rules on runtime model downloads and non-CC0 data; the current X terms; whether non-commercial detector outputs legally taint the fitted geometry; what counts as "non-commercial" ([LT](./licences-tos.md)).

## Index of topic notes

| Note | One-line description | Data table | Evidence |
|---|---|---|---|
| [consent-likeness-law](./consent-likeness-law.md) | Publicity and personality rights, digital-replica and deepfake statutes (ELVIS, NO FAKES, TAKE IT DOWN, AI Act Art. 50), consent tiers and the release, plus the ConsentRecord, gating and provenance design | [JSON](../data/consent-likeness-law.json): post-mortem terms, damages, key dates, add-on policy defaults | 1 ✅ / 5 📄 / 52 🧠 / 25 ↔️ |
| [biometric-privacy](./biometric-privacy.md) | Whether face geometry is biometric (BIPA, CUBI, Colorado, CCPA, GDPR); duties, retention and enforcement; local versus cloud; data classes, retention defaults, embedding and EXIF policy | [JSON](../data/biometric-privacy.json): statutory parameters, enforcement, engine privacy defaults, artifact classes, EXIF policy | 3 ✅ / 2 📄 / 58 🧠 / 13 ↔️ |
| [licences-tos](./licences-tos.md) | Model, dataset and template licences; GPL and the Extensions platform; photographer copyright; platform scraping bans; LicenceTag, taint propagation and the photo rights gate | [JSON](../data/licences-tos.json): component matrix, photo copyright terms, exposure, platforms, licence policy defaults | 0 ✅ / 3 📄 / 65 🧠 / 29 ↔️ |
