# Commercial photo-to-head tools

> Every commercial "photo to head" product is a template fitter: it bends one fixed vendor topology inside a learned shape space until landmarks or user pins reproject onto the photos, then projects the photos as texture. Likeness is bounded by that shape space, the camera model and how many views constrain depth, and no vendor publishes millimetre error against ground-truth scans. In 2026 the field splits into a Blender-native pin fitter (KeenTools FaceBuilder), rig-ecosystem converters (Reallusion Headshot → Character Creator; Mesh to MetaHuman / MetaHuman Creator), a legacy statistical fitter (FaceGen), a scan-to-template wrapper (R3DS/Faceform Wrap), a downstream blendshape service (Polywink) and selfie-avatar SDKs (Avaturn, Avatar SDK) filling the space Ready Player Me reportedly left. They set the UX and output contracts to match (pins, per-photo cameras, camera groups, ARKit names, wrap-to-template) and expose the gap: an open, metric, auditable multi-view fit. With no harvest, everything is expert knowledge or contested recollection; prices, versions and licences are perishable.
Evidence status: 4 ✅ / 2 📄 / 63 🧠 / 40 ↔️ — 🧠 items are queued for web verification; 4 claim groups checked 2026-11-20 (see log).

## Key facts

### Shared mechanics
- **Template + shape space + 2D constraints + camera + projection.** A pin binds an image point to a surface point; the solver minimises reprojection error over shape, expression, head pose and sometimes focal length 🧠.
- **One photo cannot fix depth.** Single-image modes infer nasal projection, chin and forehead slope from the prior 🧠.
- **Projected texture is not albedo:** light, shadow, specular and vignetting are baked in (`reconstruction/albedo-lighting-inverse-rendering.md`) 🧠.
- **No independent benchmark.** I know of no peer-reviewed mm-level comparison of FaceBuilder, MetaHuman conform or avatar SDKs against scans (Headshot 1 has one clinical study [9]); evidence is vendor demos and forum impressions; one peer-reviewed clinical study did test Headshot v1.0 (Character Creator 3) against optical face scans, whole-face RMSE 1.77 mm (perioral 1.26 mm) [9], but none found for FaceBuilder, Mesh to MetaHuman or avatar SDKs 📄 (corrected in verification).
- **Processing location matters for consent.** FaceBuilder, FaceGen, Wrap and (I believe) Headshot run locally; the MetaHuman autorig, Polywink, Avaturn and cloud avatar SDKs process faces on vendor servers 🧠. Identifying face geometry is biometric data under GDPR Art. 9 and Illinois BIPA ↔️ (not legal advice).

### KeenTools FaceBuilder for Blender
- **Input:** any number of photos; each becomes a view with its own camera; EXIF focal is read, and focal can be fixed, shared by a camera group or estimated per view 🧠. Auto focal/sensor setup came with the "revamped" release (forum-sourced in `community/blenderartists-forum.md`) 🧠.
- **Pins:** neural auto-pinning ("Align face") since 2021.1, often needing manual correction (forum-sourced, same note) 🧠. Shape- and expression-rigidity settings limit how far pins pull the mesh from the prior 🧠.
- **Expressions:** an expression mode tolerates non-neutral photos; neutral photos still fit better (forum-sourced) 🧠.
- **Output:** fixed KeenTools topology with selectable density and optional parts (ears, eyes, neck, mouth) ↔️; several UV layouts (recalled: Butterfly, Legacy, Spherical, Maxface, MakeHuman) ↔️; texture baked from chosen views 🧠; ARKit-compatible blendshapes recalled as 51 (ARKit 52 minus `tongueOut`) with Live Link Face CSV import ↔️.
- **Licence:** GPL Python add-on that downloads a proprietary core 🧠; paid, with a trial (a forum user mentions 30 days) and subscription pricing; list price contested: about US$179/yr (individual Freelancer plan, 2024 CG Channel report [5]) to US$499/yr (floating plan on the current store page [4]), and KeenTools says it raised prices [6]; Blender 5.x support and the 51-shape count unverified ↔️.
- **Siblings:** GeoTracker (objects) and FaceTracker (facial performance on a FaceBuilder head; Blender version recalled from 2024) ↔️.
- **Limits:** front and ¾ likeness good; profile only as good as profile photos and pins 🧠; no radial-distortion model that I know of ↔️; the low-dimensional space flattens alar shape, lid folds and vermilion border, which you must sculpt 🧠.

