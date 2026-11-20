# Consent, right of publicity and deepfake law

> Recreating a real person's head touches four legal layers:
> - **publicity and personality rights** (US state law, the German KUG, French *droit à l'image*, UK passing off, Indian court orders);
> - **biometric and data-protection law** over the photos, meshes and embeddings (GDPR Art. 9, Illinois BIPA, Texas CUBI);
> - **digital-replica and deepfake law** (Tennessee ELVIS Act, California AB 2602/AB 1836, TAKE IT DOWN, the pending NO FAKES Act, EU AI Act Art. 50 from 2 Aug 2026);
> - **contracts and licences**.
>
> Written, scoped, revocable consent is necessary but not sufficient: it does not cure photo or tattoo copyright, a non-commercial model licence, or a duty to disclose realistic fakes. For the add-on, safe design means default-deny consent gating, local processing, no stored embeddings, no celebrity presets and provenance metadata on export. There was no harvest or earlier draft, so all of this is expert knowledge as of mid-2026, awaiting verification; it is not legal advice.
>
> Evidence status: 0 ✅ / 0 📄 / 53 🧠 / 27 ↔️ — 🧠 items are queued for web verification.

## Key facts

**US right of publicity**
- There is **no federal right of publicity**. Roughly 30–40 states recognise one by statute or common law, about 20–25 of them by statute. ↔️
- **California.** Civ. Code §3344 bars knowing use of a living person's name, voice, signature, photograph or likeness on products or in ads without consent, with damages of at least $750 or actual damages, plus profits and fees. §3344.1 covers the dead for 70 years. 🧠
- **Stylisation is no safe harbour.** Common law reaches "evocation": in *White v. Samsung* (9th Cir. 1992) a robot evoking Vanna White was enough, and *Midler v. Ford* and *Waits v. Frito-Lay* covered sound-alike voices. 🧠
- **Transformative use** (*Comedy III v. Saderup*, Cal. 2001): literal likenesses are not protected (the Stooges T-shirts lost); significant added creative expression is (*Winter v. DC Comics*, 2003). 🧠
- **Games: realism loses** (*No Doubt v. Activision*, 2011; *Keller v. EA*, 9th Cir. 2013; *Hart v. EA*, 3d Cir. 2013). Composites and look-alikes won in *Kirby v. Sega* (2006), *Lohan v. Take-Two* (N.Y. 2018) and *Noriega v. Activision* (2014). **Likeness accuracy and legal exposure rise together.** 🧠
- **False endorsement** (Lanham Act §43(a)) runs in parallel. 🧠 One-off fine art fares better than multiples, STLs or ads (*ETW v. Jireh*, 6th Cir. 2003). 🧠

**Digital-replica statutes**
- **Tennessee ELVIS Act** (signed 21 Mar 2024, effective 1 Jul 2024). 🧠
  - It adds actual or simulated voice.
  - It creates liability for knowingly making an unauthorised likeness available.
  - It also covers distributing any "algorithm, software, tool, or other technology" whose **primary purpose or function** is producing a *particular, identified* person's likeness without authorisation.
  - It exempts news, commentary, parody, documentary and fleeting use.
  - A general fitter is not aimed at one person; a shipped celebrity preset might be. ↔️
- **California.** 🧠
  - **AB 2602** (effective 1 Jan 2025) voids replica clauses unless the uses are specifically described and the performer had a lawyer or union.
  - **AB 1836** makes digital replicas of deceased personalities actionable at the greater of $10,000 or actual damages.
  - **SB 942**, the AI Transparency Act, requires latent disclosures from large generative-AI providers. Its operative date slipped to Aug 2026. ↔️
- **New York.** 🧠
  - Civil Rights Law §§50–51 protect living people against use for advertising or trade.
  - §50-f adds a 40-year post-mortem right, and a deceased-performer replica rule that a conspicuous disclaimer defeats.
  - §52-c gives a civil action for sexual deepfakes.
  - December 2025 laws added "synthetic performer" ad disclosure and heir consent for replicas of the dead. ↔️
- **Illinois** amended its Right of Publicity Act (50 years post-mortem) for digital replicas in 2024. 🧠
- **NO FAKES Act** (federal). 🧠
  - It was introduced in July 2024 and reintroduced in April 2025 (S.1367/H.R.2794), backed by SAG-AFTRA, RIAA, MPA, YouTube and OpenAI.
  - It would create a federal right against unauthorised "digital replicas" (highly realistic, readily identifiable voice or likeness), with post-mortem terms renewable up to 70 years, written time-limited licences, notice-and-takedown, liability for products "primarily designed" to replicate specific people, First Amendment exclusions and partial pre-emption.
  - **It was not enacted at my cutoff (mid-2026).** ↔️
- The **US Copyright Office** *Digital Replicas* report (July 2024) urged a federal right for everyone, not only celebrities. 🧠
- **TAKE IT DOWN Act** (signed 19 May 2025). Publishing non-consensual intimate images is a federal crime, including AI "digital forgeries". Platforms must remove them within **48 h** of a valid request, with platform duties in force from May 2026 under FTC enforcement. 🧠 Most states also have intimate- and election-deepfake laws, some of the election laws enjoined on First Amendment grounds (*Kohls v. Bonta*). ↔️
- **Pre-emption.** A December 2025 executive order targets state AI laws; its reach over likeness statutes is unclear. ↔️

**Biometric and data-protection law**
- **Illinois BIPA** (740 ILCS 14) treats a "scan of face geometry" (not a photograph) as a biometric identifier. It requires informed written consent *before* collection, a public retention policy, and destruction when the purpose ends or within 3 years of the last interaction. Damages are $1,000 per negligent and $5,000 per reckless violation, with no harm needed (*Rosenbach*, 2019); SB 2979 (2024) counts repeat scans of one person as one violation. 🧠
- **Is a fitted mesh "face geometry"?** This is contested. *Zellmer v. Meta* (9th Cir. 2024) excluded data that cannot identify a person. ↔️ Assume it is covered.
- **Texas CUBI** is AG-enforced at up to $25,000 per violation (Meta settled for $1.4B in 2024). Washington and Colorado have similar laws. 🧠
- **GDPR.** 🧠
  - Photos are personal data. They become special-category biometric data only when technically processed **to uniquely identify** someone (Art. 4(14), Art. 9, Recital 51). ↔️
  - Explicit consent must be as easy to withdraw as to give (Art. 7(3)), and the right to erasure applies.
  - The household exemption (Art. 2(2)(c)) ends once you publish to the open web (*Lindqvist*, CJEU 2003).
  - Fines reach €20M or 4 % of turnover.
- **India's DPDP Act 2023** requires free, specific, informed, unambiguous consent. Its Rules were notified in November 2025 and phase in over about 12–18 months. ↔️

**EU AI Act (Regulation (EU) 2024/1689)**
- **Timeline.** In force since 1 Aug 2024. Art. 5 bans applied from 2 Feb 2025, including untargeted scraping of facial images to build recognition databases. **Art. 50 transparency applies from 2 Aug 2026.** 🧠
- **Art. 50(2).** Providers of generators of synthetic image, audio, video or text must mark outputs machine-readably; assistive editing is exempt. 🧠
- **Art. 50(4).** Deployers must disclose **deep fakes** (Art. 3(60): content resembling existing persons that would falsely appear authentic). For evidently artistic or satirical work, a non-intrusive disclosure is enough. 🧠
- **Fines** for Art. 50 breaches reach €15M or 3 % of turnover. 🧠
- **Open source is not a shield.** The open-source exemption in Art. 2(12) **does not cover Art. 50**. 🧠
- **Does it reach this add-on?** ↔️
  - Classical least-squares fitting is probably not an "AI system" (the Commission's February 2025 guidelines exclude mathematical optimisation).
  - Neural landmark detectors and regressors probably are.
  - Meshes are not among the output types Art. 50(2) lists.
- **Dates may move.** The labelling code of practice and the November 2025 "Digital Omnibus" (which proposed an Art. 50(2) grace period) could change them. ↔️

**Other jurisdictions**
- **Germany.** Under KUG §22, portraits may be distributed only with consent, and relatives' consent is needed for 10 years after death. §23 exempts contemporary history and uncommissioned art serving a "higher interest". 🧠
- **France.** Civil Code Art. 9 grounds the *droit à l'image*. The 2024 SREN law penalises sharing AI depictions made without consent unless they are obviously synthetic (Penal Code 226-8), and penalises sexual deepfakes more heavily (226-8-1). 🧠
- **Denmark** proposed (2025) a right over one's own face, body and voice. ↔️ **Italy's** Law 132/2025 criminalises harmful deepfakes. ↔️
- **UK.** There is no image right; claims run through passing off (*Irvine v Talksport*; *Fenty v Arcadia*, the Rihanna T-shirt), privacy, UK GDPR and defamation. 🧠 Sharing intimate deepfakes became an offence in 2024; creating them became one under the Data (Use and Access) Act 2025 (check commencement). ↔️ Guernsey has a registrable image right. 🧠
- **India.** There is no statute. Delhi and Bombay High Court injunctions protect personality rights against AI cloning: Amitabh Bachchan (2022), Anil Kapoor (2023), Arijit Singh (voice, 2024) and a 2025 wave. 🧠 MeitY's October 2025 draft IT Rules would label "synthetically generated information" over ≥10 % of the display area. ↔️ (final form)
- **China.** Civil Code Art. 1019 bars IT-forged portraits, and AI-content labelling has been mandatory since 1 Sep 2025. 🧠

**Contracts and practice**
- **SAG-AFTRA.** The 2023 TV/Theatrical contract requires "clear and conspicuous", use-specific, paid consent for digital replicas; the 2025 video-game agreement added AI consent and disclosure. 🧠
- **EA's *College Football 25*** (2024) paid opted-in athletes about $1,500 plus a game copy: the consented-likeness model. 🧠
- **Tattoos are the tattoo artist's copyright.** *Alexander v. Take-Two* (2022 jury) found infringement; *Solid Oak v. 2K* (2020) found fair use. ↔️ **Projecting a third party's photo as texture reproduces it**, whereas measured geometry arguably does not. ↔️

## Numbers & reference tables

**Table 1: Post-mortem publicity terms** (statutes change; verify)

| Jurisdiction | Term after death | Notes | Badge |
|---|---|---|---|
| California | 70 years | §3344.1 | 🧠 |
| New York | 40 years | §50-f, from 2020 | 🧠 |
| Tennessee | 10 years, then while used | lapses after 2 years of non-use | 🧠 |
| Indiana / Oklahoma | 100 years | broadest | 🧠 |
| Texas / Illinois | 50 years | | 🧠 |
| Washington | 10 years (individual) / 75 years (personality) | | ↔️ |
| Florida | 40 years | | 🧠 |
| Ohio / Pennsylvania / Virginia | 60 / 30 / 20 years | | ↔️ |
| Germany (KUG) | 10 years | relatives' consent | 🧠 |
| NO FAKES (proposed) | 10 years, renewable up to 70 | not law | ↔️ |

**Table 2: Damages, fines, deadlines**

| Law | Figure | Unit | Badge |
|---|---|---|---|
| Cal. §3344 / §3344.1 | ≥750 | USD statutory minimum, or actual damages + profits | 🧠 |
| Cal. AB 1836 | ≥10,000 | USD per deceased-replica violation | 🧠 |
| Illinois BIPA | 1,000 / 5,000 | USD per negligent / reckless violation | 🧠 |
| BIPA destruction deadline | ≤3 | years after last interaction | 🧠 |
| Texas CUBI | ≤25,000 | USD per violation | 🧠 |
| TAKE IT DOWN removal | 48 | hours after valid request | 🧠 |
| TAKE IT DOWN prison | ≤2 (≤3 if minor) | years | ↔️ |
| AI Act Art. 50 | 15M / 3 % | EUR / turnover, whichever higher | 🧠 |
| GDPR upper tier | 20M / 4 % | EUR / turnover | 🧠 |
| India draft label | ≥10 | % of display area | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Classify the use before capture.** Each tier needs everything the one before it needs, plus more. 🧠
   - **Personal**: never shared.
   - **Portfolio or social**: public, non-commercial.
   - **Commercial**: client portrait, game asset, ad, stock, 3D print.
   - **Replica**: rig, expressions, voice, AI training.

   Only the personal tier can lean on the GDPR household exemption.
2. **Get a written release scoped to the tier.** 🧠 Cover what is captured (photos, video, iris or skin texture); allowed derivatives (sculpt, textured model, rig, print, animation); media, territory, duration and fee; named cloud processors; AI training as a separate default-no opt-in; banned uses (sexual, political, endorsement); the subject's approval of published likenesses; withdrawal and its effect on published work; retention of raw photos versus mesh; and death. As in SAG-AFTRA and AB 2602, describe each use specifically and re-consent for new ones.
3. **Minors** need guardian consent plus the child's assent. Never default to an animatable, public or realistic-body combination for them. **Deceased subjects** need estate consent; check Table 1 for commercial work. 🧠
4. **Celebrities.** Realistic, public and commercial use loses (*Keller*, *No Doubt*). Private practice is low-risk. Selling STLs, prints or mods of a recognisable star is not. Caricature helps against publicity claims, **not** against endorsement or deception claims. ↔️
5. **Own your reference.** Shoot it yourself (see `blender/reference-camera-setup.md`); projecting scraped photos as texture copies someone's copyright. License, omit or alter tattoos and logos in commercial work. 🧠
6. **Process locally.** Name any cloud step (Mesh to MetaHuman, generative-3D sites) in the release and check vendor training terms (see `blender/metahuman-cc-bridges.md`). 🧠
7. **Publishing realistic renders.** Add a visible credit ("Digital likeness of X, made with consent") plus IPTC digital-source-type metadata or C2PA Content Credentials (`c2patool`). Treat this as mandatory for neural-pipeline output in the EU from August 2026. ↔️
8. **Never put a realistic real person's head on sexual content** without specific documented consent. That is criminal under US federal law, in most US states, in the UK and in France. 🧠
9. **Common failures:** a "sculpt" consent stretched to a rigged, sold asset; a bystander fitted from a group photo; raw photos packed into a shared .blend; non-commercial FLAME or InsightFace weights in a paid job (see `blender/blender-face-addons.md`). 🧠

## Algorithmic implications

Statistical sigmas do not apply here. The priors are **policy defaults** that the engine enforces. 🧠

- **`ConsentRecord`**, stored as a JSON sidecar and a .blend custom property, holds:
  - `subject_pseudonym`, `signer_role` (subject / guardian / estate), `consent_text_version`, `signed_at`, `expires_at`;
  - `jurisdiction_tags`, `photo_sha256[]`, `retention_days`, `revocation_contact`;
  - `scopes` as bitflags: `CAPTURE, RECONSTRUCT, STORE_RAW, RENDER_PRIVATE, PUBLISH_NONCOMMERCIAL, COMMERCIAL, PRINT_3D, RIG_ANIMATE, CLOUD_PROCESSING, AI_TRAINING`.
- **Default-deny gates.** Solving and fitting need `RECONSTRUCT`, ARKit or expression export needs `RIG_ANIMATE`, and commercial export needs `COMMERCIAL`.
- **Defaults** (tune with counsel):
  - self-consent age ≥18;
  - commercial consent re-confirmed every 12 months;
  - raw-photo deletion reminder 90 days after the project closes, with a hard cap of 3 years (the BIPA ceiling);
  - embeddings held in RAM only;
  - `AI_TRAINING` and `CLOUD_PROCESSING` off.
- **Age by attestation**, not ML estimation, which is itself biometric processing and error-prone.
- **Multi-face guard.** With more than one detected face, the user picks the subject; others are never fitted or stored. Offer no gallery search or "who is this".
- **Provenance on export.**
  - Write `likeness.consent_id`, `likeness.synthetic=true` and `likeness.scopes` into custom properties and glTF `extras`.
  - Write XMP/IPTC metadata on renders, with optional C2PA signing.
  - Turn the visible disclosure overlay on by default for realistic public renders. ↔️
- **`Purge subject`** deletes packed images, landmark caches and temp files and writes a hash-only receipt. **Revocation** scans project .blend files for the `consent_id`.
- **Licence guard.** Tag each component with its licence and block `COMMERCIAL` export if a non-commercial component touched the result.
- **Ship no named real-person presets or sample data.** Use synthetic or consented demo subjects only, because the ELVIS and NO FAKES clauses target tools built for identified people.

## Disagreements, myths & open questions

- **Myths.** 🧠
  - *"It's art, so it's protected."* Realism is the weak point of transformative use.
  - *"Stylised means safe."* *White v. Samsung* says otherwise.
  - *"Public photos are free."* Copyright, publicity rights and the GDPR still apply.
  - *"Open source is exempt from the AI Act."* Not from Art. 50.
  - *"The dead have no rights."* Post-mortem terms run 10–100 years.
- **Contested.** ↔️
  - Are meshes and landmarks biometric data? It turns on purpose and identifiability (Recital 51, *Zellmer*).
  - Does Art. 50 reach CGI made by classical fitting? Probably not, but neural steps change that.
  - First Amendment limits on broad replica rights.
  - Whether consent survives death: SAG-AFTRA terms say yes unless limited.
- **Open (time-sensitive):** NO FAKES votes and pre-emption scope; the Digital Omnibus outcome and labelling code; India's final IT Rules; Danish enactment; a UK personality right; the December 2025 US executive order.

## Sources

No web harvest or earlier draft existed for this topic, so no URLs are cited. Related notes: `reconstruction/identity-embeddings.md`, `blender/metahuman-cc-bridges.md`, `blender/blender-face-addons.md`, `community/ai-assisted-sculpting.md`, `reconstruction/photogrammetry-heads.md`.

**Further reading (by name, not yet linked)**
- Regulation (EU) 2024/1689 (AI Act), Arts. 2(12), 3(60), 5, 50, 99; GDPR Arts. 2, 4(14), 7, 9, Recital 51
- Tennessee ELVIS Act 2024; California Civil Code §§3344, 3344.1, AB 2602, AB 1836, SB 942; New York Civil Rights Law §§50–51, 50-f, 52-c; Illinois BIPA (740 ILCS 14)
- NO FAKES Act of 2025; TAKE IT DOWN Act (2025); U.S. Copyright Office, *Copyright and Artificial Intelligence, Part 1: Digital Replicas* (2024)
- *Comedy III v. Saderup* (Cal. 2001); *White v. Samsung* (9th Cir. 1992); *Keller v. EA* (9th Cir. 2013); *Hart v. EA* (3d Cir. 2013); *Kirby v. Sega* (2006); *Lohan v. Take-Two* (N.Y. 2018)
- Kunsturhebergesetz §§22–23; *Fenty v Arcadia* [2015] EWCA Civ 3
- J. Thomas McCarthy, *The Rights of Publicity and Privacy*; Jennifer E. Rothman, *The Right of Publicity: Privacy Reimagined for a Public World* (2018)
- SAG-AFTRA 2023 TV/Theatrical and 2025 Interactive Media agreements; C2PA specification; IPTC Digital Source Type vocabulary
