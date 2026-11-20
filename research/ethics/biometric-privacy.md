# Biometric privacy law and face geometry

> A photo→3D likeness pipeline produces what biometric laws regulate: landmark geometry, fitted shape coefficients, a metric face mesh and, if likeness is scored with ArcFace-style embeddings, a textbook faceprint. Illinois BIPA excludes photographs, but courts have treated face geometry *derived from* photos as a "scan of face geometry"; GDPR calls data biometric when it *can* uniquely identify someone and makes it Art. 9 special-category data when processed *to* identify. Whether a likeness mesh never used for recognition is regulated is contested, and a high-likeness head is identifying by design, so the safe engineering stance treats every derived artifact as biometric. Local processing largely takes the add-on developer out of the chain, but every duty (written release, purpose, retention, disclosure limits) then sits with the artist or studio running it. Not legal advice; the law moved in 2024–2026.
>
> Evidence status: 0 ✅ / 0 📄 / 60 🧠 / 16 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Is face geometry "biometric"?**
- **BIPA (740 ILCS 14, Illinois, 2008).** "Biometric identifier" = retina or iris scan, fingerprint, voiceprint, or *scan of hand or face geometry*; photographs, physical descriptions and demographic data are excluded. "Biometric information" = information based on an identifier and *used to identify* someone. "Scan of face geometry" is undefined. 🧠
- **Derived geometry is not "a photograph".** Rivera v. Google (N.D. Ill. 2017) and the Facebook Tag Suggestions litigation (Patel v. Facebook, 9th Cir. 2019) treated templates computed from uploaded photos as scans of face geometry. 🧠
- **Must it be able to identify?** Zellmer v. Meta (9th Cir. 2024): face signatures that could not identify a non-user were not biometric identifiers. Virtual try-on suits (AR make-up, eyewear; since ~2022) split: some survived dismissal with no recognition purpose, others failed for not alleging identification capability. A likeness mesh is untested. ↔️
- **Meshes do identify.** 3D-only recognition on FRGC v2.0 (≈4,000 scans of ≈466 people) reached roughly 97–99 % verification at 0.1 % false-accept rate in late-2000s methods. 🧠
- **Texas CUBI (Bus. & Com. Code §503.001, 2009)** covers a "record of hand or face geometry", only when captured **for a commercial purpose**. 🧠
- **Washington RCW 19.375 (2017)** excludes photographs "or data generated therefrom"; the **My Health My Data Act** (RCW 19.373, 2024) is broader (face imagery from which a template can be extracted) and has a private right of action. 🧠
- **US comprehensive state laws** (≈19–20 states) make biometric data processed to identify "sensitive", needing opt-in consent. Virginia-model text excludes photos and data generated from them; Connecticut-style text adds "unless generated to identify a specific individual". 🧠
- **Colorado HB 24-1130 (from 1 July 2025)** binds any controller collecting biometric identifiers, whatever its size: written policy, consent, deletion by the earliest of purpose met, 24 months after last interaction, or 45 days after no longer needed. 🧠
- **GDPR Art. 4(14):** biometric data = personal data from *specific technical processing* of physical characteristics that *allow or confirm unique identification*, "such as facial images". **Recital 51:** photos are special-category only when processed by technical means allowing unique identification. **Art. 9(1)** bans processing biometric data "for the purpose of uniquely identifying" a person unless Art. 9(2) applies (here, realistically, explicit consent). 🧠
- **GDPR reading here:** a fitted head is personal data and very likely biometric data (technical processing, identification-capable); in the mainstream (EDPB, UK ICO 2024) reading, Art. 9 turns on purpose. A likeness sculpt needs an Art. 6 basis; 1:1 identity scoring with embeddings comes close to "confirming" identity. ↔️
- **CCPA/CPRA (Cal. Civ. Code §1798.100 ff.):** "biometric information" includes face imagery from which a faceprint *can* be extracted, so the photos qualify; it is "sensitive personal information" (right to limit) only when processed *to uniquely identify*. 🧠
- **Elsewhere:** Japan's APPI lists computer-processed facial-feature positions and shapes as identification codes; China PIPL Arts. 28–29 (sensitive, separate consent); Brazil LGPD Art. 5(II); Quebec requires 60 days' notice to its regulator before a biometric database goes live; Australia treats biometric templates as sensitive. 🧠