### Reallusion Headshot (Character Creator)
- **Headshot 1 (2020, CC3):** one frontal photo → CC head; Auto mode (full game head) or Pro mode (higher-resolution face texture) 🧠.
- **Headshot 2 (2023, CC4)** adds Mesh mode: any-topology head, auto plus manual alignment points, refine brushes, texture bake; output is a rigged CC character with the CC facial profile (ARKit-compatible names in Extended) 🧠.
- **CC5** reportedly shipped in 2025 with a denser head; Headshot's status there is unknown to me ↔️.
- **Licence and price:** perpetual licences, each a few hundred US dollars, often bundled ↔️; raw base mesh and morphs not redistributable (`blender/metahuman-cc-bridges.md`) 🧠.
- **Likeness:** photo mode is recognisable but depth-guessed; mesh mode is as good as its input and alignment points; base density limits lids and nostrils without SubD plus normal maps 🧠.

### MetaHuman (Epic Games)
- **Paths:** Creator (cloud 2021, in-engine since UE 5.6, 2025); Mesh to MetaHuman (UE 5.0, 2022); Footage to MetaHuman / Animator (UE 5.2, 2023; iPhone depth or stereo head-mounted cameras) 🧠. 5.6–5.7 reportedly added monocular-video and audio-driven animation ↔️.
- **No first-party "photo → MetaHuman"** that I know of; the usual chain is photos → FaceBuilder or photogrammetry → mesh → Mesh to MetaHuman or Creator conform ↔️.
- **Input contract:** neutral, eyes open, lips closed, clear brow, real scale in cm, one combined textured mesh 🧠.
- **Output:** DNA rig with RigLogic (≈250 raw expression controls; LOD0 head ≈24k vertices, recalled) 🧠.
- **Licence:** free; since UE 5.6 MetaHumans fall under the standard Unreal Engine EULA [1][2] (Creator EULA only for the cloud tool on 5.5 and earlier), usable with any engine or creative software [1] and sellable or usable in Unity or Godot [3]; the UE EULA's revenue-based terms (free under US$1M/yr, seats above) apply, and the exact license text for Blender/Unity/Fab use was not located ✅. The autorig needs an Epic account and cloud 🧠.
- **Drift:** conform pulls toward Epic's scan database at nasal tip and alae, vermilion, lid aperture and jaw angle; 5.6's parametric model claims a wider range, unmeasured ↔️.

### FaceGen (Singular Inversions)
- **PhotoFit:** one frontal photo plus optional profiles; the user places about a dozen points per photo; a scan-trained statistical morphable model fits shape and colour 🧠.
- **Products:** Modeller (demo and paid tiers), Artist, SDK; "Customizer" maps FaceGen statistics onto your own mesh 🧠. The SDK made NPC faces in Bethesda games of the Oblivion–Skyrim era 🧠.
- **Research use:** its statistical controls underpin face-perception work such as Oosterhof & Todorov (2008) 🧠; its caricature control scales deviation from the mean face, the mechanism behind the caricature advantage in recognition 🧠.
- **Likeness and price:** smooth, low-resolution, generic; perpetual tiers in the hundreds of US dollars ↔️.

### R3DS Wrap (Faceform)
- **Not photo-to-head:** it wraps a template onto a scan. Graph: point pairs → rigid alignment → Wrapping (control points, excluded polygons, coarse-to-fine smoothness) → optional texture-guided optical-flow wrapping → subdivide/project → texture and blendshape transfer; brush fixes, Python, batch 🧠.
- **Family:** Wrap (year-versioned after Wrap 3), Wrap4D, ZWrap 🧠; reportedly rebranded Faceform, as `blender/import-export-scans.md` also flags ↔️. Subscription with an indie tier under a revenue cap; prices unverified ↔️.
- **Role:** the de facto standard; its rigid + landmark + regularised NRICP pipeline is what the numpy wrap reproduces (`reconstruction/deformation-fitting-math.md`) 🧠.

### Polywink
- **Downstream rigging service:** upload a neutral head (separate eyes and teeth, mouth closed) and receive the ARKit 52 set, a larger FACS set (recalled 150–240 shapes) or a Maya control rig, in about a day, priced per character in the hundreds of US dollars ↔️. It inherits your likeness, and consent must name the upload 🧠.

