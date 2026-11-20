# Classic art-anatomy references for heads

> **Status: NOT RESEARCHED. 0 sources, 0 verified claims.** The harvest pass (11 of 11 queries) and this verification pass (3 of 3 attempted searches, run 2026-11-20) were both refused because the shared per-turn WebSearch budget (200 calls per turn) had run out. Page fetching is unavailable in this sandbox, and the repository has no earlier research notes on Loomis, the Reilly method, Asaro, Peck, Bridgman, Scott Spencer or Uldis Zarins. This note therefore contains **no facts, no numbers and no citations**. It records what to verify, a ready-to-run search plan, and design guidance for how the fitting engine and add-on should *consume* art-anatomy canons. That guidance is engineering reasoning that does not depend on any specific canon value. Rerun this topic in a fresh turn before anything here is relied on.

## Key facts

None verified. Nothing in this note may be cited as a fact about these books or methods until the rerun fills this section with sourced bullets (✅ / ⚠️ / ↔️).

### Claims queued for verification (questions, not facts)

These are the claims that matter most for a 3D artist or a fitting algorithm. They are written as questions on purpose, so that no unverified value enters the library.

| # | Question to answer with 2+ independent sources | Why it matters downstream | Best source type |
|---|---|---|---|
| Q1 | How does Loomis build the cranium (ball, side planes) and attach the face? Where does he place the brow line, nose base and chin relative to the ball? Does he divide the face into equal vertical thirds, and from which landmarks? | Blocking scaffold and vertical-proportion prior | Book text (archive.org scans, publisher pages), art-school syllabi |
| Q2 | Where does Loomis put the eye line relative to total head height, and how does that compare with measured adult populations? | Commonly used "sanity check" whose population validity is unknown | Book text plus anthropometry papers (PMC) |
| Q3 | What are the horizontal canons (eye width vs head width, inter-eye gap, mouth width vs pupils or irises, nose width vs inner canthi, ear height vs brow and nose)? Which author states each one? | Horizontal-proportion priors | Book text, anthropometry papers testing "neoclassical canons" |
| Q4 | What is the Reilly method (Frank Reilly's "abstraction" or rhythm lines)? Which secondary sources teach it, and what landmarks does it use? | Region and curve vocabulary for sculpt guides | Atelier or teacher pages, practitioner forums |
| Q5 | Who made the Asaro head (John Asaro), when, and in what variants (planar, female, skull)? Is it sold under a licence that allows use of the plane layout? | Plane segmentation masks; possible IP constraints | Vendor or official pages, interviews |
| Q6 | Which Stephen Rogers Peck book is the head reference (title, first-edition year, publisher)? What does it cover for skull and facial muscles? | Bibliography accuracy | Publisher or library catalogue |
| Q7 | Which Bridgman titles cover the head ("Constructive Anatomy" and others), with years? What is his "wedging"/block approach, and is the work public domain? | Licensing of diagrams for the docs; block-in method | archive.org, Project Gutenberg, library catalogues |
| Q8 | What are Scott Spencer's anatomy and ZBrush books (exact titles, publisher, years)? What does his head and face chapter teach (skull landmarks, fat pads, muscle-to-form)? | Digital-sculpting-native reference; terminology for UI | Publisher (Wiley/Sybex), Gnomon, ArtStation |
| Q9 | "Anatomy of Facial Expression" by Uldis Zarins (with Sandis Kondrats?): year, publisher (Anatomy Next / Exonicus?), page count, method (muscle-by-muscle expression breakdown, 3D-scan based?) | Expression layer and AU or blendshape mapping | Publisher page, reviews, Amazon or Goodreads listings |
| Q10 | Which of these do professionals recommend most for head likeness, and why (Reddit r/learnart, r/ZBrush, Polycount, ArtStation, BlenderArtists)? Collect at least 3 independent threads per claim. | "Best reference" claim for the docs | Forums (practitioner opinion only) |
| Q11 | What are the documented criticisms: idealization, a single body type or ethnicity, the hairline as an unreliable landmark, Loomis "mannequin" faces hurting likeness? | Myths and limits section | Forums, art-education essays, anthropometry papers |
| Q12 | Do anthropometric studies test classical or neoclassical facial canons, and what fraction of subjects meet each one? (Search lead: work associated with L. G. Farkas on neoclassical canons. The title and year must be confirmed before citing.) | Converts art canons into priors with variance | PMC / NCBI, Plastic & Reconstructive Surgery |

## Numbers & reference tables

No sourced values were obtained, so this section and `research/data/art-anatomy-books.json` are intentionally left out. The rerun should fill this template. Every row needs a URL, and every canon needs a matching anthropometric row with mean, SD and sample size.

| Canon (as stated by author) | Author / book | Landmark pair A | Landmark pair B | Stated ratio A:B | Measured ratio mean ± SD | Population, n | Source(s) | Status |
|---|---|---|---|---|---|---|---|---|
| Face vertical thirds | (confirm) | trichion–nasion (or glabella) | nasion–subnasale | — | — | — | — | not researched |
| Lower face thirds | (confirm) | subnasale–stomion | stomion–menton | — | — | — | — | not researched |
| Eye line height | Loomis (confirm) | vertex–endocanthion line | vertex–menton | — | — | — | — | not researched |
| Eye width vs face width | (confirm) | en–ex | zy–zy or eu–eu | — | — | — | — | not researched |
| Inter-canthal = eye width | (confirm) | en–en | en–ex | — | — | — | — | not researched |
| Nose width vs inter-canthal | (confirm) | al–al | en–en | — | — | — | — | not researched |
| Mouth width vs pupils | (confirm) | ch–ch | pupil–pupil | — | — | — | — | not researched |
| Ear height vs nose | (confirm) | sa–sba | n–sn | — | — | — | — | not researched |

Landmark abbreviations follow standard craniofacial anthropometry (tr trichion, n nasion, sn subnasale, sto stomion, me menton, en endocanthion, ex exocanthion, al alare, ch cheilion, zy zygion, eu euryon, sa/sba superaurale/subaurale). The rerun must confirm this naming against a primary anthropometry source.

## Applying this to photo→3D face sculpting in Blender

*The points below are design reasoning for the add-on. They are not claims sourced from the books. They hold whatever the canon values turn out to be.*

1. **Use canons for blocking, never as targets for likeness.** A Loomis- or Bridgman-style block-in (cranial mass, face front plane, side planes, jaw wedge) is useful for building a correct base before photo fitting, for example a "Block-in" operator that places a sphere-plus-jaw proxy from 3-5 clicked landmarks. Once photo landmarks exist, the subject's measured ratios must win. Likeness lives in how a person deviates from the canon, so snapping to the canon erases it.
2. **Measure canons on the fitted 3D mesh in a canonical frame, not on the photo.** In a 2D photo, vertical ratios such as brow/nose/chin thirds shift with head pitch, and every ratio shifts with lens perspective at short camera distance. Run canon checks only after the head is posed in a fixed reference orientation (Frankfurt-horizontal-style alignment) with intrinsics estimated or supplied.
3. **Prefer stable skeletal landmarks.** Trichion (hairline) is soft-tissue and hair-dependent and is not stable in adults with receding or styled hair, so any "thirds" check anchored on the hairline should carry low weight. Nasion, subnasale, menton, the canthi and the tragus are better anchors.
4. **Plane maps as a lighting check.** An Asaro- or Reilly-style plane partition can be added as vertex groups on the base topology. A single-key-light render compared against the reference photo shows plane-orientation errors (cheek front-to-side turn, brow ridge, mouth barrel) that landmark error alone misses. Confirm the Asaro IP and licence status (Q5) before shipping a copy of its exact plane layout.
5. **Separate identity from expression.** Fit identity from neutral photos only. Expression knowledge (the Zarins-type muscle-by-muscle breakdown) belongs in a separate shape-key or FACS-AU layer, cross-referenced to FACS action units. Never use it to explain away identity residuals.
6. **What usually goes wrong (to confirm against practitioner sources in Q10/Q11):** idealized "mannequin" faces, an eye line placed by rule rather than measured, ears placed by canon rather than from the profile photo, and symmetric canons applied to asymmetric faces.

## Algorithmic implications

*Engineering design. Every numeric default is pending the rerun.*

- **Represent each canon as a named soft prior:** `{name, landmark_pairs: (A, B), stated_ratio, pop_mean, pop_sd, population, n, source_urls, weight}`. Art books give single idealized values without variance, so `pop_mean` and `pop_sd` must come from anthropometric data, not from the art book. If no population data exists, keep `weight = 0` (display only).
- **Prior strength should decay with evidence.** Energy term: `w_canon * Σ ((r_subject − pop_mean) / pop_sd)^2`, with `w_canon` falling as photo coverage of that region rises. A frontal-only fit leaves depth ratios (nose projection, ear position) under-constrained, which is where a canon or population prior should be allowed to act.
- **Never hard constraints.** Hard canon constraints would force every fit toward one idealized face and remove likeness.
- **Deviation report as a product feature.** Report the subject's z-score for each canon ratio. Large |z| values are the likeness-defining features a sculptor should preserve or accentuate. This makes the art-anatomy vocabulary (thirds, eye widths, planes) the explanation layer of the UI rather than an input.
- **Region masks from plane theory.** Define vertex groups for the major planes (forehead front and sides, temporal, orbital, zygomatic front and side, nasal dorsum and sides, maxillary barrel, mental, mandibular sides) on the template topology. Use them for per-region regularization weights and for targeted sculpt brushes. Plane names and boundaries must be checked against the sourced plane maps (Q4, Q5).
- **Expression layer.** If Zarins (Q9) maps expressions to specific muscles, mirror that as a muscle→AU→shape-key table so expression shapes are anatomically named. Identity fitting must zero this layer.
- **Provenance in data files.** Every prior loaded by the engine should carry its `source_urls` and `status`. The loader should refuse `status: "not researched"` entries for non-zero weights. That rule applies to every row this note could have produced today.

## Disagreements, myths & refuted claims

None assessed, because no sources were retrieved. Debates the rerun should investigate:

- Whether idealized canons (Loomis-type proportions) describe real adult populations, or only a stylized ideal. Anthropometric studies of "neoclassical canons" are the right test (Q12).
- Whether planar methods (Asaro, Reilly) help or hurt photographic likeness compared with landmark measurement. This is expected to be practitioner opinion only.
- Whether the "eyes at half head height" style of rule (to be confirmed as an actual teaching, Q2) holds across ages and sexes. It is expected to vary with age, because cranial versus facial growth changes the proportions in children.
- Attribution confusion. Readers can mix up the Reilly method (Frank Reilly) and the Asaro head (John Asaro), and Uldis Zarins' "Anatomy for Sculptors" line and his "Anatomy of Facial Expression" title. The exact titles and co-authors need confirming.

Refuted: none (nothing was tested).

## Open questions

- All of Q1–Q12 above.
- Are Bridgman's and Loomis's head books in the public domain in the US or EU? This decides whether their diagrams can be reproduced in the add-on docs. It needs exact first-publication years and renewal status, from a primary source.
- Is there any published quantitative comparison between the Asaro plane layout and real scanned faces (for example, plane normals compared with mean-face normals)?
- Which canon ratios differ by sex, age and population enough that a single default is harmful? Each prior needs a population tag, and the add-on needs a population selector or a broad default SD.
- Do professional likeness sculptors (ArtStation, Gnomon, Scott Spencer's teaching) recommend these books for likeness, or only for generic anatomy? Likeness-specific advice may come mostly from caricature and portrait-sculpting sources instead.

### Search plan for the rerun (about 18 calls)

1. `Loomis "Drawing the Head and Hands" head construction ball side plane brow line thirds` (standard). Then `allowed_domains: ["archive.org"]`.
2. `Loomis head proportions eye line halfway criticism likeness`, `allowed_domains: ["reddit.com"]`.
3. `Reilly method head abstraction rhythms Frank Reilly Art Students League` (standard).
4. `John Asaro planes of the head model history`, then `Asaro head licence reproduction`.
5. `Stephen Rogers Peck Atlas of Human Anatomy for the Artist head muscles` (title to confirm).
6. `George Bridgman Constructive Anatomy head public domain year`, `allowed_domains: ["archive.org","gutenberg.org"]`.
7. `Scott Spencer ZBrush Digital Sculpting Human Anatomy head chapter` (title to confirm), plus Polycount and ArtStation domains.
8. `Uldis Zarins Anatomy of Facial Expression Anatomy Next review`; extended mode if thin.
9. `best anatomy book for sculpting faces likeness recommended`, `allowed_domains: ["reddit.com","polycount.com","blenderartists.org","artstation.com"]`.
10. `neoclassical facial canons anthropometry Farkas proportion validity`, `allowed_domains: ["ncbi.nlm.nih.gov","pmc.ncbi.nlm.nih.gov"]`.
11. `facial thirds proportion adults anthropometric study mean SD`, PMC domains.
12. `eye width intercanthal distance ratio canon anthropometric`, PMC domains.

## Sources

None. No search returned results in either pass (budget exhausted). No URL, title, year or number in this note comes from a retrieved source, and the book and author names are taken from the task brief. `research/sources/art-anatomy-books.json` is written with an empty source list to match.