**Obligations and exposure**
- **BIPA §15:** (a) public retention policy, destroying when the purpose is met or **3 years** after last interaction, whichever is first; (b) before collecting: written notice, specific purpose and term, **written release**; (c) no profiting; (d) no disclosure without consent; (e) security at least equal to other sensitive data. 🧠
- **"Private entity" includes individuals; there is no service-provider exemption.** A freelance artist is covered and cloud vendors have been sued directly; courts generally require an affirmative act of collection, or control for possession (e.g., Heard v. Becton Dickinson, N.D. Ill. 2020). ↔️
- **BIPA damages (§20):** $1,000 negligent / $5,000 intentional or reckless per violation, plus fees. Rosenbach v. Six Flags (Ill. 2019): no actual harm needed. Tims (Ill. 2023): 5-year limitation. Cothron v. White Castle (Ill. 2023): each scan accrues a claim. 🧠
- **P.A. 103-0769 (SB 2979, Aug 2024)** made repeated collection from one person by one method a single violation and accepts e-signatures as a written release; courts split on pending cases. ↔️
- **CUBI:** notice and consent (not necessarily written) before capture; no sale or disclosure; reasonable care; destroy **≤1 year after the purpose expires**; Attorney General only, **≤$25,000 per violation**. Texas settled with Meta for $1.4 billion (2024) and Google for $1.375 billion (2025). 🧠
- **Texas HB 149 (TRAIGA, from 1 Jan 2026)** reportedly amended CUBI: a public image implies no consent unless the person published it; AI training not used to identify is carved out. ↔️
- **GDPR controller duties** fall on the artist or studio; a hobbyist has the **Art. 2(2)(c) household exemption**, lost once results are published to the world (CJEU Lindqvist, 2003). Duties: Art. 6 basis; Art. 9(2)(a) explicit consent where Art. 9 applies; withdrawable, provable consent (Art. 7); minimisation and storage limitation (Art. 5); by design (Art. 25); Art. 28 contract with cloud processors; transfer rules (EU–US Data Privacy Framework since 2023); DPIA at large scale (Art. 35). 🧠
- **Clearview AI** (scraped faceprints): ≈€20 M each from Italy, Greece and France (2022), €30.5 M from the Netherlands (2024); BIPA class settled in 2025 for an equity stake. 🧠
- **FTC:** biometric Policy Statement (2023); Everalbum (2021) ordered deletion of *models trained* on improperly obtained face data. 🧠
- **EU AI Act:** Art. 5(1)(e) has banned untargeted face scraping into recognition databases since 2 Feb 2025; Art. 50(4) deepfake disclosure was due 2 Aug 2026, with 2025 "Digital Omnibus" delay proposals. ↔️
- **Likeness law sits alongside:** right of publicity (e.g., Cal. Civ. Code §3344), digital-replica statutes (California AB 2602/AB 1836; Tennessee ELVIS Act, 2024), US TAKE IT DOWN Act (2025). The amended COPPA Rule (2025) adds facial templates to children's personal information. 🧠

**Local vs cloud**
- **Local, open-source, no telemetry:** the developer does not collect, possess or disclose (BIPA) and is neither controller nor processor (GDPR; Recital 78 only *encourages* producers). All duties fall on whoever runs the tool on someone else's face. 🧠
- **A developer-run cloud backend** makes the developer a BIPA collector and a GDPR processor or controller: release flow, retention policy, security, processing agreement, transfer mechanism, 72 h breach notice. 🧠
- **Accidental collection is the usual trap:** crash reports with face crops, analytics with landmark arrays, "send to support" buttons, cloud inference hidden in a dependency. 🧠

## Numbers & reference tables

**Table 1 — Statutory parameters** (nominal currency; as of author knowledge)

| Law | Parameter | Value | Badge |
|---|---|---|---|
| BIPA | Retention cap | earlier of purpose met or 3 yr after last interaction | 🧠 |
| BIPA | Damages per violation | $1,000 negligent / $5,000 intentional or reckless | 🧠 |
| BIPA | Violation count since 2024 | one per person per method (retroactivity disputed) | ↔️ |
| BIPA | Limitation period | 5 yr | 🧠 |
| CUBI | Destruction | ≤1 yr after purpose expires | 🧠 |
| CUBI | Civil penalty (AG only) | ≤$25,000 per violation | 🧠 |
| Colorado | Deletion | earliest of purpose met / 24 months after last interaction / 45 days after no longer needed | 🧠 |
| GDPR | Maximum fine | €20 M or 4 % worldwide turnover, whichever higher | 🧠 |
| GDPR | Breach notice | 72 h | 🧠 |
| GDPR | Subject-request reply | 1 month (+2 extendable) | 🧠 |
| CCPA | "Business" threshold | >$25 M revenue (≈$26.6 M adjusted, 2025), or ≥100,000 consumers, or ≥50 % revenue from selling/sharing | 🧠 |
| CCPA | Fine | $2,500 / $7,500 intentional or minors (≈$2,663 / $7,988, 2025) | 🧠 |
| CCPA | Breach damages | $100–$750 per consumer per incident (≈$107–$799, 2025) | 🧠 |