### Avaturn, Ready Player Me and successors
- **Avaturn:** three selfies → realistic full-body avatar; GLB with a Mixamo-compatible skeleton, ARKit blendshapes and visemes; web SDK; free personal use, paid developer plans ↔️.
- **Ready Player Me** (Wolf3D) made stylised cross-game selfie avatars with Unity and Unreal SDKs 🧠. Netflix agreed to acquire it in December 2025 [7][8] ✅; coverage reports services winding down on 31 Jan 2026 (date not pinned to a single URL, so shutdown stays unconfirmed) 🧠.
- **Other options:** Avatar SDK / MetaPerson (itSeez3D; one selfie → realistic head or body, local SDK option), in3D (phone-video body scans), Meshcapade (SMPL-family bodies; commercial SMPL/FLAME licensing), Didimo (B2B); status and terms unverified ↔️.
- **All target real-time avatars**, not sculpt-grade likeness: game-density meshes, smoothed features, selfie perspective baked in 🧠. Generalist image-to-3D (Tripo, Meshy, Rodin, Hunyuan3D, TRELLIS) is untopologised and non-metric (`community/ai-assisted-sculpting.md`) 🧠.

## Numbers & reference tables

**Table 1 — Tool matrix** (as recalled; verify per release)

| Tool | Input | Views: min / good | Solver | Output | Expression set | Runs | Badge |
|---|---|---|---|---|---|---|---|
| FaceBuilder | photos | 1 / 5–9 incl. both profiles | pins + morphable head, per-view cameras | KeenTools head + projected texture | 51 ARKit-style | local | 🧠 |
| Headshot photo mode | frontal photo | 1 / 1 | landmarks + learned depth | CC head + texture | CC profile | local | 🧠 |
| Headshot 2 mesh mode | mesh | n/a | alignment points + conform | rigged CC character | CC profile | local | 🧠 |
| Mesh to MetaHuman | textured mesh | 1 frontal frame / + ¾ | 2D curve markers + identity solve | DNA rig | ≈250 controls | cloud autorig | ↔️ |
| FaceGen PhotoFit | photos | 1 / 3 | manual points + 3DMM | FaceGen meshes | expression/phoneme morphs | local | 🧠 |
| Daz Face Transfer | frontal photo | 1 / 1 | learned fit | Genesis morph + texture | Genesis | local | 🧠 |
| R3DS/Faceform Wrap | scan + template | n/a | point pairs + regularised NRICP | your template | transfers yours | local | 🧠 |
| Polywink | neutral mesh | n/a | automatic transfer | shapes or rig | ARKit 52; larger FACS | cloud | ↔️ |
| Avaturn | selfies | 3 / 3 | learned regression | GLB full body | ARKit + visemes | cloud | ↔️ |
| Ready Player Me | selfie | 1 / 1 | learned, stylised | GLB | ARKit + visemes | reportedly closed | ↔️ |

**Table 2 — Cost and licence, order of magnitude** (USD; perishable)

| Tool | Model | Rough cost | Licence gist | Badge |
|---|---|---|---|---|
| FaceBuilder | subscription, trial | ~180–500 per seat-year (contested, corrected in verification) [4][5][6] | GPL front + closed core; outputs yours [4] | ↔️ |
| Character Creator + Headshot | perpetual, bundles | hundreds each | no raw base/morph redistribution | ↔️ |
| MetaHuman | free, Epic account | 0 | UE EULA; outside-UE use since 5.6 [1][2][3] | ✅ |
| FaceGen | perpetual tiers | hundreds | SDK separate | ↔️ |
| Wrap | subscription tiers | hundreds to low thousands per year | indie revenue cap | ↔️ |
| Polywink | per character | hundreds | third-party upload | ↔️ |
| Avaturn | freemium + developer plans | free personal | per plan | ↔️ |

**Table 3 — Accuracy ladder** (face-region surface error vs a reference scan, mm, adults. Rows 1–2 are NoW figures verified in `reconstruction/single-image-regression.md`; the rest are my estimates for defaults, not benchmarks)

| Route | Face region | Profile / nasal tip | Badge |
|---|---|---|---|
| Mean FLAME face, scale optimised (NoW mean) | ≈1.5 | not scored | 🧠 |
| Best research single-image regressor (NoW median) | ≈0.9–1.2 | not scored | 🧠 |
| Commercial single photo (Headshot photo, avatar SDKs, Face Transfer, FaceGen 1-view; Headshot 1 clinical study RMSE 1.77 mm [9]) | 1.2–3 | 2–6 | ↔️ |
| Multi-view pin fit, 5–9 views with profiles | 0.8–2 | 1–3 | ↔️ |
| Handheld photogrammetry + wrap | 0.5–2 | 0.5–2 | ↔️ |
| Synchronised rig + Wrap | 0.1–0.5 | 0.1–0.5 | ↔️ |
| Extra local drift from vendor conform | +0.5–2 at nose, lips, lids | +0.5–2 | ↔️ |

**Table 4 — Output contracts to match**

