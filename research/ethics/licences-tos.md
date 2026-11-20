# Licences and platform terms

> A photo→3D likeness is clean only when three separate permission chains are all clean: the subject's consent (`ethics/consent-likeness-law.md`); the copyright in every photograph, which belongs to whoever pressed the shutter rather than to the subject, and which public visibility on a platform never grants; and the licence of every model, dataset and template that touches the fit. The third chain is where open face tooling usually fails. Code is MIT, BSD or Apache, but FLAME, BFM, InsightFace weights, dlib's 68-point model and most research regressors carry non-commercial or no-redistribution terms, and converting them to ONNX does not lift those terms. An add-on that imports `bpy` should be GPL-3.0-or-later, but the GPL does not reach the meshes and renders it makes, and a bpy-free numpy engine can stay permissive. Instagram, Facebook, X, TikTok and LinkedIn all forbid automated collection, so the clean route for social photos is the subject's own data export plus each photographer's permission. No harvest or earlier draft existed, so this is expert knowledge as of mid-2026. It is not legal advice.
>
> Evidence status: 0 ✅ / 0 📄 / 64 🧠 / 32 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Models, templates and datasets**
- **The asset licence decides, not the code licence.** Converting weights to ONNX, quantising, pruning or fine-tuning them does not change their terms. 🧠
- **FLAME (MPI-IS).** The model is a registration download for non-commercial scientific research, and redistributing it is forbidden. MPI-style terms also exclude pornographic, military and surveillance uses, and they treat training commercial systems or producing commercial artefacts with the model as commercial use (paraphrase). Commercial licences go through MPI or Meshcapade. 🧠 A CC BY 4.0 "FLAME 2023 Open" is reported in sibling notes but unconfirmed. ↔️
- **BFM 2009 / 2017 / 2019 (University of Basel).** A signed agreement for non-commercial research only, no redistribution, and a separate agreement for commercial use. 🧠
- **Other 3D morphable models** (LSFM, LYHM/Headspace, FaceScape, FaceWarehouse, UHM, HIFI3D++) are application-gated and academic. 🧠 FaceScape also limits which subjects may appear in publications. ↔️
- **Permissive bases are scarce.**
  - MPFB2/MakeHuman: GPL-3.0-or-later code, a CC0 base mesh and targets, and some CC-BY packs. ↔️
  - ICT-FaceKit: MIT. ↔️
  - MediaPipe's canonical face OBJ (468 vertices with UVs): Apache-2.0. 🧠
- **Landmark detectors.**
  - **MediaPipe Face Landmarker.** Apache-2.0 code. Its model cards are believed to state Apache-2.0 for the weights and to list identification as out of scope. ↔️
  - **dlib.** Boost-licensed code, but `shape_predictor_68_face_landmarks.dat` was trained on iBUG 300-W, whose terms exclude commercial use. 🧠
  - **InsightFace.** MIT code; its pretrained packs (buffalo_l, antelopev2, including the 2d106 and 1k3d68 landmarkers) are "non-commercial research only", with paid licences available. 🧠
  - **FAN.** BSD-3 code; weights trained on research datasets. ↔️
- **Hidden-dependency traps.**
  - BiSeNet face-parsing weights ship with MIT code but were trained on CelebAMask-HQ, which is non-commercial. 🧠
  - Ultralytics YOLO, including "YOLOv8-face", is AGPL-3.0 for code and weights; closed use needs an Enterprise licence. 🧠
  - Depth Anything V2 Base/Large is CC BY-NC 4.0. ↔️
- **Datasets.**
  - CelebA and CelebAMask-HQ: non-commercial research.
  - FFHQ: a CC BY-NC-SA 4.0 compilation of individually licensed Flickr images.
  - WebFace42M: non-commercial.
  - MS-Celeb-1M was withdrawn in 2019 and MegaFace in 2020. 🧠
