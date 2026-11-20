# Polycount: likeness sculpting knowledge

> Polycount, the long-running game-art forum and wiki, comes at likeness from the realtime-character side. Critique arrives as paintovers and liquify-overs on a render placed beside a reference at a matched angle and lens, with "post wires" and "show the clay" as standing demands. The verdicts recur: the camera does not match the photo; the cranium and neck are undersized; the eyes are too big, too proud or thin-lidded; the lips do not wrap the teeth; the ears are misplaced; the face is too symmetric and too young; and likeness won in the sculpt is lost again in retopology, baking, shading or hair. Professional advice converges on coarse-to-fine gating, many long-lens references from one period, a scan or base-mesh start wrapped to the subject, and judging only through matched cameras under matched light. No harvest or earlier draft existed and no Polycount URL appears anywhere in the library, so everything below is expert knowledge or pinhole arithmetic; for the engine it becomes stage gates, one-sided hair and beard silhouette bounds, paintover ingestion, a critique lint and an export likeness check.
>
> Evidence status: 0 ✅ / 0 📄 / 60 🧠 / 25 ↔️ — verified 2026-11-20: Hertel, MRD1 and ear-tilt ranges found population-dependent (↔️); remaining 🧠 items unconfirmed.

## Key facts

**The forum and how it critiques**
- Polycount is a game-art community from the late-1990s modding era, with a forum and a community wiki best known for topology, baking and realtime-character knowledge rather than fine-art portraiture. Founding year, forum platform, wiki host and current activity (much critique has moved to ArtStation and Discord) are time-sensitive 🧠
- Likeness work appears in showcase-and-critique WIP threads and long-running personal sketchbooks, often as short portrait studies 🧠
- **Critique etiquette:** reference beside render at the same angle ("no ref, no likeness crit"); an untextured clay render first; wireframes on request ("post wires"), with topology critiqued separately from likeness; a turntable or embedded 3D viewer (Marmoset Viewer and Sketchfab are typical) 🧠
- **The paintover is the most actionable critique.** A critic warps the render in a 2D editor (Liquify) or draws over it. It is single-view: a fix made to satisfy one paintover can break the other views, so professionals re-check every matched camera before accepting it 🧠
- **Priority order of critique:** silhouette and head mass → feature placement → feature shape → surface and skin → shading. "Polishing the wrong shape" and "noodling" are the classic rebukes for detailing early 🧠

**Recurring likeness verdicts** (a synthesis of the critique genre, not a count)
- **Lens mismatch:** render through a wide default camera against a long-lens photo, or a selfie traced as if distant; nose and mid-face size come out wrong. Critics ask for matched FOV before judging anything else 🧠
- **Cranium and neck too small:** hair hid the skull; the neck lacks sternocleidomastoid and trapezius mass and reads as a "floating mask" 🧠
- **Eyes:** too large; too far forward (not seated in the orbit); lids paper-thin; caruncle, tear-line meniscus and corner occlusion missing; sclera showing above the iris (stare); "dead eyes" from missing wetness and specular 🧠
- **Mouth:** lips "stuck on" instead of wrapping the dental arch; corners not tucked into the modiolus; volume idealised 🧠
- **Nose:** width and projection wrong (the most lens-sensitive feature); generic nostrils; alar base too far forward 🧠
- **Ears:** generic, too low, too far forward or too upright, and checked last 🧠
- **"His brother, not him":** over-symmetric, idealised, younger, with the artist's default face creeping in ("every painter paints himself"; evidence for self-resemblance in portraits is mixed) ↔️
- **Reference drift:** references spanning years or weight changes; a smile in the reference against a neutral sculpt 🧠
- **Likeness lost downstream:** retopology, normal-map baking (lip line and lid margin shift with cage or ray distance), engine shading (SSS, specular) and hair cards. Professionals judge likeness with brows and hair on, since hairline and brows carry identity, and shape with them off 🧠

