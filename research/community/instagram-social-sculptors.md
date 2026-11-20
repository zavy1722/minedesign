# Instagram and social media sculptors' tips

> **Status: evidence gap. No technique content verified.** The harvest and this verification pass both ran into a shared WebSearch limit (200 calls per turn across all agents). The harvester ran 1 of its 5 planned queries, and all 3 verification searches attempted in this pass were refused. The only material retrieved is five Instagram profile pages whose search snippets show bios and follower counts. They contain no likeness tips, proportion methods, measurements or recurring advice from named sculptors. This note records exactly what was found and lists the checks that still need sourcing. It also sets out how the add-on and fitting engine should take in social-media practitioner advice once it is harvested. Nothing below should be read as a confirmed sculpting rule.

## Key facts

- The Instagram account `@societyofportraitsculptors` describes itself as "Professional sculptors committed to making portrait sculpture accessible to a wider public". This is the bio text from a search snippet, and no technique content was visible [1]. ⚠️ single-source
- The accounts `@charactersculpt`, `@sculptor_artists` and `@clayshaper` came up for a query on Instagram portrait-sculptor likeness and proportion tips. Their snippets showed only bio and follower information, with no method content [3][4][5]. ⚠️ single-source
- `@cooleblumen` (Inese Veismane) appears as a clay-tutorial account. From the snippet, the tutorials seem to be about clay flowers, not portraits, so it is not relevant to likeness work and is excluded from further use [2]. ⚠️ single-source
- Web search snippets for Instagram profile pages showed bios, not post captions or reel text. None of the five results gave access to a sculptor's actual advice [1][2][3][4][5]. ⚠️ single-source (observed in one harvest)
- No TikTok, X or Threads content was retrieved. The harvester's queries for those platforms never ran ("NOT RUN, search budget exhausted"), so there is nothing to cite for them.
- **No claims were verified.** Three independent cross-check searches were attempted in this pass, and all three were refused for budget, not answered empty:
  - Philippe Faraut portrait sculpting and likeness proportions
  - ZBrush likeness tips on reference-photo focal-length distortion
  - Reddit discussion of mirror and flip proportion checks

  So the absence of results says nothing about what these sources contain.

## Numbers & reference tables

None of the sources gave a numeric value, so this section holds **no numbers**, by design. The table below is a harvest checklist: the values a fitting algorithm or Blender user would need from practitioner sources. Each one still needs a primary or independent anthropometric source before it goes into code.

| Quantity to source | Units | Why the tool needs it | Practitioner source type to look for | Status |
|---|---|---|---|---|
| Vertical position of eye line within total head height | ratio of head height | Blockout grid default and sanity check on landmark fit | Clay portrait instructors' process posts, books | not sourced |
| Facial thirds (hairline to brow, brow to nose base, nose base to chin) | ratio | Region-wise scale priors | Same | not sourced |
| Head width in eye-widths | count | Width prior for blockout | Same | not sourced |
| Reference-photo focal length recommended by likeness sculptors | mm (35 mm equiv.) | Default `f35` when EXIF is missing; warning threshold for wide-angle selfies | Digital likeness artists' process notes | not sourced |
| Camera-to-subject distance for reference shoots | m | Perspective-distortion warning | Same | not sourced |
| Number and angles of reference views used for a likeness | count, degrees yaw | Minimum photo set the add-on should request | Process breakdowns, reels | not sourced |
| Caliper or measurement points that clay portraitists take from a live sitter | named landmark pairs | Mapping to the engine's landmark set and measurement UI | Clay portrait demos | not sourced |

No `data/instagram-social-sculptors.json` file was written, because no values could be sourced.

## Applying this to photo→3D face sculpting in Blender

None of the points below comes from the retrieved sources. They are engineering recommendations for making use of social-media advice safely once it is harvested.

1. **Treat every social-media tip as a hypothesis with provenance.** For each tip, record:
   - the handle and post or reel URL
   - the post date
   - the medium (clay or digital) and the software if stated
   - whether it is a **construction rule** ("place X at Y") or a **diagnostic check** ("compare A against B")

   Diagnostic checks transfer to a photo-fitting workflow far better than construction rules. Construction rules are often canonical-head conventions, while a photo-based likeness should come from the subject's own measurements.

2. **Make camera matching the backbone, so lens advice becomes data rather than folklore.** The engine already estimates focal length during PnP (`face3d/solve/pnp.py`) and converts 35 mm-equivalent focal length to pixels (`face3d/geometry/camera.py: focal_px_from_35mm`, `to_blender_camera`).
   - Export the solved camera per photo into Blender, with the photo as that camera's background image.
   - Evaluate the sculpt through the matched camera, not through an arbitrary viewport.
   - Whatever focal length practitioners recommend shooting with, the tool should *measure* the effective focal length of each supplied photo and flag disagreement between views.

3. **Build the checks that practitioner advice usually targets, as add-on operators, and validate them against the solver rather than against anecdote:**
   - **Silhouette overlay per matched camera.** Measure the sculpt's outline against a segmented photo mask, and report the mismatch area by region (forehead, cheek, jaw, chin, nose profile).
   - **Mirrored comparison.** Show a horizontally flipped render beside a flipped photo, so the user gets a fresh look at the comparison.
   - **Landmark reprojection report.** Give per-landmark pixel error in each photo, sorted worst-first.
   - **Measured asymmetry report.** Compare left and right landmark distances on the fitted mesh with those triangulated from the photos.

