# Reddit: face-from-photos problems and answers

> **Status: unverified, research blocked. This note has no sourced facts.** Two attempts failed to get any Reddit material. First, the harvester's WebSearch calls restricted to `reddit.com` returned an API 400 error saying that reddit.com is not accessible to the search user agent. Second, the shared per-turn WebSearch budget (200 calls) ran out before the remaining harvest queries and before any verification. The verifier's one retry on 2026-11-20 also came back "budget used up". Per the project honesty rules, this note therefore states no community claims, tool rankings, numbers, versions, licences or quotes as facts. What remains is: (a) a record of the gap, (b) a list of hypotheses and candidate tool names from model background knowledge, clearly marked unverified, for the next harvest to confirm or reject, and (c) engineering implications that follow from camera geometry alone and do not depend on Reddit content.

## Key facts

- **No community fact about face-from-photos workflows was verified in this run.** Zero sources were retrieved, so no bullet here carries a citation marker or a ✅ / ⚠️ / ↔️ badge.
- **Process fact (tool log, not a web source):** WebSearch with `allowed_domains: ["reddit.com"]` returned HTTP 400 ("domain not accessible to the search user agent") during the harvest. Future Reddit harvesting cannot rely on domain-filtered search. Use unfiltered queries that contain "reddit" plus the subreddit name, or secondary sources that quote threads.
- **Process fact (tool log):** the 200-call per-turn WebSearch budget is shared by all agents in a workflow turn. It was used up before this topic ran, and nothing was worked around (no curl, no reader proxies), as the tool instructions require.

## Numbers & reference tables

No sourced numbers exist for this topic yet, so the data file `research/data/reddit-face-from-photos.json` was deliberately **not** written. The table below is a **collection schema**. It lists what the next harvest should look for. It contains no values.

| Quantity to harvest | Unit | Why a fitter or artist needs it | Acceptable source type |
|---|---|---|---|
| Recommended photo count for face photogrammetry (handheld, single camera) | images | Default for the add-on's capture checklist | Vendor docs; repeated practitioner reports |
| Recommended focal length / camera distance for likeness photos | mm (35 mm-equiv.), m | Perspective-distortion prior; focal initialisation in `solve_pnp` | Photography references; vendor docs |
| Number of reference views users actually have (front / 3/4 / profile) | views | Decides when the solver is under-constrained | Thread surveys |
| Reported likeness error after automated fit (if anyone measured it) | mm or % | Benchmark target | Papers; vendor benchmarks |
| Mesh density of exported heads from popular tools | vertices / faces | Retopology / sculpt-readiness expectations | Official docs |
| Price / licence of commonly recommended tools | USD, licence name | Recommendation table | Official pricing / licence pages only |

## Applying this to photo→3D face sculpting in Blender

Everything in this section comes from **first principles of camera geometry and photogrammetry. None of it comes from Reddit.** It is included because it does not depend on the failed harvest. Each item should still be cross-checked against sourced notes elsewhere in the library.

1. **Recover focal length before trusting the proportions.** A camera close to the face (typical for phone selfies) enlarges the parts nearest the lens (nose, central face) relative to the parts farther away (ears, jaw width). If you sculpt over a selfie as though it were an orthographic view, the head gets a nose that is too large and a face that is too narrow. Read the EXIF focal length when it exists (`focal_px_from_35mm` in `face3d/geometry/camera.py`). Otherwise estimate it jointly with pose (`solve_pnp` with free focal).
2. **Do not use orthographic image planes for anything but rough blocking.** The common Blender habit of front and side image planes assumes parallel projection. Prefer camera-matched backgrounds: export solved cameras with `to_blender_camera` so each photo lines up through a real perspective camera.
3. **Separate identity from expression and pose.** Smiles, squints and head tilt change the apparent shape. For the base sculpt, use neutral-expression photos. Treat expressive photos as low-weight or expression-only evidence.
4. **Treat hair, ears and jaw contour as unreliable.** Hair hides the true skull outline. Ears are often hidden or foreshortened. The silhouette of the jaw and cheek changes with lighting and focal length. Give these regions low confidence and fix them by hand in sculpt mode.
5. **Check symmetry deliberately.** Real faces are asymmetric. Mirror modifiers and symmetric sculpting erase the asymmetry, which is likely part of the likeness (a hypothesis to verify). Block in symmetrically, then turn symmetry off for the final likeness pass.
6. **Validate from the views you did not fit.** Leave out one photo, render the head through that photo's solved camera, and overlay the two. Agreement in a single view proves little.