**Professional workflow tips that recur**
- **References:** 20–50+ photos from one period, sorted by angle on a reference board (PureRef is typical); prefer long-lens press and red-carpet images over close wide shots; film stills give angles but unknown lenses; keep neutral frames 🧠
- **Caricature handles:** list the 3–5 features where the sitter departs most from average and protect them through every pass, the caricaturist's method (caricature research: Rhodes, Brennan & Carey 1987) 🧠
- **Start point:** a scan-derived generic head or base mesh wrapped to the subject (R3DS Wrap, reportedly rebranded Faceform Wrap, in many pro pipelines) versus a sphere or DynaMesh blob for learning ↔️
- **Low resolution first:** block masses at the lowest subdivision with a large Move brush; step up only when the lower level matches in every view 🧠
- **Proxies early:** eyeball spheres before lids; a dental-arch proxy before lips 🧠
- **Many cameras:** Maya image planes, ZBrush Spotlight and stored views; compare in each 🧠
- **Matched light:** key the sculpt like the reference; check in grayscale and at thumbnail size, flip, and come back with fresh eyes 🧠
- **Symmetry:** on for blockout, off once primary forms agree in all views, then reintroduce the sitter's real asymmetry; when to switch is disputed ↔️
- **Practice:** many short studies beat one long piece 🧠
- **Approvals:** licensed likenesses (games, collectibles) go through talent or licensor approval rounds, so pros keep edits reversible (layers, morphs) 🧠

**Scan versus hand likeness**
- Realistic AAA actors are now mostly scanned (photogrammetry rigs, light stages), then cleaned and retopologised. Hand likeness from photos remains for people who cannot be scanned. Attitudes run from pragmatic ("the scan is reference; the artist still makes it read") to purist ↔️

## Numbers & reference tables

**Table A — Polycount verdict → measurable check.** Adults, neutral face, mostly European-derived norms; values kept consistent with `community/likeness-mistakes.md` Table A.

| Verdict | Measure | Typical adult value | Flag when | Badge |
|---|---|---|---|---|
| "Lens doesn't match" | camera→nose distance Z; nose-tip/tragion magnification 1 + d/Z (d ≈ 10 cm) | Z ≥ 1.5 m → ≤ 1.07; 0.5 m → 1.20 | render Z differs from photo Z by > 25%; photo Z < 0.8 m | 🧠 (geometry) |
| "Eyes too big" | iris diameter (HVID); iris / en–ex | 11.7 ± 0.5 mm; 0.34–0.44 | ratio outside range | 🧠 |
| "Eyes popping" | cornea apex ahead of lateral orbital rim (Hertel) | 12–20 mm; L–R ≤ 2 mm; published adult ranges run 8–23 mm by population (Caucasian means 15.4–16.5, Asian 8–20, adult range 11–23) [1][2] | outside range | ↔️ ancestry |
| "Staring" | upper-lid cover of iris; MRD1 | 1–2 mm (unconfirmed); MRD1 3.5–4.5 mm in sources (4.0–4.5 trial protocol, 3.5 ± 0.8 normative study) [3][4] | sclera above iris without photo support | ↔️ |
| "Paper lids" | upper-lid margin thickness | ≈ 1.5–2.5 mm | < 1 mm | 🧠 |
| "Mouth too wide" | ch–ch / IPD (IPD 63 ± 3.5 mm) | 0.78–0.90 | ≥ 1.0 at rest | 🧠 |
| "Lips stuck on" | cheilion behind labrale superius (profile) | roughly 1.5–2 cm (uncertain) | < 1 cm | ↔️ |
| "Nose wrong" | al–al / en–en | ≈ 1.0–1.3 | outside 0.9–1.4 | ↔️ ancestry |
| "Ears too low" | tragion height vs orbitale (Frankfort) | ≈ level | > 8 mm off after pitch is solved | 🧠 |
| "Ears too upright" | ear long-axis tilt from vertical | 10–30° (≈ 20°); one adult male study 15.6 ± 3.9°, other cohorts report >25° in ~12–14% [5] | < 5° | ↔️ |
| "Skull too small" | head length g–op / breadth eu–eu | 175–205 / 140–160 mm | g–op short vs profile | ↔️ |
| "Neck too thin" | neck circumference | ≈ 36–42 cm men, 30–36 cm women | below range without photo support | 🧠 |
| "Too symmetric" | whole-face mirror RMSD | ≈ 0.8 mm (library value) | < 0.3 mm | 🧠 |

**Table B — Subdivision ladder.** Quad counts are exact arithmetic (×4 per level from a 2,000-quad head); the "fix here" column is studio guidance.

