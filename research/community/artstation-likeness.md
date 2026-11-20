# ArtStation: likeness breakdowns and tutorials

> Likeness breakdowns on ArtStation (project posts, "making of" articles, Learning courses, Marketplace tutorials, and the interviews that republish them) describe one process. Curate many photos from one age window, rank them by lens, distance and retouching, block primary forms at low resolution, compare through a matched camera per hero photo (or by eye), cycle every view until silhouette and features agree, then add asymmetry, eyes, identity marks, brows and hair, and judge under light matched to the photos. The most repeated lessons: likeness lives in head shape and primary forms, telephoto event photos beat selfies, retouched covers and film stills mislead in predictable ways, and brows and hair make a likeness "click". Reported timelines run from weeks to months part-time, with groom and texture taking as long as the sculpt. No harvest or earlier draft existed, so everything here is expert knowledge or pinhole arithmetic awaiting verification; platform facts are time-sensitive.
>
> Evidence status: 0 ✅ / 0 📄 / 57 🧠 / 26 ↔️ — 🧠 items are queued for web verification.

## Key facts

**The platform and its genres** (time-sensitive; verify all of it)
- ArtStation launched in 2014 (Ballistiq, Canada). Epic Games bought it in 2021; Learning courses then became free and Marketplace fees fell 🧠 ↔️
- Epic's **Fab** (late 2024) merged its asset stores; what still sells on ArtStation Marketplace versus Fab needs checking before the add-on links to it ↔️
- **Genres:** project posts with breakdown images (clay, wireframe, side-by-side with the photo, turntable); "making of" articles; Learning courses; Marketplace video tutorials. Text-rich breakdowns mostly appear as interviews on 80 Level, 3dtotal, the Gnomon blog and ZBrushCentral 🧠
- **The late-2022 anti-AI protest** led to "NoAI" tags and filters; the community stays hostile to AI-started work (`community/ai-assisted-sculpting.md`) ↔️
- **Source quality:** self-reported, survivorship-biased, sometimes vendor-sponsored; judged by strangers who know the celebrity from the same press photos; side-by-sides show the best angle 🧠

**The recurring process** (common core across breakdowns; no single artist is quoted here)
- **Reference:** tens to hundreds of photos from one age and weight window, sorted by angle on a PureRef board; 5–15 "hero" images to match against 🧠
- **Base:** sphere or DynaMesh blockout (studies), a neutral base mesh, or, most often in professional realism, a licensed **3D scan** of a similar head wrapped to clean topology (R3DS/Faceform Wrap, ZWrap), with the likeness sculpted on top 🧠 ↔️
- **Primary forms at low resolution:** cranium and occiput, jaw width and angle, brow, cheek mass, nose block, mouth barrel, ear position. "Whack-a-mole": a fix in one view breaks another, so cycle all views after every change 🧠
- **Secondary forms after symmetry is off:** lids over a correct eyeball, caruncle and canthi, alae and nostrils, lip border and corners, nasolabial and infraorbital transitions, ears 🧠
- **Identity marks:** hand-sculpt or paint the sitter's own moles, scars, forehead lines and crow's feet over generic multichannel displacement (Texturing XYZ-type maps) 🧠
- **Texture:** projected from photos in Mari or Substance Painter, then repainted; artists warn a projection "fakes" likeness from its own angle 🧠
- **Brows and hair** (XGen, Ornatrix, Houdini, Blender hair curves): breakdowns repeatedly say the likeness clicked only once these went in, and grooming took as long as the sculpt 🧠
- **Look-dev:** compare with the reference camera and photo-matched light; present with a neutral studio rig 🧠
- **Feedback:** peers and, ideally, people who know the subject; breaks; flipped images 🧠

