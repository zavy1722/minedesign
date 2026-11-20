# Engine requirements: consent, privacy, law & licensing

**For:** the team designing the numpy-only fitting engine and the Blender add-on (camera solve, landmark bundle adjustment, template warp, silhouette and profile fit, shape keys, texture projection).
**Sources:** [CL] = `research/ethics/consent-likeness-law.md`, [BP] = `research/ethics/biometric-privacy.md`, [LT] = `research/ethics/licences-tos.md`, plus their tables in `research/data/<topic>.json`. Verification-log corrections (2026-11-20) are applied. **(editor)** marks a synthesis across notes; the area guide is `research/ethics/README.md`, and its contradictions are labelled C1–C14.
**Badges:** ✅ verified · 📄 single-sourced · 🧠 unverified expert knowledge, **provisional** · ↔️ contested.
**On sigmas:** this area supplies **no statistical priors**. Every constant below is a policy default (σ = n/a). Where it says "bounds", that is the allowed tuning range. Treat any 🧠 constant as provisional and tune it with counsel. None of this is legal advice.

## 1. Architecture constraints

| ID | Requirement | Badge | Cite |
|---|---|---|---|
| A1 | **Split licensing.** The engine package never imports `bpy` and is MIT or Apache-2.0. The Blender glue is `license = ["SPDX:GPL-3.0-or-later"]` (the Extensions platform requires GPL-3.0-or-later). Every file gets an SPDX header, and a NOTICE lists each wheel and asset. | 📄 (GPL-3 rule) / 🧠 | [LT] |
| A2 | **Policy logic lives in the bpy-free engine.** The consent gates, data classes, licence taint and retention clocks are pure Python, unit-tested headless. The glue only calls them. | 🧠 (editor) | [LT], [BP] |
| A3 | **Local only.** `network_enabled = False`. Any network call needs the `CLOUD_PROCESSING` scope and a per-call confirmation naming the host, data classes and scope. The add-on also checks `bpy.app.online_access` and declares the `network` permission. | 🧠 / 📄 (online_access) | [BP], `blender/blender-extensions-packaging.md` |
| A4 | **Zero-download path.** The whole pipeline (landmarks → camera solve → BA → warp → silhouette → shape keys) runs with **no downloaded component**: landmarks entered manually or imported, plus the bundled CC0 template. Detector downloads are optional. The Extensions platform bars "requiring externally downloaded components". | 📄 / ↔️ (download rules) | [LT], C8 |
| A5 | **Inputs are local files only.** No URL or social-platform importers, no account logins. | 🧠 | [LT] |
| A6 | **Never bundle non-commercial or no-redistribution weights or data**, and never port code from repositories with NC or unknown licences. Reimplement from the papers instead: equations are not copyrightable. Assets bundled in the extension must be **CC0**. | 📄 (CC0) / 🧠 | [LT] |
| A7 | **No telemetry.** Error reports strip images, arrays and file paths. CI monkeypatches `socket.socket.connect` to raise during a full pipeline run. | 🧠 | [BP] |
| A8 | **No named real-person presets or sample data.** Demo subjects are synthetic or consented. The ELVIS Act covers tools whose "primary purpose or function" is producing an individual's likeness (📄); whether a general fitter is covered is ↔️. | 📄 / ↔️ | [CL] |

## 2. Data formats

**2.1 `ConsentRecord`**, stored as a JSON sidecar plus a .blend custom property **(editor: CL and BP schemas merged, C4)**
```
consent_id, subject_pseudonym, signer_role ∈ {self, subject, guardian, estate},
consent_text_version, method, signed_at, expires_at, jurisdiction_tags[],
photo_sha256[], retention_days, revocation_contact,
scopes: bitflags {CAPTURE, RECONSTRUCT, STORE_RAW, TEXTURE, RENDER_PRIVATE,
         PUBLISH_NONCOMMERCIAL, COMMERCIAL, PRINT_3D, RIG_ANIMATE,
         CLOUD_PROCESSING, IDENTITY_CHECK, AI_TRAINING}
```
- How BP's scopes map onto these flags: sculpt→RECONSTRUCT, texture→TEXTURE, publish→PUBLISH_NONCOMMERCIAL, commercial→COMMERCIAL, animate→RIG_ANIMATE, print→PRINT_3D, cloud→CLOUD_PROCESSING, identity_check→IDENTITY_CHECK, train→AI_TRAINING.
- BP's `subject_is_user` bypass becomes `signer_role = self`. A self-attested record is still required, so that export provenance exists. 🧠 [CL][BP]