| Level | Quads | Fix at this level | Badge |
|---|---|---|---|
| 0 | 2k | cranium length and breadth, face height, jaw width, neck | 🧠 |
| 1 | 8k | placement: orbits, nose mass, mouth barrel, ear position | 🧠 |
| 2 | 32k | feature shapes: lids, alae, vermilion border, helix | 🧠 |
| 3 | 128k | soft tissue: nasolabial fold, malar fat, tear trough, lid folds, age | 🧠 |
| 4 | 512k | wrinkles and creases | 🧠 |
| 5–6 | 2M–8M | pores and micro-skin (often from scans or tiling skin maps) | 🧠 |

**Table C — Realtime head budgets in game-art discussion.** Orders of magnitude only, not standards.

| Use | Head LOD0 triangles | Texturing | Badge |
|---|---|---|---|
| PS3/360-era hero | ≈ 3k–8k | 1–2k maps | ↔️ |
| PS4/XB1-era hero | ≈ 10k–30k | 2–4k plus detail normal | ↔️ |
| Current-gen hero / cinematic | ≈ 30k–100k+ | 4k–8k or UDIMs plus tiling micro-normal | ↔️ |
| MetaHuman LOD0 face | tens of thousands of vertices; exact count to verify | UDIM-style | ↔️ |

**Table D — Suggested retopology/bake likeness tolerances** (engineering suggestion, not a community standard)

| Region | Max deviation sculpt → game mesh + normal map | Badge |
|---|---|---|
| Lid margins, vermilion border, alar rim | 0.2–0.3 mm | 🧠 |
| Nose tip, ear rims, chin | 0.5 mm | 🧠 |
| Cheeks, forehead, cranium front | 1.0 mm | 🧠 |
| Back of head, neck | 1.5–2 mm | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Build the critique sheet for yourself.** For each solved camera (`to_blender_camera`): photo | clay render under matched light | 50% overlay | Difference | black silhouette, plus a wireframe and a turntable. Bind each camera to a timeline marker (Timeline › Marker › Bind Camera to Markers, Ctrl+B) so scrubbing flips views 🧠
2. **Audit references.** One period, neutral expression. Estimate distance as d ≈ f_px · 63 mm / IPD_px. Use photos closer than 0.8 m for texture and expression only, never proportions, and reject mirrored or filtered selfies 🧠
3. **Proxies first.** Eyeball spheres (r ≈ 12 mm) with a corneal bulge, a dental-arch proxy, and hair and beard volumes as separate objects so silhouettes can be judged with and without them 🧠
4. **Climb Table B on Multires.** At levels 0–1 use Grab, Elastic Deform and Snake Hook with a large radius, or a Lattice for the cranium; do not go up a level until the lower one matches in every camera 🧠
5. **Paintover loop.** Export the sheet, paint over or Liquify it in Krita, GIMP or Photoshop, then apply with Grab from the same camera. Accept a change only after it reads better in every other camera too 🧠
6. **Light.** One soft area light at the photo's key direction; judge in grayscale. Matcaps are for form reading, not likeness verdicts 🧠
7. **Hair and brows.** Before a final verdict add brow and hairline proxies (curves, cards or painted texture). Judge likeness with them on and shape with them off 🧠
8. **Symmetry.** Switch it off once Table B level 1 matches; re-add asymmetry only where two or more views agree (`anatomy/facial-asymmetry.md`) ↔️
9. **Downstream check.** If you retopologise or bake, write sculpt-to-low distance to an attribute (Geometry Nodes Geometry Proximity) and colour against Table D 🧠
10. **Sitter sign-off.** Show the consenting sitter the sheet in both mirror and true orientation, collect region notes ("nose a bit wider"), apply them as reversible shape keys and record the approval 🧠

**What goes wrong:** a likeness that works only in the projecting camera (texture projection, one-view overfit); ears that are wrong in every view (unsolved pitch); a "cousin" (symmetry and idealisation); a perfect clay head that dies in Eevee (eyes, shading, hair). See `community/likeness-mistakes.md`, `community/zbrush-to-blender-likeness.md` and `blender/sculpting-likeness-workflow.md` 🧠

## Algorithmic implications