**Reference lore specific to likeness of real people**
- **Telephoto event photos are the gold standard** (red carpet, press, sport): shot from metres away, near-orthographic, in same-day sequences across many yaw angles 🧠
- **Covers and studio portraits are often liquified:** jaw slimmed, eyes enlarged, neck lengthened, skin smoothed. Cross-check proportions against untouched photos ↔️
- **Film and TV stills** carry makeup, prosthetics, wigs, grading and unknown lenses; a grab never desqueezed from anamorphic (usually 2×) is horizontally squeezed 🧠
- **Interview video** gives same-day yaw sweeps but low resolution, compression and blur: good for understanding form, not measurement 🧠
- **Phone photos:** selfies at 0.3–0.6 m enlarge the nose; front cameras often mirror; beauty modes smooth and reshape; ultra-wide "face distortion correction" warps edge faces away from a pinhole projection ↔️
- **Body changes:** role weight changes alter buccal fat, jowl and neck; makeup moves lip and brow borders; contouring fakes planes; glasses rescale the eyes 🧠

**Camera matching as practised**
- **Four routes:** (i) by eye, side by side in an always-on-top PureRef window; (ii) ZBrush overlay (Spotlight, See-through, perspective; `community/zbrush-to-blender-likeness.md`); (iii) a DCC camera with image plane (Maya, Max, Blender) at the EXIF or guessed focal length; (iv) solvers: KeenTools FaceBuilder, point-correspondence Wrap, or photogrammetry when the sitter is available 🧠
- **Celebrity photos rarely have a known focal length;** artists guess from apparent perspective (nose-to-ear ratio, ear visibility), the largest unacknowledged error in by-eye pipelines 🧠
- **Many acclaimed likeness artists match by eye only,** relying on many views rather than exact cameras ↔️
- **Production likeness of actors is scan-based** (photogrammetry rigs, facial capture); hand-sculpted likeness dominates collectibles, portfolios, historical subjects and unavailable actors 🧠

**What breakdowns say the likeness "is"**
- **Head shape and silhouette first:** cranial shape, jaw, profile line 🧠
- **Eyes as lid shapes:** lid thickness, crease height and hooding, how the lid wraps the globe, the lower-lid curve, canthal tilt; the iris itself matters little 🧠
- **Brows, hairline and hair:** carry recognition at a distance (consistent with Sinha & Poggio 1996) 🧠
- **Characteristic expression:** some insist on capturing a habitual asymmetric smile or brow set; others sculpt neutral and add expression later ↔️
- **Skin identity marks** matter at close range, not at thumbnail size 🧠

**Practitioners frequently cited for realistic likeness** (names only; no statement in this note is attributed to them): Hadi Karimi, Ian Spriggs, Sefki Ibrahim, Hossein Diba, Glauco Longhi, Adam Skutt, Pablo Muñoz Gómez, and for Blender sculpting Daniel Bystedt and Yan Blanco 🧠

## Numbers & reference tables

**Table 1 — Reference source types.** Magnification = 1 + dz/d, with dz = 0.10 m from nose tip to ear plane (assumed 0.09–0.11 m); distance and lens columns are typical ranges, not measurements. f35 = 35 mm-equivalent focal length.

| Source | Typical d (m) | f35 (mm) | Nose:ear magnification | Main risks | Use for | Suggested σ multiplier | Badge |
|---|---|---|---|---|---|---|---|
| Event/press telephoto | 3–10 | 70–300 | 1.01–1.03 | flash flattening, smiles | proportions, profile, yaw sweeps | 1.0 | 🧠 |
| Own controlled capture (consenting sitter) | 1.5–3 | 85–135 | 1.03–1.07 | none if EXIF is kept | everything | 0.7–1.0 | 🧠 |
| Studio portrait / magazine | 1.5–4 | 70–135 | 1.03–1.07 | liquify retouching | hairline, colour; proportions only if consistent | 2–3 or exclude | ↔️ |
| Film/TV still | 0.6–3 | 25–150 (unknown) | 1.03–1.17 | makeup, anamorphic, grade | 3/4 form, expression | 1.5–2 | 🧠 |
| Interview video frame | 1–3 | 35–100 | 1.03–1.10 | compression, blur, low resolution | yaw coverage | 1.5–2.5 | 🧠 |
| Phone rear camera | 0.8–2 | 24–120 (multi-lens) | 1.05–1.13 | HDR, sharpening, lens correction | general | 1.2 | 🧠 |
| Phone selfie | 0.3–0.6 | 22–30 | 1.17–1.33 | perspective, mirroring, beauty filters, face warping | colour, hairline only | 3 or exclude | ↔️ |