- **CC licences on Flickr photos never covered biometrics.** The BIPA suits over IBM's *Diversity in Faces* (built from YFCC100M) show this; outcomes were mixed. ↔️
- **Runtimes are clean and GPL-3-compatible.** 🧠
  - The ONNX spec and package: Apache-2.0.
  - ONNX Runtime: MIT.
  - OpenCV ≥4.5: Apache-2.0.
  - NumPy: BSD-3.
  - PyTorch: BSD-style.
  - The `mediapipe` wheel: Apache-2.0.
- **Use-restricted licences** (OpenRAIL-M, Tencent Hunyuan's reportedly excluding the EU, UK and South Korea, Meta's Sapiens) pass their rules downstream and are not OSI-open. ↔️
- **Are weights copyrightable?** US law may find no human authorship. *Getty Images v. Stability AI* (UK High Court, Nov 2025) reportedly held that trained weights are not an "infringing copy". ↔️ Click-through and registration terms still bind whoever accepted them, as contracts. 🧠

**GPL and Blender add-ons**
- **The Blender Foundation's position.** Blender is GPL-2.0-or-later. The Foundation holds that distributed add-ons that use `bpy` must be GPL-compatible; they may be sold, and buyers may redistribute them. This is untested in court. ↔️
- **Outputs are not GPL.** Meshes, .blend files and renders carry only the licences of assets embedded in them, such as a template or packed photos. Ship a CC0 template so outputs stay unencumbered. 🧠
- **Compatibility.** 🧠
  - MIT, BSD, BSL-1.0 and Apache-2.0 can join a GPL-3 work; Apache-2.0 cannot join GPLv2-only.
  - AGPL-3.0 combines with GPLv3 under §13.
  - Non-commercial terms are "further restrictions", so NC *code* can never be merged in.
- **Correction to `blender/blender-extensions-packaging.md`.** Separate data files on the same medium count as GPL "mere aggregation", so the GPL alone does not bar bundling NC weights. Three other things do: the assets' own no-redistribution clauses, the Extensions free-content policy, and the trap it sets for downstream commercial users. ↔️
- **Extensions platform.** The manifest declares SPDX licences, with GPL-3.0-or-later recommended. Bundled assets must be free, wheels must be bundled rather than pip-installed at runtime, and network use needs a declared permission. The rules on downloading model weights at runtime are unconfirmed. ↔️
- **Closed native cores** (FaceBuilder-style) rely on a "separate program" argument. The FSF treats a plugin that shares the host's address space as one combined work. ↔️
- **Split licensing.** A numpy engine with no `bpy` import can be MIT or Apache-2.0 (with a patent grant) and reused outside Blender. The Blender glue is GPL-3.0-or-later, and the extension ships under GPL with the engine's notice kept. 🧠
- **Selling.** Licence keys and paid support are fine, but no term may bar buyers from redistributing. 🧠 Blender Market was reportedly renamed Superhive in 2025. ↔️

**Platform terms**
- **Instagram's Terms of Use** forbid unauthorised or automated collection of information without express permission (paraphrase). Users license their content to *Meta*; third parties get nothing. 🧠
- **No API route to someone's photos.** The Instagram Basic Display API was retired on 4 Dec 2024, and the Graph API serves only business and creator accounts' own media. ↔️
- **The sanctioned route is the subject's own export** through Accounts Center, "Download your information", which also covers Facebook and Threads. 🧠
- **X's terms** ban scraping without prior written consent and reportedly add liquidated damages. ↔️ TikTok, LinkedIn, Pinterest and Reddit also prohibit automated collection. 🧠
- **US scraping case law.**
  - *Van Buren* (2021) and *hiQ v. LinkedIn* (9th Cir. 2022) narrowed the CFAA for public data, yet hiQ lost on breach of contract and settled (2022). 🧠
  - In *Meta v. Bright Data* (N.D. Cal. 2024), logged-out scraping was held not bound by Meta's terms. ↔️
  - Scraping while logged in means you accepted the terms. 🧠
