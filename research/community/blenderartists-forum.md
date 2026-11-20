# BlenderArtists forum knowledge on faces

> BlenderArtists (a Discourse forum) holds the main announcement and support threads for KeenTools FaceBuilder, from the "KeenTools for Blender 2.8" beta thread through the 2021.1 "now with AI" release. It also has threads on single-photo generators (AutoFace, MetahumanModeler) and a steady run of beginner "model my own face from photos" questions. What this pass could extract is qualitative only. Neural auto-pinning is a starting point that still needs manual pin correction. Focal length and sensor size are estimated per photo, not assumed. Expressive photos are accepted, but neutral photos still give better results. **No accuracy figures, landmark counts or sample sizes were found, and nothing could be checked against an independent source.** The shared WebSearch budget ran out before any cross-check, and the one direct fetch of the forum failed (proxy 403). Every claim below therefore comes from a single search snippet and was not confirmed by opening the page. MPFB/MakeHuman, FLAME add-ons, likeness critiques and shared scripts were not searched at all.

## Key facts

- **FaceBuilder 2021.1 added automatic alignment.** "A couple of neural networks" find the face in each photo and place all the pins FaceBuilder needs. (Paraphrased from the search summary of the release thread, not a direct quote.) [1] ⚠️ single-source
- **The developers say the automatic pins are not always 100% accurate**, so pins sometimes have to be adjusted by hand. This is the vendor's own warning, not a user complaint. [1] ⚠️ single-source
- **The "Revamped FaceBuilder" thread says focal length and sensor size are set automatically for each photo**, which cuts manual camera setup. [2] ⚠️ single-source
- **FaceBuilder accepts photos with facial expressions**, so neutral photos are not strictly required, but neutral photos are still described as giving better quality. [1][2] ⚠️ single-source (two threads from the same vendor or community, so not independent)
- **Forum users call FaceBuilder a paid add-on, and one mentions a 30-day trial.** The current price, licence and trial terms were not checked against keentools.io. [1][4] ⚠️ single-source, unverified, and possibly out of date
- **MetahumanModeler**, a community add-on shared in "Released Add-ons and Extensions", reportedly builds a mesh with MetaHuman topology from a single image. Its author says it was built on their understanding of how FaceBuilder works. [5] ⚠️ single-source
- **AutoFace** is described as making a rigged, textured character from a single photograph. Only the thread title was seen, with no method or results. [6] ⚠️ title only
- **The question keeps coming back.** "Model human face from random photos", "Photo to 3D" and "Want to Create a 3D Model Face of Myself?" are recurring threads. Their answers were not retrieved. [7][8][9] ⚠️ title only
- **Thread order (inference).** Discourse numbers topics in the order they are created. By topic ID, the "Revamped FaceBuilder" thread (1245723) came *before* the 2021.1 thread (1294243). That conflicts with the harvester's wording of a "later revamp". [1][2] ↔️ contested (inferred from URLs, not from post dates)

## Numbers & reference tables

The forum material gave **no measurement, accuracy or performance numbers**. The two tables below are the only structured data this pass supports. No data JSON was written, because nothing here is a value a fitting program could use.

**Table 1 — Claims register (tool behaviour, version and licence)**

| Tool | Thread / version | Claim | Quantity | Status | Source |
|---|---|---|---|---|---|
| FaceBuilder | 2021.1 | Neural networks auto-detect the face and place pins | none | ⚠️ | [1] |
| FaceBuilder | 2021.1 | Auto pins are not always accurate, so manual fixes are needed | none | ⚠️ | [1] |
| FaceBuilder | "Revamped" thread | Focal length and sensor size auto-set per photo | none | ⚠️ | [2] |
| FaceBuilder | revamp / 2021.1 | Expressions supported; neutral photos still better | none | ⚠️ | [1][2] |
| FaceBuilder | n/a | Paid add-on with a trial | 30-day trial (user report) | ⚠️ unverified | [1][4] |
| MetahumanModeler | community add-on | One image → MetaHuman-topology mesh | none | ⚠️ | [5] |
| AutoFace | community | One photo → rigged, textured character | none | ⚠️ title only | [6] |