**Table 2 — Reference set composition recommended in breakdowns**

| Item | Typical value | Badge |
|---|---|---|
| Photos collected | 30–300 | 🧠 |
| Hero photos matched | 5–15 | 🧠 |
| Views | front; ¾ left and right (yaw 30–45°); profiles (≈90°); slight high and low (pitch ±15–20°); back of head if possible | 🧠 |
| Age window | ≤ 2–3 years, one weight period | 🧠 |
| Expression | neutral, lips closed, teeth lightly together; expression photos kept as a separate set | 🧠 |
| Resolution | face ≥ 400–600 px wide for heroes | 🧠 |

**Table 3 — Reported project timelines and phase shares.** Self-reported, highly variable, unverified.

| Project type | Total effort | Badge |
|---|---|---|
| Speed likeness study (sculpt only) | 2–10 h | ↔️ |
| Collectible / print likeness head (sculpt only) | 20–80 h | ↔️ |
| Portfolio offline-render bust (sculpt, texture, groom, render) | 80–400 h, often 1–6 months part-time | ↔️ |
| Scan-based real-time actor head (cleanup, texture, groom) | 1–4 weeks | ↔️ |

| Phase (portfolio bust) | Share of time | Badge |
|---|---|---|
| Reference gathering and curation | 3–10% | 🧠 |
| Blockout and primary likeness | 20–35% | 🧠 |
| Secondary and tertiary sculpt | 10–20% | 🧠 |
| Texture (projection, paint, XYZ) | 10–20% | 🧠 |
| Groom (hair, brows, lashes, peach fuzz) | 15–30% | ↔️ |
| Look-dev, lighting, comparison renders | 10–20% | 🧠 |

**Table 4 — Asset specs typical of breakdowns**

| Item | Typical range | Badge |
|---|---|---|
| Sculpt base mesh | 5–20 k quads | 🧠 |
| Final head sculpt (ZBrush) | 5–40 M polygons (subdivision level 5–7) | 🧠 |
| Head displacement/colour maps | 4–10 UDIM tiles at 4K–8K | 🧠 |
| Real-time hero head, LOD0 | 20–60 k triangles | ↔️ |
| Scalp groom, rendered strands | 50–200 k (from a few hundred to a few thousand guides) | 🧠 |
| Real scalp hair count | ≈ 100 k (≈ 90–150 k, varies with hair colour) | 🧠 |
| Real eyelashes per lid | upper ≈ 90–160, lower ≈ 75–80 | ↔️ |

## Applying this to photo→3D face sculpting in Blender