| Contract | Count / value | Notes | Badge |
|---|---|---|---|
| ARKit blendshapes | 52 incl. `tongueOut` | coefficients 0–1 | 🧠 |
| FaceBuilder blendshapes | 51 | no tongue | ↔️ |
| MediaPipe Face Landmarker | 52 incl. `_neutral`, no `tongueOut` | per `blender/blender-face-addons.md` | 🧠 |
| MetaHuman raw controls | ≈250 | `CTRL_expressions_*` | 🧠 |
| Polywink sets | 52; FACS 150–240 | recalled | ↔️ |
| MetaHuman / CC / Daz scale | cm (×100 from Blender m) | check IPD 55–70 mm after import | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Route by capture** 🧠: photos only → multi-view pin fit (FaceBuilder or this add-on); subject can hold still for 50–150 photos → photogrammetry then wrap; production rig needed → fit first, then Mesh to MetaHuman or Headshot mesh mode, and audit drift.
2. **Photo protocol for every tool** 🧠: neutral, eyes open, lips closed, hair off forehead and ears, no glasses, soft even light; tele lens or 2–3× phone tele at ≥1 m (`blender/reference-camera-setup.md`); front, ±30–45°, both profiles, slightly high and low; fixed zoom so views form one camera group; a scale cue (measured IPD or a ruler at face depth).
3. **FaceBuilder recipe** 🧠:
   - Group views by camera; estimate focal only if EXIF is missing or wrong.
   - Pin the front first: canthi, mouth corners, nasal tip, subnasale, chin, ear attachment.
   - Pin profiles along the silhouette: glabella, nasion, pronasale, subnasale, lips, pogonion.
   - Use few confident pins; fighting pins make lumps, so delete rather than add.
   - Lock expression for neutral photos; check every view after each pin.
   - Texture from the front and both ¾ views; profiles smear the cheeks.
4. **Audit any vendor head** 🧠: scale (IPD 55–70 mm, head height 21–25 cm); mirroring (parting, moles, asymmetries on the right side); reprojection RMS in px and %IOD with one camera per photo; profile overlay for nasal projection, chin and forehead slope, where single-view tools fail most.
5. **Make it sculpt-ready** 🧠: wrap the vendor result onto your production topology, apply transforms, add Multires and reproject; de-light the projected texture or keep it as reference only.
6. **What goes wrong** 🧠: wide-lens selfies inflate the nose and hide ears; mirrored selfies swap sides; a faint smile becomes identity; hair read as skull; beards hide the jaw; ×100 scale errors; cloud uploads without matching consent.

## Algorithmic implications

- **Pins as first-class constraints** 🧠: `Pin{view, xy_px, surface(tri, bary), sigma, source ∈ {user, auto}}`. Default σ: user 0.75% IOD; auto 1.5% (corners), 2.5% (lid and lip contours), 4% (face oval, re-associated each iteration), matching `blender/blender-face-addons.md`; Huber δ = 2σ; a user pin overrides auto pins on the same feature.
- **Camera groups** 🧠: views from one body and zoom share intrinsics. EXIF focal prior f_px = f35·√(W²+H²)/43.27 with log-σ 0.03; without EXIF start at 50 mm equivalent, log-σ 0.5, and solve focal only when ≥2 views or a profile constrain it. Principal point at centre; k1 only for wide lenses.
- **Rigidity as prior weight** 🧠: slider r ∈ [0,1] → λ_shape = 10^(2r−1) (0.1–10, default 1) on PCA coefficients ~ N(0,1); separate expression rigidity; residual per-vertex offsets capped near 5 mm unless ≥2 views agree.
- **Vendor heads as observations, not truth** 🧠: an imported FaceBuilder, Headshot or MetaHuman head becomes a point-to-plane term with σ ≈ 2.5 mm (single-photo tools; 4 mm on profile regions), 1–1.5 mm (multi-view pin fits) or 0.5 mm (scan + wrap), down-weighted once photo constraints exist.
- **Texture projection** 🧠: per-texel weight cos(θ)^k, k = 2–4; reject θ > 70–75°; feather seams over 8–16 texels; keep a per-texel view-index map so artists can repaint from a chosen photo.
- **Export contracts** 🧠: ARKit-52 names; a cm "bridge-ready neutral" for MetaHuman, CC and Daz; stable vertex order. Never ship vendor topology or indices; build correspondences locally from the user's licensed copy (`blender/metahuman-cc-bridges.md`).
- **Evaluation harness** 🧠: since vendors publish nothing, add "compare to scan": 7-landmark Umeyama alignment (NoW-style), per-region RMS for nose, mouth, eyes, forehead and cheeks (REALY-style) and profile-silhouette error, so users can rank FaceBuilder, Headshot and the add-on on their own subject.
- **Consent and licence metadata** 🧠: `{tool, version, processing: local|cloud, licence, commercial_ok, consent_scope}` per asset; block exports that passed a cloud step without matching consent.