- **Stage gates** (suggested defaults, IOD = interpupillary ≈ 63 mm) 🧠
  - **A, masses:** release features when the front and profile silhouette chamfer (`fit_silhouettes`) is < 2% of face height n–gn and landmark RMS is < 4% IOD.
  - **B, features:** release surface detail when detector-landmark RMS is < 3% IOD (user-checked pins < 1.5%) in every view, including one held-out photo.
  - **C, surface:** no landmark may move more than 0.5 mm during detail passes; flag any that does.
- **Symmetry schedule:** `Priors.sigma_sym` 1.0 mm in A, 2.0 mm (engine default) in B, 4.0 mm in C, keeping `sigma_mid` at 1.5 mm throughout ↔️
- **One-sided hair and beard bounds.** Hair and beard silhouettes are outer bounds, not targets. Use a hinge penalty when the scalp or jaw surface projects outside the hair or beard contour (margin 0–3 mm), with no pull inward. Fill the skull shape from a cranial prior: g–op 175–205 mm, σ ≈ 7 mm within a sex-specific population, plus scalp soft tissue ≈ 4–8 mm over bone 🧠
- **Paintover ingestion.** Given render R and paintover P from camera k, estimate a dense 2D flow w = flow(R → P). For each visible vertex with projection Jacobian J_i (2×3), solve min Σ‖J_i Δx_i − w(u_i)‖²/σ_w² + λ‖L Δx‖² + Σ_{k′≠k} reprojection terms, with L the cotan Laplacian. Depth is free in one view, so the Laplacian, priors and other views fix it. Reject or down-weight the edit if any other view's landmark RMS rises by more than 0.5% IOD. Default σ_w ≈ 2 px at the paintover resolution 🧠
- **Critique lint.** Compute Table A on every fit and flag only unsupported deviations: |model − photo| > 2σ_photo, or population |z| > 2.5 where no photo sees the feature. Never pull a photo-supported feature toward the mean 🧠
- **Caricature handles.** Let the user tag 3–5 distinctive regions; raise their landmark weights ×2 and exclude them from prior shrinkage, so averaging cannot erase them ↔️
- **Region sliders for approvals.** Build masked deformation bases (eyes, nose, mouth, jaw, ears, cranium) on `ReducedDeformer`, each limited to ±3 mm and exported as named shape keys, so sitter feedback stays reversible and logged 🧠
- **Loop preservation.** After `RBFWarp`, measure quad angle distortion around the eye and mouth loops; if cranium or jaw scale changes > 10%, prefer an ARAP solve to plain `laplacian_deform` so animation loops survive 🧠
- **Export likeness check.** On export to a game topology, compute per-vertex deviation against Table D and block "likeness-approved" status if lid, lip or alar regions exceed tolerance 🧠
- **Critique-sheet generator.** Render photo, clay, overlay, difference, silhouette, wireframe, flipped and 64 px thumbnails per solved camera, numpy-side, so it is Blender-version-independent; share it for critique only as far as the sitter's consent covers 🧠
- **Soft landmarks.** Hairline (trichion) σ ≈ 3–5 mm; brows ≈ 2 mm; never use either for camera solving 🧠

## Disagreements, myths & open questions

- ↔️ **Scan versus hand sculpt:** whether scan-based likeness counts as craft; settled in practice by production needs.
- ↔️ **Sculpt versus texture:** how much likeness lives in skin colour, brows and lip borders rather than form. Untextured clay heads often read weaker than their geometry deserves.
- ↔️ **Symmetry timing** and **base mesh versus sphere** starts.
- ↔️ **Orthographic front and side planes:** still common in box-modelling tutorials; matched perspective cameras are the modern professional norm. Planes are fine for blocking only.
- ↔️ **"Every painter paints himself":** a persistent adage with mixed evidence; the fix (overlay, held-out views, fresh viewers) is the same either way.
- 🧠 **Myth: a paintover is ground truth.** It is one view and one critic's eye.
- 🧠 **Myth: golden-ratio or "beauty mask" templates help likeness.** They push towards an ideal, which is the opposite of likeness.
- ↔️ **Myth: "the eyes are the likeness."** Head shape, configuration, brows and hairline all carry identity.
- ↔️ **Generative AI** (2023–2026): game-art communities including Polycount have been largely sceptical; forum policies are time-sensitive.
- ↔️ **Likeness rights:** celebrity likenesses in portfolios are common but legally grey and jurisdiction-dependent. This project's model, a consenting sitter with a recorded approval, avoids that.
- **Open questions:** no Polycount thread has been harvested; which threads and wiki pages (face topology, edge loops) to cite; whether any thread gives quantitative likeness tolerances; a frequency count of critique categories in portrait WIPs.