**2.2 Data classes.** Every stored object carries `data_class ∈ {PERSONAL_IMAGE, BIOMETRIC_GEOMETRY, BIOMETRIC_TEMPLATE, LIKENESS_ASSET, AGGREGATE_PRIOR}` in a project manifest, and the purge operators act by class. 🧠 [BP]

| Engine artifact | Class | Persistence default | Badge |
|---|---|---|---|
| Source photos | PERSONAL_IMAGE | external encrypted folder; working copies EXIF-stripped | 🧠 |
| Per-photo 2D landmarks (68–478 pts), crops, heatmaps | BIOMETRIC_GEOMETRY | session only (`cache_ttl_days = 0`) | ↔️ |
| Camera solve, BA landmark 3D points, 3DMM or shape coefficients | BIOMETRIC_GEOMETRY | project only, consent-scoped | ↔️ |
| Fitted mesh, identity shape keys, sculpt | BIOMETRIC_GEOMETRY | consent-scoped | ↔️ |
| Projected or baked albedo (iris detail) | LIKENESS_ASSET | consent-scoped; needs `TEXTURE` + photo rights | ↔️ |
| Recognition embedding | BIOMETRIC_TEMPLATE | RAM only, never persisted | 🧠 |
| Template mean / PCA prior | AGGREGATE_PRIOR | bundle only if its licence allows | 🧠 |

[BP]. The second-row grouping (BA points, camera solve) is (editor).

**2.3 `LicenceTag`**, one per component and per image:
`{spdx_or_custom, commercial_ok: true|false|null, redistributable, attribution, share_alike, use_restrictions[], territory_excluded[], source, version, sha256, accepted_at}`. A `null` value counts as `false` at export. 🧠 [LT]

**2.4 `PhotoRecord`** **(editor: LT + BP)**
`{sha256, rights_basis ∈ {self_shot, subject_selfie, photographer_licence, cc_licence, public_domain, unknown}, photographer_artist, copyright (EXIF/IPTC, preserved), licence: LicenceTag, consent_id, exif_intrinsics: {FocalLength, FocalLengthIn35mmFilm, Make, Model, PixelXDimension, PixelYDimension, Orientation}}`. 🧠 [LT][BP]

**2.5 Model registry entry.** `{name, url, sha256, bytes, licence_text_hash, commercial_ok, needs_network, is_ml}`. Before any download, show the licence and require a click, and store the timestamp. `is_ml` is (editor), for C13. 🧠 [LT]

**2.6 Audit log.** Append-only JSONL with `{event, time, data_class, sha256}`. It never holds pixels or coordinates. Purges write a receipt containing only hashes. 🧠 [BP][CL]

**2.7 Export provenance.**
- Write `likeness.consent_id`, `likeness.synthetic = true`, `likeness.scopes`, the photographer's Artist and Copyright (for texture paths) and the component LicenceTags into custom properties and glTF `extras`.
- Write XMP/IPTC digital-source-type metadata on renders; C2PA (`c2patool`) is optional.
- Generate `ATTRIBUTION.txt` for CC-BY components.

🧠 / ↔️ [CL][LT]

## 3. Default-deny gates