1. **Curate before you solve.** Board photos by yaw bin; tag source type (Table 1), date, EXIF focal, expression and mirroring (check a parting or mole). Keep retouched covers and filtered selfies out of proportion work. For a consenting sitter, your own capture (Table 2; `community/reddit-face-from-photos.md`) beats any celebrity board.
2. **Estimate distance per photo:** d ≈ f_px × 63 mm / IPD_px. Anything under ~1 m is used for colour and hairline only unless the solver frees the focal length.
3. **Solve one perspective camera per hero photo** (the engine, or FaceBuilder) and attach the photo as that camera's Background Image (Depth Front, opacity 0.3–0.5, Frame Method Stretch, render resolution = photo pixels). Lock camera transforms, keep Lock Camera to View off, and bind cameras to timeline markers so one key steps through views (`blender/reference-camera-setup.md`).
4. **Base:** start from the fitted template or a licensed neutral scan wrapped to your topology, not a sphere, when accuracy is the goal. Keep the fit as a shape key over Multires L0–L1.
5. **Primary pass through every camera,** profile first: largest error, lowest level, re-check all views. Do not let one hero photo dominate.
6. **Add proxy brows and hairline early:** a few Blender hair-curve guides or cards, sized to the photo. Pros report the likeness only reads once these exist, and a bald, browless head tempts you to "fix" correct geometry.
7. **Eyes before lids:** ~24 mm globes, iris ≈ 11.7 mm, then lid thickness, crease and lower-lid curve per view (`blender/eyes-modeling-blender.md`).
8. **Symmetry off once primaries agree.** Add asymmetry only where ≥ 2 solved views agree.
9. **Identity marks:** place moles and scars as vertex-group markers or texture decals. They anchor texture projection and double as cross-view correspondences.
10. **Texture projection for checking only.** Turn it off for shape review, and judge from cameras ≥ 20–30° away from the projecting photo.
11. **Match the light to the photo's key** (catchlight position, nose-shadow direction), then build the "breakdown sheet" for each camera: photo | render | 50% overlay | difference | flipped, at full size and at a ~64 px thumbnail.
12. **Fresh eyes:** someone who knows the sitter, a day's break, a held-out photo.

**What goes wrong**

| Symptom | Likely cause | Fix |
|---|---|---|
| Jaw too narrow, eyes too big | retouched press or cover photos | cross-check against untouched event photos |
| Nose too big, ears too small | selfie or close film still treated as distant | solve the focal length; weight down close shots |
| Face too wide or narrow in one film still | anamorphic frame not desqueezed, or a crop | check the aspect ratio; drop it |
| Older or heavier than intended | references span years or roles | one age and weight window |
| "Looks right only in the hero shot" | single-photo overfit; texture projection | held-out view; texture off |
| Grey clay never reads as them | no brows or hair; neutralised expression | proxy groom; optional characteristic-expression key |

## Algorithmic implications

- **Per-photo metadata record:** `source_type`, `exif_f35`, `date`, `mirrored`, `anamorphic_desqueezed`, `expression`, `retouch_risk`. Landmark σ = base σ (0.03×IOD interior, 0.06–0.08×IOD contour; `blender/sculpting-likeness-workflow.md`) × the Table 1 multiplier 🧠
- **Focal priors by source,** log-normal in f35 (σ_log = standard deviation of ln f) 🧠:
  - controlled capture: EXIF, σ_log 0.02;
  - phone selfie: 26 mm, σ_log 0.1;
  - phone rear: 26 mm, σ_log 0.6 (multi-lens);
  - event/press: 135 mm, σ_log 0.5;
  - studio/magazine: 100 mm, σ_log 0.4;
  - film or video: 50 mm, σ_log 0.7.
  
  The same priors are in `data/artstation-likeness.json`.
  Above ~3 m perspective carries almost no depth, so require profile views for depth.
- **Robust per-view down-weighting.** Estimate a per-view noise scale (IRLS or Cauchy loss). Flag a view whose jaw-contour and eye-size residuals show a consistent signed pattern not explained by pose: likely liquify. Cap any single view at ≤ 40% of the total data weight (no "hero photo") 🧠
- **Coverage gate:** require ≥ 3 yaw bins and ≥ 1 view with |yaw| ≥ 60°; otherwise warn that depth comes from the prior 🧠
- **Pixel aspect:** fixed at 1.0 (σ 0.01) unless flagged anamorphic; never estimate it freely from faces 🧠
- **Phone lens correction:** in shots with f35 ≤ 16 mm, or when the face lies beyond ~60% of the half-diagonal, inflate σ ×2 or exclude the photo, because the image may not be pinhole ↔️
- **Age-window check:** compare age-sensitive ratios across views solved at the same yaw (lower-face height, nasolabial depth proxies); warn about outliers > 3 robust SD ↔️
- **Brows and hairline as first-class targets.** Fit brow curves (≥ 5 points each) and a hairline polyline. Export them as Blender curves (groom guides) and keep them out of the skin-shape loss for the brow ridge 🧠
- **Identity marks as tie points.** User-clicked moles, scars and freckles seen in ≥ 2 views become extra bundle-adjustment correspondences and texture anchors 🧠
- **Expression:** fit the neutral identity from neutral photos only; export an optional "characteristic expression" shape key (0–1, default 0) fitted from flagged expression photos ↔️
- **Breakdown sheet generator:** per solved camera, output photo, render, overlay, difference, flip and thumbnail as one PNG, the automated version of the ArtStation side-by-side 🧠
- **Time budget:** reach primary-likeness tolerances (interior reprojection < 2–3% IOD, silhouette < 1–2 mm) in minutes, replacing the 20–35% blockout phase 🧠