## Sources

No Polycount URL appears in the library. Verification sources (2026-11-20):

1. AAO EyeWiki, Exophthalmometry: https://eyewiki.aao.org/Exophthalmometry
2. Normal Values of Hertel Exophthalmometry in a Chinese Han Population: https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4336939/
3. AAO EyeWiki, Margin to Reflex Distance 1,2,3: https://eyewiki.aao.org/Margin_to_Reflex_Distance_1,2,3
4. LEV102 Topical Gel in Acquired Blepharoptosis protocol (MRD1 normal 4.0–4.5 mm): https://cdn.clinicaltrials.gov/large-docs/46/NCT05715346/Prot_000.pdf
5. Ear inclination in adult Rakhain males (Bangladesh): https://banglajol.info/index.php/JNINB/article/view/59937/41251
 Cross-referenced library notes: `community/likeness-mistakes.md`, `community/zbrush-to-blender-likeness.md`, `community/blenderartists-forum.md`, `blender/sculpting-likeness-workflow.md`, `blender/reference-camera-setup.md`, `blender/eyes-modeling-blender.md`, `anatomy/facial-asymmetry.md`, `anatomy/ear.md`.

**Further reading (by name, not yet linked)**
- Polycount wiki: topology and edge-loop pages (page names unverified)
- Farkas, *Anthropometry of the Head and Face*, 2nd ed., 1994
- Scott Spencer, *ZBrush Character Creation: Advanced Digital Sculpting* (Sybex); *ZBrush Digital Sculpting Human Anatomy* (Sybex, 2010)
- Zarins & Kondrats, *Anatomy for Sculptors: Understanding the Human Figure*, 2014; Zarins, *Anatomy of Facial Expression*, 2017
- Faigin, *The Artist's Complete Guide to Facial Expression*, 1990
- Goldfinger, *Human Anatomy for Artists*, 1991
- Rhodes, Brennan & Carey, identification and ratings of caricatures, *Cognitive Psychology*, 1987
- Mori, "The Uncanny Valley", *Energy*, 1970
- Jimenez et al., "Next-Generation Character Rendering", GDC 2013 (to verify)
- Ward et al., nasal distortion in short-distance photographs, *JAMA Facial Plastic Surgery*, 2018
- Sorkine & Alexa, "As-Rigid-As-Possible Surface Modeling", SGP 2007
- Hartley & Zisserman, *Multiple View Geometry in Computer Vision*

## Verification log (2026-11-20)

- Eye-seating priors (Hertel 12–20 mm, L–R ≤ 2 mm): contested. Hertel ranges vary by population, about 8–23 mm; Caucasian means 15.4–16.5 mm, Asian 8–20 mm. https://eyewiki.aao.org/Exophthalmometry ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4336939/
- MRD1 4–5 mm: contested, sources give 3.5–4.5 mm. https://cdn.clinicaltrials.gov/large-docs/46/NCT05715346/Prot_000.pdf ; https://eyewiki.aao.org/Margin_to_Reflex_Distance_1,2,3
- Upper lid covers 1–2 mm of iris; lid margin thickness 1.5–2.5 mm; L–R ≤ 2 mm: unconfirmed (no source found).
- Head length g–op 175–205 mm, σ ≈ 7 mm; scalp soft tissue 4–8 mm: unconfirmed (ANSUR II has head length and neck circumference, but no figures retrieved; scalp thickness not found).
- Ear tilt 10–30°: contested, 15.6 ± 3.9° in one adult male cohort, >25° in some; tragion level with orbitale: unconfirmed. https://banglajol.info/index.php/JNINB/article/view/59937/41251
- Neck circumference 36–42 cm men / 30–36 cm women: unconfirmed (ANSUR II report NATICK/TR-15/007 https://apps.dtic.mil/sti/pdfs/ADA611869.pdf holds the tables, not retrieved).
- Cheilion 1.5–2 cm behind labrale superius: unconfirmed.