## Disagreements, myths & open questions

- **"FaceBuilder makes a scan-accurate head."** It is a pinned fit of a low-dimensional head ↔️.
- **"One good photo is enough."** No single-image tool recovers metric depth; a scaled mean face already scores about 1.5 mm on NoW 🧠.
- **"There is an official MetaHuman from a photo."** Not first-party to my knowledge; third-party chains such as MetahumanModeler exist (`community/blenderartists-forum.md`) ↔️.
- **"Mesh to MetaHuman preserves the scan."** It conforms a template and autorigs from a database; drift is reported but unmeasured ↔️.
- **Open questions** ↔️: FaceBuilder price, tiers, Blender 5.x support and blendshape count; Headshot under CC5; MetaHuman after 5.7 and exact outside-UE terms; Ready Player Me's status; Faceform branding and Wrap prices; Polywink set sizes; any independent mm-level benchmark of FaceBuilder, Mesh to MetaHuman and avatar SDKs.

## Sources

1. https://www.metahuman.com/license
2. https://www.unrealengine.com/eula/mhc
3. https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/
4. https://keentools.io/buy
5. https://www.cgchannel.com/2024/03/keentools-ships-facebuilder-2024-1-for-blender/ (2024 CG Channel coverage; the search summary did not say which 2024 article carried the $179/yr figure)
6. https://keentools.io/news/new-licensing
7. https://techcrunch.com/2025/12/19/netflix-acquires-gaming-avatar-maker-ready-player-me/
8. https://www.pocketgamer.biz/netflix-acquires-avatar-creation-platform-ready-player-me
9. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9487071/

Related notes: `blender/metahuman-cc-bridges.md`, `blender/blender-face-addons.md`, `community/blenderartists-forum.md` (FaceBuilder release threads), `community/reddit-face-from-photos.md`, `reconstruction/photogrammetry-heads.md`, `reconstruction/single-image-regression.md`.

**Further reading (by name, not yet linked)**
- Vendor documentation: KeenTools FaceBuilder for Blender; Reallusion Character Creator 4 manual (Headshot 2) and EULA; Epic MetaHuman docs and Unreal Engine EULA; FaceGen Modeller/SDK; R3DS/Faceform Wrap; Polywink; Avaturn; Avatar SDK
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999
- Egger et al., "3D Morphable Face Models—Past, Present, and Future", ACM TOG 2020
- Oosterhof & Todorov, "The functional basis of face evaluation", PNAS 2008
- Sanyal et al., RingNet and the NoW benchmark, CVPR 2019
- Chai et al., "REALY: Rethinking the Evaluation of 3D Face Reconstruction", ECCV 2022
- Amberg, Romdhani & Vetter, "Optimal Step Nonrigid ICP Algorithms for Surface Registration", CVPR 2007
- Apple ARKit documentation, `ARFaceAnchor.BlendShapeLocation`

## Verification log (2026-11-20)

- MetaHuman 5.6 under UE EULA, usable outside UE, sellable: confirmed. https://www.metahuman.com/license ; https://www.unrealengine.com/eula/mhc ; https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/ . Revenue-based terms noted; specific Blender/Unity/Fab license text not located. No first-party photo path: unconfirmed (not searched directly).
- FaceBuilder price and licence: contested (US$179/yr to US$499/yr; prior note said 100-300). https://keentools.io/buy ; https://keentools.io/news/new-licensing ; https://www.cgchannel.com/2024/03/keentools-ships-facebuilder-2024-1-for-blender/ . GPL add-on with proprietary core, 51 ARKit blendshapes, Live Link CSV and Blender 5.x support: unconfirmed.
- Ready Player Me / Netflix: acquisition confirmed (December 2025). https://techcrunch.com/2025/12/19/netflix-acquires-gaming-avatar-maker-ready-player-me/ ; https://www.pocketgamer.biz/netflix-acquires-avatar-creation-platform-ready-player-me . Closure on 31 Jan 2026: reported in search summary, not tied to a URL, unconfirmed.
- No peer-reviewed benchmark: corrected. A clinical study tested Headshot v1.0 vs optical scans (RMSE 1.77 mm). https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9487071/ . None found for FaceBuilder, Mesh to MetaHuman or avatar SDKs.