| Operation | Requires | Badge | Cite |
|---|---|---|---|
| Landmark detection, camera solve, BA, template warp, silhouette or profile fit | `RECONSTRUCT`; a current (unexpired) record; each photo's sha256 listed in `photo_sha256[]` | 🧠 | [CL][BP] |
| Identity (fit) shape keys | `RECONSTRUCT` | 🧠 (editor) | [CL] |
| Expression, FACS or ARKit shape keys or rig export | `RIG_ANIMATE` | 🧠 | [CL] |
| Texture projection or bake | `TEXTURE`; `rights_basis ≠ unknown` | 🧠 | [BP][LT] |
| Pack images or store raw photos in the project | `STORE_RAW`; `rights_basis ≠ unknown` | 🧠 | [CL][LT] |
| Identity score | `IDENTITY_CHECK`; 1:1 against the same project's reference photos only | 🧠 | [BP] |
| Any network call | `CLOUD_PROCESSING`; `network_enabled`; `bpy.app.online_access` | 🧠 / 📄 | [BP] |
| Public render export | `PUBLISH_NONCOMMERCIAL` or `COMMERCIAL`; disclosure overlay on | ↔️ | [CL] |
| Commercial export | `COMMERCIAL`; `result.commercial_ok == true` | 🧠 | [CL][LT] |
| STL or print export | `PRINT_3D` | 🧠 | [CL] |
| Dataset or training export | `AI_TRAINING` | 🧠 | [CL] |

With `rights_basis = unknown`, a private-study fit is allowed with a warning, but texture bake, packing and export are blocked. 🧠 [LT]

## 4. Numeric defaults (σ = n/a; policy constants)