**Table 2 — Thread order by Discourse topic ID** (Discourse assigns IDs in creation order; the dates themselves were not retrieved, apart from the "2021" in thread [1]'s title)

| Order | Topic ID | Thread | Source |
|---|---|---|---|
| 1 | 1154237 | AutoFace — character from a single photograph | [6] |
| 2 | 1173005 | KeenTools For Blender 2.8 | [4] |
| 3 | 1210803 | The first-stable FaceBuilder release for Blender | [3] |
| 4 | 1211277 | Model human face from random photos | [7] |
| 5 | 1245723 | Revamped FaceBuilder for Blender | [2] |
| 6 | 1294243 | FaceBuilder for Blender 2021.1 — now with AI (2021) | [1] |
| 7 | 1313606 | Photo to 3D | [8] |
| 8 | 1531052 | Generating MetaHuman from a single image (MetahumanModeler) | [5] |
| 9 | 1606840 | Want to Create a 3D Model Face of Myself? | [9] |

## Applying this to photo→3D face sculpting in Blender

1. **Choose identity photos with a neutral expression.** Expressive photos are accepted, but the forum material says neutral photos fit better [1][2]. Keep smiling or talking shots for texture or for checking expressions later. Do not let them drive the base shape.
2. **Treat automatic pins as a first draft.** The vendor admits they are not always right [1]. Check every pin against its photo, then re-solve and check the result from all views before you start sculpting. Wrong pins usually show up as asymmetry, a shifted jaw or a misplaced ear, and the mistake then carries into every later sculpt pass.
3. **Check the camera estimate for each photo.** Focal length and sensor size are estimated per photo [2]. In general projective geometry, a wrong focal length trades off against subject distance. That changes how much the nose and mid-face appear to project and how wide the face appears, which hits likeness directly. (This is reasoning, not a forum statement.)
   - If several photos came from the same camera and zoom and their estimated focal lengths still disagree, lock them to one shared value.
   - If EXIF data survives, use it as a starting value. (This is our recommendation; it does not come from the forum.)
4. **Expect single-photo tools to guess depth.** With one view, nothing measures depth along the camera axis. Nose projection, chin and forehead slope, and cheekbone depth therefore come from the tool's statistical prior, not from the person. Use AutoFace or MetahumanModeler output [5][6] for blocking and clean topology. Add a profile photo, or sculpt depth by eye against reference, before judging likeness.
5. **Pick the target topology before you fit.** The demand for MetaHuman-topology output [5] shows that artists want the fitted shape in a production topology (MetaHuman, MPFB/MakeHuman, or their own). Retopologising afterwards loses some of the fit. Fitting directly onto the target mesh, or wrapping onto it, avoids that.
6. **Check licences before you distribute anything.** FaceBuilder is reported as paid [1][4]. This pass did not confirm its current price, trial terms, licence or the licence of meshes it exports.
7. **Common failure modes.** Beginner threads [7][8][9] were not read, so these are design expectations rather than forum findings:
   - mixing photos with different expressions and lighting into one shape solve;
   - trusting auto-pins on three-quarter and profile views without checking;
   - using a single photo and expecting it to fix the face's depth.

## Algorithmic implications

- **Use two levels of landmark trust.** The detector sets the starting pins, and each one carries a confidence weight. Once a user moves a pin, treat it as a high-weight or hard constraint. After every edit, re-solve only the parts affected, so a fix in one view updates the shared identity. This matches the "auto, then fix by hand" workflow the vendor itself describes [1].
- **Solve for the camera of each photo, but in pixel units.** Pixels can only measure the ratio of focal length to sensor size, not the two values separately. Solve one focal length in pixels per photo. Convert it to Blender's `Camera.lens` and `sensor_width` only when exporting. Fix sensor width to a convention, and do not optimise it as a free variable. For photos marked "same camera", share the focal value or pull them towards a common value. FaceBuilder sets both values per photo [2]. A cleaner tool should make the redundancy explicit.
- **Separate identity from expression.** One set of identity coefficients is shared across all photos. Each photo also gets its own expression coefficients, with a prior centred on zero. Photos the user marks "neutral" have their expression fixed at zero. In the identity solve, weight neutral photos more heavily, so expressive photos can be used without bending the identity [1][2].
- **Report confidence along the depth axis.** In single-view mode, raise the weight of the shape prior. Show the user which vertices are constrained by data and which come mostly from the prior. Default the UI to ask for at least one profile photo, because the single-photo tools in [5][6] rely entirely on the prior for depth.
- **Make output topology a plug-in.** Fit in the engine's own parametric space, then transfer the result to MetaHuman, MPFB or FLAME topology with fixed correspondences. Demand for MetaHuman output is documented [5]. MPFB and FLAME demand on this forum was not researched.
- **Defaults.** Auto-pin on, but require a review step before sculpting. Show the reprojection error for each pin. Flag any focal estimate that disagrees with EXIF or with photos from the same camera. Use a neutral-expression prior.

## Disagreements, myths & refuted claims

- **Myth: AI auto-pinning is one-click.** The vendor's own release thread says results are not always 100% accurate [1].
- **Myth: because expressions are supported, any photo will do.** The same material says neutral photos still give better quality [1][2].
- **Unresolved: can a single photo give a likeness?** AutoFace and MetahumanModeler claim single-image generation [5][6], but no accuracy evidence was found. On geometric grounds, depth from one view is driven by the prior.
- **Contested: the order of FaceBuilder versions.** The harvester called the revamp "later" than 2021.1. Topic IDs suggest the "Revamped FaceBuilder" thread (1245723) came before the 2021.1 thread (1294243). Post dates were not confirmed.
- **Unresolved: price and licence.** Users report a paid product with a 30-day trial [1][4]. No primary source was checked, so the current terms are unknown.
- **Refuted:** none. No claim could be tested against an independent source, so none could be refuted.

## Open questions

- How does FaceBuilder currently (2025–2026) price, license and version itself, and what is the licence on the meshes it exports? This needs a check against the primary keentools.io pages.
- Have the forum threads ever given a measured accuracy (millimetre error, landmark count, reprojection error) for FaceBuilder, AutoFace or MetahumanModeler?
- What does BlenderArtists say about **MPFB / MakeHuman** likeness workflows (adjusting targets to match photos), and about **FLAME-based** add-ons and their licence limits? Neither was searched.
- **Likeness critiques.** Which features do forum critics most often flag when a likeness fails (eye spacing, nose projection, mouth width, ear position)? This would give a data-driven list of what to check first.
- **Shared scripts.** Have users posted bpy scripts for camera matching, landmark import (for example from MediaPipe or dlib) or shape-key fitting that the engine could reuse or credit?
- What do the "Model human face from random photos" and "Want to Create a 3D Model Face of Myself?" threads actually recommend? Only their titles were seen.
- **Follow-up needed:** a new run with fresh search budget should rerun the three skipped harvester queries (MPFB, FLAME, FaceBuilder photo reference) and confirm the claims above against keentools.io and docs.blender.org.

## Sources

[1] FaceBuilder for Blender 2021.1 is out: now with AI — https://blenderartists.org/t/facebuilder-for-blender-2021-1-is-out-now-with-ai/1294243 — forum (vendor announcement thread) — 2021
[2] Revamped FaceBuilder for Blender — https://blenderartists.org/t/revamped-facebuilder-for-blender/1245723 — forum (vendor announcement thread) — n.d. (before [1] by topic ID)
[3] The first-stable FaceBuilder release for Blender — https://blenderartists.org/t/the-first-stable-facebuilder-release-for-blender/1210803 — forum — n.d.
[4] KeenTools For Blender 2.8 — https://blenderartists.org/t/keentools-for-blender-2-8/1173005 — forum — n.d.
[5] Generating metahuman based on a single image blender ue5 tutorial — https://blenderartists.org/t/generating-metahuman-based-on-a-single-image-blender-ue5-tutorial/1531052 — forum (Released Add-ons and Extensions) — n.d.
[6] AutoFace - Create Rigged and Textured Character from a Single Photograph — https://blenderartists.org/t/autoface-create-rigged-and-textured-character-from-a-single-photograph/1154237 — forum — n.d.
[7] Model human face from random photos — https://blenderartists.org/t/model-human-face-from-random-photos/1211277 — forum — n.d.
[8] Photo to 3D — https://blenderartists.org/t/photo-to-3d/1313606 — forum — n.d.
[9] Want to Create a 3D Model Face of Myself? — https://blenderartists.org/t/want-to-create-a-3d-model-face-of-myself/1606840 — forum — n.d.