4. **Common failure modes to guard against.** These come from the engine design and are not practitioner-sourced:
   - **Sculpting with symmetry on.** This erases asymmetry that the photos actually show.
   - **Judging likeness in a perspective viewport whose focal length differs from the photo's.** The shapes cannot match even when the geometry is right.
   - **Mixing photos taken at very different distances or with different lenses.** One shape cannot satisfy all of them.
   - **Using expression-bearing photos as if they were neutral.**

5. **Next-session harvesting procedure.** For each named artist found, search their handle together with "likeness" and "process" on `instagram.com`, then cross-search the same advice on `youtube.com`, `polycount.com`, `blenderartists.org` and `reddit.com`. A tip counts as verified only when two independent artists or sources give it, and any numeric value must also be checked against an anthropometric or medical source in the library.

## Algorithmic implications

- **Provenance-weighted claim registry.** Store practitioner claims in a structured registry with these fields:
  - `source_kind` (social, forum, book, paper)
  - `n_independent_sources`
  - `medium`
  - `rule_type` (construction or diagnostic)
  - `numeric_value` and `units`
  - `status`

  Fitting code may read only entries with `status = verified` **and** a non-social corroborating source. Social-only claims may drive UI hints and diagnostics but must never act as priors in the energy function.
- **No canonical-proportion priors from this topic.** No proportion values were sourced here, so the fitter must not hard-code proportion targets on the strength of community lore. Shape priors should come from measured anthropometric data, which belongs in other library notes, and should be weak relative to the photo evidence.
- **Diagnostics as first-class outputs.** Return these from the solver:
  - per-view silhouette IoU or mismatch area
  - per-landmark reprojection residuals
  - estimated per-photo `f35`
  - a left/right asymmetry vector

  These are the measurable counterparts of the "check your likeness" advice sculptors share, and they let a user or a later study test whether a given practitioner tip actually lowers error.
- **Symmetry as a parameter, not a default constraint.** Expose a symmetry weight (0 means free, larger values push towards symmetric). Fit with low symmetry when the photos give good bilateral coverage, and raise it only to fill occluded regions.
- **Focal-length policy.** Estimate focal length per photo, and use EXIF only as an initial value. Warn when the estimates disagree strongly across views or point to a wide-angle near-distance capture. Thresholds are left unset until a source supplies them; see the open questions.
- **Experiment hook.** Because social-media tips arrive unverified, the engine should be able to A/B a tip as a diagnostic, for example comparing a mirrored-view check with no check in user studies, before any tip graduates into defaults.

## Disagreements, myths & refuted claims

- **No contradictions recorded.** Nothing was retrieved that could disagree with anything else.
- **Nothing refuted.** No claims were tested.
- **Methodological caution.** Platform posts are short, promotional and survivorship-biased: finished likenesses get posted and failed ones do not. Captions often leave out the method. Treat recurring advice as practitioner opinion until a forum thread, video demonstration or book corroborates it. This is a stated policy for the library, not a sourced finding.

## Open questions

- **Recurring advice from named portrait sculptors, clay and digital, on social platforms.** This is entirely unharvested. The harvester's unrun queries cover TikTok, X, Threads and an unrestricted query on reference photos and measurements. This pass's refused queries cover Faraut's clay portrait method, ZBrush likeness and focal-length distortion, and Reddit mirror and flip checks. All of them should be re-run with a fresh search budget.
- **Proportion grids.** Do social-media portrait instructors teach eye-line and midline proportion grids, and with what values? Do digital likeness artists endorse those grids or reject them for photo-based work?
- **Likeness checks.** Which checks recur across independent artists? Candidates to test, none confirmed here:
  - squinting or blurring
  - mirror and flip views
  - silhouette and profile comparison
  - matched-camera overlays
  - caliper measurements from a live sitter
- **Reference photography.** What focal length and distance do likeness sculptors recommend for reference photos, and how many views do they ask for? This directly sets add-on defaults (see the table above).
- **Reaching post content.** How can Instagram and TikTok post captions and reel transcripts be reached when web search returns only profile bios? Possible routes are artist-run YouTube mirrors of reels, ArtStation process write-ups and interviews. Direct fetching is blocked in this sandbox.
- **Engagement as a signal.** Do engagement metrics on Instagram or TikTok correlate with technical accuracy of the advice? This is probably not answerable from search alone.

## Sources

[1] Portrait Sculptors (@societyofportraitsculptors) Instagram profile — https://www.instagram.com/societyofportraitsculptors/ — social (Instagram profile; bio via search snippet) — n.d.
[2] Inese Veismane (@cooleblumen) Instagram profile — https://www.instagram.com/cooleblumen/ — social (Instagram profile; excluded as off-topic) — n.d.
[3] Character Sculpt (@charactersculpt) Instagram profile — https://www.instagram.com/charactersculpt/ — social (Instagram profile) — n.d.
[4] Sculptor Artists (@sculptor_artists) Instagram profile — https://www.instagram.com/sculptor_artists/ — social (Instagram profile) — n.d.
[5] CLAYSHAPER (@clayshaper) Instagram profile — https://www.instagram.com/Clayshaper/ — social (Instagram profile) — n.d.