| Parameter | Default | Unit | Bounds | Legal anchor | Badge | Cite |
|---|---|---|---|---|---|---|
| `min_self_consent_age` | 18 | years | jurisdiction-tunable | below this, guardian consent + child assent | 🧠 | [CL] |
| `commercial_consent_reconfirm` | 12 | months | ≤12 | SAG-AFTRA / AB 2602 logic | 🧠 | [CL] |
| `cache_ttl_days` | 0 | days | 0–30 | minimisation | 🧠 | [BP] |
| `raw_photo_delete_after_purpose` | 45 | days | +45 once, logged (max 90) | Colorado | 📄 | [BP]; C1 (editor) |
| `raw_photo_reminder` | at close; [CL] says 90 | days | ≤ due date | CL's 90-day figure kept as the outer bound | 🧠 | [CL]; C1 |
| `retention_after_purpose_days` | 365 | days | outer bound only | CUBI ≤1 yr | 🧠 | [BP] |
| `max_days_since_last_interaction` | 730 | days | hard cap | Colorado 24 months 📄; BIPA 3 yr 🧠 | 📄 | [BP] (replaces CL's 3 yr) |
| `expiry_warning_days` | 30 | days | — | — | 🧠 | [BP] |
| `max_faces_auto_fitted_per_photo` | 1 | count | fixed | never fit bystanders | 🧠 | [CL] |
| `identity_match_mode` | 1:1 | enum | no 1:N | avoid building a recognition capability | 🧠 | [BP] |
| `persist_embeddings` | false | bool | never | embeddings can be inverted | 🧠 | [BP][CL] |
| `network_enabled`, `telemetry` | false, false | bool | per-call opt-in | developer stays out of collection | 🧠 | [BP] |
| `AI_TRAINING`, `CLOUD_PROCESSING` | off | flag | explicit opt-in | — | 🧠 | [CL] |
| `disclosure_overlay_realistic_public` | on | flag | — | AI Act Art. 50(4), deception statutes | ↔️ | [CL] |
| `disclosure_overlay_area` | not set | % of frame | India draft says ≥10 % | not law yet | ↔️ | [CL] |
| `unknown_commercial_ok` | false | bool | fail closed | — | 🧠 | [LT] |

Reference deadlines that the purge and revocation operators must be able to meet (not engine constants):
- GDPR subject-request reply within 1 month (+2). 🧠 [BP]
- GDPR breach notice within 72 h, if a cloud backend ever exists. 🧠 [BP]
- TAKE IT DOWN removal within 48 h, for hosts. 🧠 [CL]

## 5. Landmark schemes, templates and component licences

The landmark adapter must accept **any** scheme. Each landmark set records the detector's registry entry, so taint and `is_ml` propagate. **(editor)**

| Scheme / asset | Points | Code / weights | `commercial_ok` | Ship | Badge | Cite |
|---|---|---|---|---|---|---|
| Manual or imported landmarks | any | n/a | true | built in | 🧠 (editor) | A4 |
| MediaPipe Face Landmarker | 478 + 52 blendshape scores | Apache-2.0 / Apache-2.0 per model card (official card not retrieved) | true (verify) | optional download, SHA-256 pinned | ↔️ | [LT] |
| MediaPipe canonical face OBJ | 468 vertices + UVs | Apache-2.0 | true | NOTICE; bundling against the CC0 rule is open (C7) | 🧠 / ↔️ | [LT] |
| MPFB2 / MakeHuman base mesh and targets | — | GPL-3.0+ code / CC0 base | true | **bundle (default template)**; CC-BY packs excluded | 📄 | [LT] |
| dlib 68-point | 68 | BSL-1.0 / iBUG 300-W NC | false | never | 🧠 | [LT] |
| InsightFace 2d106 / 1k3d68 (buffalo_l, antelopev2) | 106 / 68 | MIT / NC (paid licence) | false | user download only | 🧠 (📄 in `reconstruction/identity-embeddings.md`) | [LT] |
| FAN (face-alignment) | — | BSD-3 / research datasets | null → false | no | ↔️ | [LT] |
| 3DDFA_V2 | dense | MIT / BFM + 300W-LP NC | false | never | 🧠 | [LT] |
| FLAME 2017–2023 and its landmark-embedding files | — | MPI NC, no redistribution | false | never; user path only | 🧠 | [LT] |
| FLAME 2023 Open | — | CC BY 4.0 (geometry); texture CC BY-NC-SA 4.0 | true with attribution (geometry) | user download (CC BY is not CC0) | ↔️ [LT] / 📄 `reconstruction/flame-model.md` | C6 |
| BFM 2009/2017/2019 | — | Basel NC agreement | false | never | 🧠 | [LT] |
| BiSeNet face-parsing (silhouette masks) | — | MIT / CelebAMask-HQ NC | false | never | 🧠 | [LT] |
| SAM / SAM 2 (silhouette masks) | — | Apache-2.0 / Apache-2.0 | true | optional download | 🧠 | [LT] |
| Ultralytics YOLO-face | — | AGPL-3.0 | conditional | avoid | 🧠 | [LT] |
| Depth Anything V2 | — | Small Apache-2.0; Base/Large CC BY-NC 4.0 | Small only | Small, download | ↔️ | [LT] |

**Taint propagation.** `result.commercial_ok` is the AND over every component used in the run: detector, prior, template, regressor, segmenter and photos. Track `fit_only` and `texture` paths separately. Whether non-commercial detector outputs taint the geometry is ↔️: default to conservative, and allow a user attestation that is logged. 🧠 / ↔️ [LT]

**Warn at enable, block at export.** When an NC model is enabled in a commercial project, warn; at `COMMERCIAL` export, block. 🧠 [LT], `reconstruction/identity-embeddings.md`; C12

**CI.** Fail the build on any bundled file without an SPDX entry. Run the fitting tests on the CC0 template alone. 🧠 [LT]

## 6. Failure modes the engine must detect

| # | Condition | Detection | Action | Cite |
|---|---|---|---|---|
| F1 | More than one face in a photo | detector count > 1 | the user picks the subject; others are never fitted or stored | [CL] 🧠 |
| F2 | Photo not covered by the consent (bystander, group or camera-roll photo) | sha256 ∉ `photo_sha256[]` | block fitting on that photo | [CL] 🧠 (editor) |
| F3 | Missing or expired record; scope mismatch | gate check | refuse; name the missing scope | [CL][BP] 🧠 |
| F4 | Scope creep: an animatable rig built under static-sculpt consent | expression shape keys or rig export without `RIG_ANIMATE` | block | [BP][CL] 🧠 |
| F5 | Minor without a guardian | attested age < 18 and `signer_role ≠ guardian` | block; never default to animatable + public + realistic | [CL] 🧠 |
| F6 | Deceased subject without the estate | flag set and `signer_role ≠ estate` | block commercial use | [CL] 🧠 |
| F7 | Texture from an unknown-rights photo | `rights_basis = unknown` at bake, pack or export | block | [LT] 🧠 |
| F8 | NC or unknown component in a commercial export | `commercial_ok ≠ true` | block; list the offending components | [LT][CL] 🧠 |
| F9 | Biometric leftovers in a shared .blend | packed images, camera Background Images, image empties, orphans, file preview, `.blend1…N`, autosave, `quit.blend` | the "Prepare for sharing" operator lists and purges them | [BP] 🧠 |
| F10 | Embedding persisted | IDProperty or sidecar holding an embedding-sized float vector (editor heuristic) | refuse to save; purge | [BP] 🧠 |
| F11 | Real name in identifiers | filename, datablock or property matches `subject_pseudonym`'s real-name field (editor) | warn; rename | [BP] 🧠 |
| F12 | EXIF GPS, serials, MakerNote or thumbnail left in a working copy | EXIF scan at ingest and at export | strip (Artist and Copyright kept) | [BP][LT] 🧠 |
| F13 | Network attempt without scope | socket guard or `online_access` false | raise; write to the audit log | [BP] 🧠 |
| F14 | Retention overrun | C1 clocks (45 / +45 / 730 / 365) and `expires_at` | warn 30 days before; then a purge prompt | [BP] 📄 / 🧠 |
| F15 | Model file or licence changed | sha256 or `licence_text_hash` differs from the registry | refuse to load; ask for re-acceptance | [LT] 🧠 |
| F16 | Social or URL source | import path is a URL or account | refuse | [LT] 🧠 |
| F17 | Request to "anonymise" a likeness | — | no such feature; smoothing does not de-identify | [BP] 🧠 |
| F18 | 1:N or "who is this" request | gallery import or a multi-identity compare | not implemented | [BP][CL] 🧠 |
| F19 | Accidental collection via crash reports | error handler payload contains arrays, images or paths | strip before writing | [BP] 🧠 |
| F20 | ML component touched output that is exported as realistic | any `is_ml` entry in the run | set the digital-source-type metadata; overlay on | [CL] ↔️ (C13) |

## 7. Facts that shape the design (why these gates exist)

- **Derived geometry counts as biometric.** Landmarks and meshes derived from photos are likely a BIPA "scan of face geometry" (🧠). *Zellmer* requires identification capability (📄), and a high-likeness head has it by design. [BP]
- **GDPR.** Data is biometric by capability, and Art. 9 is triggered by the purpose of uniquely identifying (✅). 1:1 identity scoring comes close to "confirming" identity. [BP]
- **BIPA counting.** It is one violation per person per method, and the Seventh Circuit held this retroactive (*Clay*, 2026) ✅. A written release before collection is still required. 🧠 [BP]
- **AI Act Art. 50** applies from 2 Aug 2026 ✅. The Art. 50(2) grace period to 2 Dec 2026 covers only pre-existing generative systems (📄). Classical least-squares fitting is probably not an AI system, while neural detectors probably are (↔️). That is why `is_ml` tracking (F20) exists. [CL]
- **Fitting extracts facts; texture copies pixels.** That is why the fit path and the texture path carry separate rights gates. 🧠 [LT]

## 8. Open questions

1. May an Extensions listing download weights at runtime, and must non-code data such as the Apache-2.0 OBJ be CC0? (↔️ [LT]; C7, C8)
2. What does MediaPipe's official model card say about the weight licence? (↔️ [LT])
3. What exactly is inside FLAME 2023 Open (bases, masks, UVs, expression basis)? (↔️ C6)
4. Do NC detector outputs taint the fitted geometry? (↔️ [LT])
5. Are 3DMM coefficients "templates", and at what iris resolution does a texture become an "iris scan"? (↔️ [BP])
6. Is a heavily hand-sculpted head still a "scan"? (↔️ [BP])
7. Does Art. 50 reach classically fitted CGI, and do 3D renders count as "deep fakes"? (↔️ [CL])
8. What are the final NO FAKES terms, and does a general-purpose fitter fall under the "primary purpose" tool liability? (↔️ [CL])
9. Do BIPA's retroactivity and TRAIGA's carve-outs hold in state courts? (↔️ [BP])
10. Which jurisdiction rules does `jurisdiction_tags` drive? The minimum age and the retention clocks are candidates; this needs counsel. (🧠 [CL][BP])