**Table 2 — Enforcement benchmarks**

| Matter | Year | Outcome | Badge |
|---|---|---|---|
| In re Facebook (Tag Suggestions), BIPA | 2021 | $650 M settlement | 🧠 |
| Rivera v. Google (Photos face grouping), BIPA | 2022 | $100 M settlement | 🧠 |
| Boone v. Snap (AR lenses/filters), BIPA | 2022 | $35 M settlement | 🧠 |
| Texas v. Meta, CUBI | 2024 | $1.4 B | 🧠 |
| Texas v. Google, CUBI and others | 2025 | $1.375 B | 🧠 |
| Clearview AI: IT, GR, FR / NL | 2022 / 2024 | €20 M each / €30.5 M | 🧠 |

**Table 3 — Pipeline artifacts, conservative classification**

| Artifact | BIPA | GDPR | CCPA | Default handling | Badge |
|---|---|---|---|---|---|
| Source photos | excluded | personal data | biometric information | external encrypted folder, EXIF stripped | 🧠 |
| Per-photo landmarks (68–478 pts) | likely face-geometry scan | biometric-capable | biometric | session cache only | ↔️ |
| 3DMM shape coefficients | likely (compact template) | biometric-capable | biometric | project only | ↔️ |
| Fitted mesh / sculpt | contested | biometric-capable; Art. 9 by purpose | biometric | consent-scoped | ↔️ |
| Albedo with iris detail | possible "iris scan" | biometric-capable | biometric | consent-scoped | ↔️ |
| Recognition embedding | identifier/information | biometric; 1:1 ≈ confirming identity | sensitive | never persisted | 🧠 |
| Population prior (mean + PCA) | none if aggregate | not personal if truly aggregate | none | check dataset licence | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Classify the job.** Own face or family, private use: GDPR household exemption, no CUBI commercial purpose; BIPA has no household exemption, but risk is low. Paid commissions, studio or game/film likenesses, or anything published make you collector/controller. Check where the subject lives and is photographed. 🧠
2. **Written release before the shoot.** A BIPA-grade release also meets CUBI and most GDPR explicit-consent tests. It states who collects and that face geometry will be measured and stored; lists artifacts (photos, landmarks, camera solve, fitted mesh, sculpt, textures, renders, prints, likeness scores); has separate tick-boxes for sculpt, publish, commercial, animation rig, 3D print, named cloud services and training; sets an end date; explains withdrawal and what cannot be recalled; needs a guardian for minors; is dated and signed (e-signature accepted in Illinois since 2024). Store it apart from the data. 🧠
3. **Pseudonymise:** subject IDs, not names, in folders, filenames, datablocks and custom properties; a .blend stores image paths. 🧠
4. **Strip EXIF on import, keep intrinsics:** copy FocalLength, FocalLengthIn35mmFilm, Make/Model, dimensions and Orientation into a sidecar for the camera solver; drop GPS, serial numbers, owner/artist names, MakerNote and thumbnails. 🧠
5. **Clean a .blend before it leaves your machine:** unpack or remove reference images, clear camera Background Images and image empties, purge orphans, set the file preview (Preferences › Save & Load) to None, and delete `.blend1…N` backups plus autosave and `quit.blend` in the temp folder. 🧠
6. **Cloud is disclosure.** Mesh to MetaHuman, hosted image-to-3D generators, render farms and AI upscalers all receive biometric data: name them in the release, read retention and training terms, delete afterwards. 🧠
7. **Publishing a photoreal head** brings in publicity and digital-replica law and possibly EU deepfake disclosure: caption renders "digital likeness, made with consent". ↔️
8. **On withdrawal or expiry,** delete every class of data including backups and remote copies; log date and hashes; keep the signed release as proof. 🧠
9. **What goes wrong:** sculpting someone from social-media photos (public is not consent); pasting client photos into a free generator; a bug report containing a face crop; ArcFace vectors in custom properties; minors without a guardian; staff "consent" to an employer (GDPR doubts it); an animatable rig built under static-sculpt consent. 🧠

## Algorithmic implications

No anatomical priors or sigmas come from this topic; it sets data classes, gates and defaults.