- **Regulators' red line is face scraping.** Clearview AI was fined in Italy, Greece, France and the Netherlands. The EU AI Act Art. 5(1)(e) has banned untargeted facial scraping for recognition databases since February 2025. 🧠
- **Creative Commons 4.0 §2(b)(1) does not license publicity, privacy or personality rights.** A CC BY portrait still needs the sitter's consent for a likeness. 🧠
- **Stock licences.** "Editorial use only" bars commercial use; releases exclude sensitive uses and newer ones add AI clauses. ↔️

**Copyright of reference photographs**
- **Who owns a photo.** The photographer does, or their employer for a work made for hire. The subject owns nothing unless they took the photo themselves. 🧠 Agencies have sued celebrities for posting paparazzi shots of themselves (e.g. *Xclusive-Lee v. Hadid*, E.D.N.Y. 2019, dismissed on registration grounds). 🧠
- **Facts against expression.** Head shape and proportions are facts. A photo's pose, lighting, angle and timing are expression (*Mannion v. Coors*, S.D.N.Y. 2005). 🧠
  - A sculpture copying a photograph infringed in *Rogers v. Koons* (2d Cir. 1992). 🧠
  - *AWF v. Goldsmith* (US 2023) rejected fair use for commercially licensing a photo-derived portrait. 🧠
- **Texture projection reproduces the photo; eyeballing it in the viewport is private study.** Study use is likely covered by fair use, UK CDPA s.29 or EU private-copy rules. ↔️ Distributing a .blend with packed images distributes copies. 🧠
- **Text-and-data mining.**
  - EU DSM Directive: Art. 3 covers research; Art. 4 allows commercial mining unless the rightsholder opts out by machine-readable means.
  - UK CDPA s.29A: non-commercial mining only.
  - Japan Art. 30-4: broad. 🧠
  - *Kneschke v. LAION* (LG Hamburg, 2024) applied the research exception. ↔️
  - 2025 US training rulings split on fair use (*Thomson Reuters v. Ross* found none). ↔️
- **Copyright metadata.** Under DMCA §1202, knowingly removing copyright management information is actionable. Keep Artist and Copyright fields; strip GPS. 🧠
- **US remedies depend on registration.** Statutory damages and fees need timely registration (17 U.S.C. §412). 🧠

## Numbers & reference tables

**Table 1: Component licence matrix** (terms change per release)

| Component | Code | Weights / data | Commercial | Bundle in extension? | Badge |
|---|---|---|---|---|---|
| MediaPipe Face Landmarker | Apache-2.0 | Apache-2.0 (model card) | yes | download, pin SHA-256 | ↔️ |
| MediaPipe canonical face OBJ | Apache-2.0 | n/a | yes | yes, with NOTICE | 🧠 |
| ONNX / ONNX Runtime | Apache-2.0 / MIT | n/a | yes | yes (wheel) | 🧠 |
| dlib 68-point | BSL-1.0 | 300-W, non-commercial | no | no | 🧠 |
| InsightFace packs | MIT | non-commercial; paid licence | no | no | 🧠 |
| 3DDFA_V2 | MIT | BFM + 300W-LP, non-commercial | no | no | 🧠 |
| DECA / EMOCA / MICA | MPI non-commercial | FLAME | no | no | 🧠 |
| FLAME 2020/2023 | n/a | MPI non-commercial | via licence | no | 🧠 |
| "FLAME 2023 Open" | n/a | CC BY 4.0? | maybe | maybe | ↔️ |
| BFM 2009/2017/2019 | n/a | Basel non-commercial | via agreement | no | 🧠 |
| MPFB2 / MakeHuman | GPL-3.0+ | CC0 base; some CC-BY | yes | yes | ↔️ |
| ICT-FaceKit | MIT | MIT | yes? | after check | ↔️ |
| BiSeNet face-parsing | MIT | CelebAMask-HQ, non-commercial | no | no | 🧠 |
| SAM / SAM 2 | Apache-2.0 | Apache-2.0 | yes | download | 🧠 |
| Ultralytics YOLO(-face) | AGPL-3.0 | AGPL-3.0 | copyleft or paid | avoid | 🧠 |
| FFHQ / CelebA | n/a | CC BY-NC-SA 4.0 / research | no | no | 🧠 |