## Disagreements, myths & open questions

- ↔️ **Camera match vs by eye.** Technical artists match cameras; several celebrated likeness artists compare by eye across many views, which works through averaging but hides focal-length errors.
- ↔️ **Sphere vs scan base vs wrap.** Spheres train seeing; scans give realism but bias toward the scanned person; fitted templates keep topology.
- ↔️ **Grey clay first vs "it clicks with hair".** Both hold: the profile must work in clay, and recognition needs brows and hair.
- ↔️ **Neutral vs characteristic expression** for the final piece.
- ↔️ **ZBrush vs Blender at very high resolution:** Blender sculpting has improved since 4.x, but many professionals still report ZBrush handles tens of millions of polygons more smoothly (time-sensitive).
- ↔️ **Ethics.** Most ArtStation likenesses depict celebrities without consent, and publicity rights vary by jurisdiction. This project requires consent; platform rules on depicting real people need checking.
- **Myth: "more photos are always better."** A curated set from one window beats an uncurated one 🧠
- **Myth: "the side-by-side proves the likeness."** It shows the best angle; ask for a held-out view 🧠
- **Myth: "detail and realism give likeness."** Pores add realism; identity sits in primary forms, brows and hair 🧠
- **Open questions:** no breakdown reports millimetre errors, so "it clicked" has never been tied to measured residuals; how much reported time is likeness correction rather than detailing; whether solved cameras cut the number of iterations.

## Sources

No web harvest or earlier draft existed for this topic, so no URLs are cited and every item is 🧠 or ↔️ pending verification. Cross-referenced library notes: `community/zbrush-to-blender-likeness.md`, `community/likeness-mistakes.md`, `community/reddit-face-from-photos.md`, `community/instagram-social-sculptors.md`, `community/ai-assisted-sculpting.md`, `blender/sculpting-likeness-workflow.md`, `blender/reference-camera-setup.md`, `blender/eyes-modeling-blender.md`.

**Further reading (by name, not yet linked)**
- ArtStation Learning; ArtStation Magazine / blog "making of" features; ArtStation Marketplace tutorials
- 80 Level artist breakdown interviews; 3dtotal making-of articles; The Gnomon Workshop likeness and portrait courses (titles unverified)
- KeenTools FaceBuilder documentation; Faceform (formerly R3DS) Wrap documentation; PureRef
- Texturing XYZ multichannel face maps; 3D Scan Store and Triplegangers head scans (licence terms to check)
- Scott Spencer, *ZBrush Digital Sculpting Human Anatomy* (2010)
- Uldis Zarins & Sandis Kondrats, *Anatomy for Sculptors* (2014)
- Philippe Faraut, *Mastering Portraiture*
- Farkas, *Anthropometry of the Head and Face*, 2nd ed. (1994)
- Ward et al., selfie nasal distortion, *JAMA Facial Plastic Surgery* (2018)
- Sinha & Poggio, "I think I know that face…", *Nature* (1996)
- Jenkins, White, Van Montfort & Burton, "Variability in photos of the same face", *Cognition* (2011)
- Rhodes, Brennan & Carey, caricature identification, *Cognitive Psychology* (1987)