- **Data class on every stored object:** `PERSONAL_IMAGE`, `BIOMETRIC_GEOMETRY` (landmarks, coefficients, meshes), `BIOMETRIC_TEMPLATE` (embeddings), `LIKENESS_ASSET` (sculpt, textures, renders), `AGGREGATE_PRIOR`, recorded in a project manifest; purge operators act by class. 🧠
- **Consent record as a required datablock:** `consent_id`, `subject_is_user`, `jurisdictions`, `scopes ⊆ {sculpt, texture, publish, commercial, animate, print, cloud, identity_check, train}`, `signed_at`, `expires_at`, `method`. `detect_landmarks`, `fit` and `export` refuse without it (unless `subject_is_user`); `identity_score` also needs `identity_check`; any network call needs `cloud`. 🧠
- **Retention defaults:** caches (crops, heatmaps, per-photo landmarks) session-only, `cache_ttl_days = 0` (max 30); `retention_after_purpose_days = 365` (CUBI); hard cap `max_days_since_last_interaction = 730` (Colorado's 24 months, inside BIPA's 3 years); warn 30 days ahead. 🧠
- **Embeddings:** in RAM, 1:1 only against the same project's reference photos, freed at once; persist only cosine scores and the model hash. Never 1:N search or "find this face". 🧠
- **Network:** `network_enabled = False`; each call confirms host, data classes and consent scope; a CI test makes `socket.socket.connect` raise during a full pipeline run. 🧠
- **Logging:** no telemetry; error reports strip arrays, images and paths; audit log is append-only JSONL (event, time, class, SHA-256), never pixels or coordinates. 🧠
- **Bundled priors:** aggregate statistics only, where the dataset licence allows redistribution; record each prior's licence and consent basis (FLAME, BFM and similar are typically non-commercial research licences). ↔️
- **No "anonymise" toggle:** smoothing or quantising a mesh that still looks like the person does not de-identify it. 🧠

## Disagreements, myths & open questions

- **Myth: "BIPA excludes photos, so photo pipelines are safe."** The exclusion covers images, not geometry measured from them. 🧠
- **Myth: "Local means no law applies."** It removes the developer, not the operator. 🧠
- **Myth: "Public photos imply consent."** Clearview, Texas's 2025 amendment and GDPR reject this. 🧠
- **Myth: "An MIT/GPL disclaimer covers users."** It does not change the duties of whoever collects. 🧠
- ↔️ **Capability vs purpose.** GDPR: biometric by capability, Art. 9 by purpose (majority) or capability alone (minority). BIPA: Zellmer requires capability; some Illinois courts ask only whether geometry was scanned.
- ↔️ **Is a hand-sculpted head still a "scan"?** Heavy manual sculpting may make it an artist's depiction, like a painted portrait. Untested.
- ↔️ **Time-sensitive:** BIPA 2024 retroactivity; the AI Act Art. 50 date and whether 3D renders count as deepfakes; TRAIGA's carve-outs; whether the EU Cyber Resilience Act reaches donation-funded add-ons; EU–US transfers after Latombe v Commission (2025, appeal pending).
- **Open:** the iris resolution at which a texture becomes an "iris scan"; whether 3DMM coefficients are "templates"; a US federal privacy law (none enacted, as far as the author knows).

## Sources

No harvest file or earlier draft existed for this topic, so no URLs are cited. Related notes: `research/reconstruction/identity-embeddings.md`, `research/blender/metahuman-cc-bridges.md`, `research/community/ai-assisted-sculpting.md`.

**Further reading (by name, not yet linked)**

- Illinois BIPA, 740 ILCS 14 (2008), amended by Public Act 103-0769 (2024)
- Texas Bus. & Com. Code §503.001; Texas HB 149 (TRAIGA, 2025)
- Washington RCW 19.375 and RCW 19.373; Colorado HB 24-1130
- CCPA as amended by CPRA, Cal. Civ. Code §1798.100 et seq.; Cal. Civ. Code §3344
- Regulation (EU) 2016/679 (GDPR), Arts. 2, 4, 6, 7, 9, 25, 28, 35, 83; Recitals 51, 78
- Regulation (EU) 2024/1689 (AI Act); Regulation (EU) 2024/2847 (Cyber Resilience Act)
- Rosenbach v. Six Flags, 2019 IL 123186; Tims v. Black Horse Carriers, 2023 IL 127801; Cothron v. White Castle, 2023 IL 128004
- Rivera v. Google (N.D. Ill. 2017); Patel v. Facebook (9th Cir. 2019); Zellmer v. Meta (9th Cir. 2024); Heard v. Becton Dickinson (N.D. Ill. 2020)
- CJEU C-101/01 Lindqvist (2003)
- EDPB Guidelines 07/2020 (controller and processor); Article 29 Working Party Opinion 02/2012 on facial recognition
- UK ICO, Biometric data guidance (2024)
- FTC Policy Statement on Biometric Information (2023); In re Everalbum (2021)
- Japan APPI; China PIPL; Brazil LGPD; Quebec IT framework act
- Phillips et al., Overview of the Face Recognition Grand Challenge, CVPR 2005