## Algorithmic implications

These are design consequences for the `face3d` engine and the Blender add-on. They follow from the geometry above, not from community evidence.

- **Focal length is a first-class unknown.** Default: free focal, initialised from EXIF when present. Add a regulariser towards a plausible phone or DSLR range. Flag single-view fits with free focal as weakly constrained, because depth and focal length trade off against each other.
- **Per-landmark confidence weights.** Default weights should be high for internal features (eye corners, mouth corners, nose tip, alar base) and low for contour landmarks (jawline, ears, hairline). Contour points slide along the silhouette as the view changes, so they should not be fixed correspondences.
- **Per-view weights and robust losses.** Use Huber or Cauchy residuals in `levenberg_marquardt` so that one bad photo (motion blur, strong expression, wrong landmark) cannot pull the fit.
- **Explicit identity / expression / pose split** in the parameter vector. Shape updates should come only from views tagged neutral, unless the user overrides.
- **A symmetry prior, not a symmetry constraint.** Penalise left-right deviation softly, so measured asymmetry survives when several views support it.
- **Coarse-to-fine deformation.** First a similarity alignment (`umeyama`), then a low-dimensional shape fit, then an RBF warp (`RBFWarp`) driven by the landmarks the user pins. Never let the RBF stage move unpinned regions far from the prior.
- **Report uncertainty, not just a mesh.** Report per-region confidence (for example, the spread of triangulated points across views from `triangulate_points`). That way the artist knows where to sculpt by hand.
- **Held-out-view reprojection error as the built-in likeness check**, shown in pixels in the UI.

## Disagreements, myths & refuted claims

Nothing could be adjudicated, because there were no sources. The following **questions** are expected to be contentious in community discussions. They are hypotheses for the next harvest, not reported findings:

- Whether AI single-image-to-3D generators (e.g. tools searched under names such as Hunyuan3D, TRELLIS, Tripo, Meshy) give a recognisable likeness, or only a generic head that then needs full re-sculpting.
- Whether photogrammetry of a live person with one handheld camera works at all, given that the subject moves between shots, compared with multi-camera rigs.
- Whether photo-fitting add-ons (searched under names such as KeenTools FaceBuilder) or game-engine pipelines (e.g. MetaHuman's mesh-to-MetaHuman flow, Character Creator Headshot) are better than sculpting by eye over camera-matched references.
- Whether likeness depends more on proportions and landmark placement or on surface detail and textures.

Tool names above are **search terms only**. This run verified none of their existence, current names, versions, licences, prices or capabilities.

## Open questions

1. **Re-run the harvest with budget.** Use unfiltered queries such as `reddit r/blender face from photos likeness`, `reddit r/photogrammetry face scan phone`, `reddit r/ZBrush likeness sculpt tips`, `reddit r/3Dmodeling AI image to 3D head honest`, and `reddit r/computergraphics 3DMM single image face reconstruction`.
2. **Alternative community domains** if Reddit stays blocked: blenderartists.org, polycount.com, ZBrushCentral, artstation.com (likeness breakdowns), youtube.com (likeness sculpt tutorials), 80.lv interviews, and the KeenTools forum.
3. **Which failure modes come up most often** (perspective distortion, hair or ear occlusion, expression contamination, lighting baked into textures, uncanny-valley "almost likeness")? This question needs counted thread evidence, not anecdotes.
4. **Has any practitioner or paper measured likeness quantitatively** (mm surface error against a scan, or face-recognition similarity) for consumer photo-to-head tools?
5. **What photo sets do users actually have?** One selfie, a few casual photos, or a controlled multi-view set? This decides the add-on's default solver mode.
6. **Privacy and consent.** How do communities and tool terms of service treat building a head of someone else from their photos? This is relevant to the add-on's documentation.

## Sources

No sources were retrieved for this topic. Domain-filtered Reddit search was refused (HTTP 400), and the shared WebSearch budget was used up before the harvest and verification could run. No URLs are listed, so that none are invented. The matching `research/sources/reddit-face-from-photos.json` has an empty `sources` array.