**Table 2: Photograph copyright terms** (default rules; older works have transitional rules)

| Jurisdiction | Category | Term | Badge |
|---|---|---|---|
| US | photos since 1978 | life + 70 y; work for hire 95 y from publication / 120 y from creation | 🧠 |
| EU / UK | original photographs | life + 70 y | 🧠 |
| Germany / Austria | simple photos (*Lichtbilder*) | 50 y from publication or production | 🧠 |
| Italy / Spain | simple photos | 20 y / 25 y | 🧠 |
| Canada / Japan | all works | life + 70 y (from Dec 2022 / Dec 2018) | 🧠 |
| China | photographic works | life + 50 y (2020 amendment) | ↔️ |
| India | photographs | 60 y from publication | 🧠 |

**Table 3: Exposure figures**

| Rule or case | Figure | Unit | Badge |
|---|---|---|---|
| 17 U.S.C. §504(c) | 750–30,000; ≤150,000 if wilful | USD per work | 🧠 |
| DMCA §1203 (copyright-information removal) | 2,500–25,000 | USD per violation | 🧠 |
| X terms, liquidated damages | 15,000 | USD per 1M posts accessed in 24 h | ↔️ |
| Clearview AI: Italy / Greece / France | 20M each (2022) | EUR | 🧠 |
| Clearview AI: Netherlands | 30.5M (2024) | EUR | 🧠 |
| Clearview AI: UK ICO | 7.5M (2022); appeals contested | GBP | ↔️ |
| Instagram Basic Display API end of life | 4 Dec 2024 | date | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Log the provenance of every image before fitting.** Record the photographer; the rights basis (shot by the artist, a selfie by the subject, a photographer's licence, a CC licence with its version, or unknown); the source; and the subject's consent ID. A consenting subject's camera roll often holds friends' photos, which the friends own. 🧠
2. **Social media.** The subject exports their own data through Accounts Center and gives you the files. Never scrape, never bulk-download through a logged-in session, and never take the subject's password. 🧠
3. **Measure, don't copy.** Fitting landmarks and silhouettes extracts facts and carries low risk. Projecting or baking texture copies pixels, so allow it only from photos with a known rights basis. In finished art, don't recreate a specific photo's pose, expression and lighting. 🧠
4. **Choose the stack by licence first.** 🧠
   - **Default stack:** MediaPipe, then the numpy fitter, then an MPFB2 CC0 base, then Multires.
   - **Opt-in research backends** (FLAME, BFM, DECA, MICA, InsightFace): the user downloads them under their own registration, and the project is flagged non-commercial.
5. **Licence the add-on correctly.** 🧠
   - Use `license = ["SPDX:GPL-3.0-or-later"]`, SPDX headers in every file, and a NOTICE listing each wheel and asset.
   - Put the engine package under MIT or Apache-2.0.
   - Never port code from repositories with NC or unknown licences. Reimplement from the papers: equations are not copyrightable, code is.
6. **Bundle no FLAME landmark-embedding files**; they are FLAME data. 🧠 MediaPipe topology and indices need only a NOTICE. 🧠
7. **What goes wrong** 🧠
   - A paid client head fitted with a FLAME regressor.
   - A dlib model inside a commercial plugin.
   - Packed photos inside a sold .blend.
   - A sculpt that copies a famous portrait.
   - An "Instagram import" feature, which breaches the terms and misuses the trademark.
   - Stripping EXIF copyright fields along with GPS.

## Algorithmic implications

Policy defaults, not statistical priors; sigmas do not apply. 🧠
- **`LicenceTag`**, one per component and per image:
  - `{spdx_or_custom, commercial_ok: true|false|null, redistributable, attribution, share_alike, use_restrictions[], territory_excluded[], source, version, sha256, accepted_at}`;
  - `null` (unknown) counts as `false` for export.
- **Taint propagation.** `result.commercial_ok` is the AND over every component the run used: detector, prior, template, regressor, segmenter and photos. Track `fit_only` and `texture` paths separately. Whether NC detector outputs taint geometry is contested, so default to conservative and allow a logged user attestation. ↔️
- **Photo gate.** `rights_basis = unknown` allows a private-study fit with a warning, and blocks texture bake, packing and export.
- **Model registry entries:** `{name, url, sha256, bytes, licence_text_hash, commercial_ok, needs_network}`. Show the licence and require a click before downloading; store the timestamp.
- **Inputs.** Import local files only: no URL or social importers, no account logins.
- **Metadata.**
  - Copy EXIF/IPTC Artist and Copyright into a sidecar and into glTF `extras`.
  - Strip GPS and serial numbers by default.
  - Auto-generate `ATTRIBUTION.txt` for CC-BY assets.
- **CI checks.** Fail on any bundled file without an SPDX entry, and run fitting tests on the CC0 template alone.

## Disagreements, myths & open questions

- **Myths.** 🧠
  - *"Public on Instagram means free to use."* Copyright, the platform's terms and personal-data law all still apply.
  - *"The subject's consent covers the photos."* It does not cover the photographer's copyright.
  - *"GPL infects my sculpt."* Outputs are not covered.
  - *"ONNX conversion or fine-tuning washes the licence."* It does not.
  - *"A CC BY portrait is cleared for a likeness."* Publicity rights are excluded.
- **Contested.** ↔️
  - Whether weights are copyrightable.
  - Whether outputs of non-commercial models are restricted: MPI-style wording says yes.
  - What counts as "non-commercial": a portfolio piece, Patreon, or a monetised tutorial? Creative Commons' 2009 study found no consensus.
  - Closed cores and aggregated NC data under the GPL.
  - Contract claims against logged-out scraping.
- **Open and time-sensitive:** the FLAME 2023 Open terms; each MediaPipe model card; the Extensions rules on runtime model downloads; the current X terms; appeals in *Kneschke* and *Getty*; KeenTools' EULA on exported meshes.

## Sources

No harvest or draft existed, so no URLs are cited. Sibling harvests' licence URLs: `blender/blender-extensions-packaging.md`, `reconstruction/multi-view-fitting.md`, `reconstruction/identity-embeddings.md`.

**Further reading (by name, not yet linked)**
- FLAME licence (MPI-IS); Basel Face Model licence agreement; InsightFace README; MediaPipe Face Landmarker model card; dlib 68-point model notes
- GNU GPL v3 and AGPL v3; FSF *Frequently Asked Questions about the GNU Licenses*; Blender Foundation licence FAQ; Blender Extensions policies; SPDX License List
- Creative Commons 4.0 legal code; Creative Commons, *Defining "Noncommercial"* (2009); OpenRAIL-M
- Instagram Terms of Use; Meta Platform Terms; X Terms of Service; LinkedIn User Agreement
- *Van Buren v. United States* (2021); *hiQ Labs v. LinkedIn* (9th Cir. 2022); *Meta Platforms v. Bright Data* (N.D. Cal. 2024)
- *Rogers v. Koons* (2d Cir. 1992); *Andy Warhol Foundation v. Goldsmith* (2023); *Mannion v. Coors* (S.D.N.Y. 2005)
- Directive (EU) 2019/790 Arts. 3–4; UK CDPA ss. 29, 29A; 17 U.S.C. §§412, 504, 1202–1203; *Kneschke v. LAION* (LG Hamburg, 2024); *Getty Images v. Stability AI* (EWHC, 2025)
