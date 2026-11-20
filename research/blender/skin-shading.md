# Realistic skin shading in Blender

> In current Blender, skin shading is controlled on the Principled BSDF. The relevant inputs are Subsurface Weight, Radius, Scale and Method, plus Subsurface IOR and Subsurface Anisotropy, which only Cycles uses. The manual quotes a measured skin anisotropy of 0.8. The skin-specific **Random Walk (Skin)** method only works in Cycles. According to the developer pull request, its surface entry mixes Lambertian diffuse transmission with GGX refraction at a fixed roughness of 1, because a pure random walk lets light travel too deep into skin. Random walk scatters light through the volume of the mesh, so the head needs closed, non-overlapping geometry at real-world scale. That is a hard requirement on any mesh a photo-fitting pipeline produces. **Verification status:** the independent cross-check could not run because the shared web-search budget ran out before the first query. Every claim below rests on one harvested source. Measured skin optics, EEVEE Next behaviour, roughness, specular and displacement maps, and texture resources are still not covered.

## Key facts

- **Subsurface Radius is a distance, set separately for each colour channel.** It is the average distance light scatters below the surface. Red can be set to scatter deeper than blue [1]. ⚠️
- **Subsurface Scale multiplies the radius.** A search snippet of the current manual gives the slider range as 0–50 cm. This was not checked against the full page text [1]. ⚠️
- **Subsurface Anisotropy: 0 means light scatters equally in all directions.** The manual uses skin as its example and says skin has been measured at **0.8**. The original measurement paper was not traced in this run [1]. ⚠️
- **Subsurface IOR only works in Cycles.** It applies to rays entering the subsurface part of the shader and can differ from the main IOR. The manual suggests this as a way to imitate the layers of skin [1]. ⚠️
- **Main IOR:** the manual says most materials fall between 1.0 (vacuum or air) and 4.0 (germanium). The default of 1.5 approximates glass, not skin [1]. ⚠️
- **Random Walk (Skin) only works in Cycles and is tuned for skin.** A snippet of the manual says its radius is adjusted automatically from the colour texture [2]. A forum post says it lacks the Burley-matching scaling that the legacy random walk applies [7]. These two statements may describe different things and could not be reconciled. ↔️
- **How Random Walk (Skin) enters the surface:** at each entry it randomly chooses between Lambertian diffuse transmission and GGX refraction with roughness fixed at **1**. Diffuse is mixed in because a pure random walk goes too deep into skin [5]. Forum users say the same thing in practical terms: results look like the older random walk, but you lose control of the entry roughness [10][6]. ⚠️ (primary source, echoed by users)
- **Random Walk needs clean, closed meshes.** It scatters light through the actual volume inside the mesh. Overlapping faces, holes and open meshes cause errors, and closed meshes work best [2]. ⚠️
- **Thin-wall mode turns off the scattering controls.** Subsurface Radius, Scale and Method have no effect in it [1]. ⚠️
- **Specular Anisotropy only works in Cycles.** Positive values stretch highlights along the tangent and negative values stretch them across it [1]. No harvested source says skin needs anisotropic specular. ⚠️
- **Input and method names change between versions.** The 3.6 manual uses older names such as "Subsurface Anisotropy" and "Anisotropic", and describes random-walk modes whose radius depends on colour [4][11]. A forum post says Blender 5.2 splits random walk into legacy and newer variants [7]. That does not match the 5.3 manual excerpt and is not confirmed in official docs. ↔️
- **Users report artifacts.** SSS can produce flat-shaded artifacts on some meshes [8]. Users also disagree on what matters most. One says zero-anisotropy random walk looks fake because it lacks a "thin film" of surface detail [7]. Another says radius and colour matter more than anisotropy for a close match [6]. ⚠️ (user opinion)

## Numbers & reference tables

All values come from Blender documentation or developer notes. None of them is a measured human-skin dataset: this run found no primary skin-optics measurements.

| Parameter | Value / range | Units | Engine | Population / basis | Source | Status |
|---|---|---|---|---|---|---|
| Subsurface Anisotropy, skin | 0.8 | dimensionless | Cycles | "Skin has been measured" according to the manual; study and sample size not given | [1] | ⚠️ |
| Subsurface Anisotropy, isotropic | 0 | dimensionless | Cycles | Definition | [1] | ⚠️ |
| Subsurface Scale slider range | 0–50 | cm | Cycles/EEVEE (not separated) | UI range, from a search snippet | [1] | ⚠️ |
| Main IOR, typical span of materials | 1.0–4.0 | dimensionless | both | 1.0 = vacuum/air, 4.0 = germanium | [1] | ⚠️ |
| Main IOR, default | 1.5 | dimensionless | both | Approximates glass | [1] | ⚠️ |
| Random Walk (Skin) entry-refraction roughness | 1 (fixed) | GGX roughness | Cycles | Implementation detail | [5] | ⚠️ |

Arithmetic, not a sourced claim: at normal incidence the Fresnel reflectance is F0 = ((n−1)/(n+1))². For the default n = 1.5 that gives F0 = 0.04. Changing the IOR therefore changes the strength of the specular highlight at head-on angles. Do not take a skin IOR from this note: none was sourced in this run.

## Applying this to photo→3D face sculpting in Blender

1. **Work at real-world scale.** The radius is a scattering distance multiplied by Scale [1]. A head fitted in normalized units (for example an inter-ocular distance of 1.0) will look like wax or plastic with any physically chosen radius. Apply scale before shading. The fitting engine should output metres. Check the head's width in the Blender viewport against a plausible real head width before tuning anything.
2. **Close the mesh before rendering with random walk** [2]:
   - Cap the neck cut. An open neck is a hole that random walk handles badly.
   - Make sure the mouth bag, nostrils and ear canals are closed, manifold surfaces.
   - Remove duplicated or overlapping shells left by retopology or shrinkwrap.
   - Keep the eyeballs, teeth and tongue as separate objects with their own materials, so their surfaces do not overlap the skin volume.
   Run a non-manifold edge check (Select → All by Trait → Non Manifold) as a pre-render gate.
3. **Never enable thin-wall on the head.** It silently turns off radius, scale and method [1].
4. **Do lookdev in Cycles.** Subsurface IOR, Subsurface Anisotropy, Specular Anisotropy and Random Walk (Skin) are all Cycles-only [1][2]. Changing them in EEVEE has no visible effect, which leads to settings that "look right" in one engine and wrong in the other. How EEVEE Next approximates SSS was **not** covered by this run (see Open questions).
5. **Choose the method deliberately.**
   - Random Walk (Skin) suits skin: it blends diffuse transmission into the entry, which limits how deep light travels [5].
   - Its entry roughness is fixed, so if you need to control the surface roughness of the scattering entry, users say the plain or legacy random walk keeps that control [10][6].
   - Because method names differ between versions, record the exact Blender version in every preset [4][7].
6. **Things that commonly look fake (user reports, weak evidence):**
   - Zero anisotropy with random walk lacks surface definition [7].
   - A wrong radius or colour hurts realism more than anisotropy does [6].
   - Faceted, flat-shaded SSS on some meshes [8]. Check smooth shading, normals and topology first. The thread's diagnosis was not captured.
7. **Not covered by evidence in this run:** roughness and specular map values by facial region, pore displacement amplitude, microdetail workflow, and texture vendors. Do not hard-code values for these from this note.

## Algorithmic implications

- **The add-on should write materials by version.** Detect `bpy.app.version`. Look up Principled inputs by identifier, with fallbacks for renamed sockets (3.6 names differ from 4.x/5.x [4][11]). Read the list of `subsurface_method` options at runtime instead of hard-coding enum strings, because names like legacy, fixed-radius and skin have shifted between versions [7]. Store the Blender version and engine in the preset.
- **Geometry gate before shading.** The fitting engine's output contract should include:
  - a watertight head (no boundary edges once the neck cap is added)
  - no self-intersections or overlapping faces
  - separate closed shells for eyes, teeth and tongue
  This follows directly from how random walk behaves on open or overlapping meshes [2]. Score violations as a hard constraint, not a soft penalty.
- **Metric scale prior.** Because Radius × Scale is a physical distance [1], the solver should end in metres. Convert to scene units only through `unit_settings.scale_length`, never by rescaling the mesh.
- **Shading parameter schema** (defaults marked TBD are deliberately left unset until sourced):
  - `ss_method`: Random Walk (Skin) when the engine is Cycles [2][5]
  - `ss_anisotropy`: 0.8, labelled "manual-cited" [1]
  - `ss_ior`: TBD, kept separate from `ior` [1]
  - `ior`: TBD (the default 1.5 is glass [1])
  - `ss_radius_rgb`: TBD, ordered R ≥ G ≥ B. The ordering follows the manual's per-channel description [1]; the magnitudes have no source here.
  - `ss_scale`: TBD in metres, clamped to the 0–0.5 m UI range [1]
  - `spec_anisotropy`: 0 (design default; no source supports anisotropy for skin)
  - `thin_wall`: forced False [1]
- **Engine flag.** When the target is EEVEE, mark the Cycles-only inputs as ignored. Do not pretend they have an effect.
- **No priors for measured skin optics yet.** Region-specific roughness, specular, radius and displacement amplitude priors need primary measurements first (see Open questions). Until then, expose them as user parameters with no claimed physical default.

## Disagreements, myths & refuted claims

- **What Random Walk (Skin) does to the radius.** The manual snippet says the radius is adjusted automatically from the colour texture [2]. A forum post says the method lacks the Burley-matching scaling of the legacy random walk [7]. These may be compatible (colour-driven radius adjustment versus a Burley-equivalence rescale), but the full manual text was not read. ↔️
- **Version naming.** Harvest notes mention "Random Walk (Fixed Radius)" in a 3.4 page and "Random Walk (Legacy)" in a non-English 4.x page. A forum post claims 5.2 splits the modes into legacy and new [7]. None of this is confirmed against the 5.x English manual. ↔️
- **"Random walk costs more render time and noise in dense media like skin."** A forum post attributes this to the Blender docs, but it was not found in the retrieved docs pages. Treat it as unconfirmed.
- **Anisotropy versus radius and colour as the key realism lever.** The forum posts disagree [6][7]. Practitioner opinion only.
- **Refuted:** none. No claim could be tested against an independent source in this run, so nothing was confirmed or refuted.

## Open questions

- **Verification still owed.** Every fact above needs a second, independent source. A follow-up run with search budget should first check the 0.8 skin anisotropy (trace it to its measurement study and sample size), the 0–50 cm Scale range, the Random Walk (Skin) radius behaviour, and the details of PR #110989.
- **Default values in 4.x/5.x** for Subsurface Radius, Scale, IOR and Method were not captured. Read them from the full manual page.
- **EEVEE Next (4.2+):** does it support any random-walk SSS, which subsurface inputs does it honour, and what are its screen-space limits? Not covered.
- **Primary skin optics.** Measured scattering distances per channel (mm), skin IOR, specular roughness by facial region, and their population and sample sizes. Leads from background knowledge, **not retrieved or verified in this run** (check titles and contents before citing): Jensen et al., "A Practical Model for Subsurface Light Transport"; Donner & Jensen, "Light Diffusion in Multi-Layered Translucent Materials"; Weyrich et al., "Analysis of Human Faces using a Measurement-Based Skin Reflectance Model"; Christensen & Burley, "Approximate Reflectance Profiles for Efficient Subsurface Scattering".
- **Displacement microdetail.** Pore and wrinkle displacement amplitudes, multi-channel displacement workflows, and Cycles adaptive subdivision versus baked normal detail. Not covered.
- **Skin texture resources, licences and prices.** Not covered. Commercial scan-derived displacement vendors are an obvious lead but were not sourced.
- **Capturing albedo and specular from the user's own photos.** Cross-polarised versus parallel-polarised separation, and how it maps to Base Color and roughness. Not covered.
- **Cause of the flat-shaded SSS artifacts** [8]. Not captured.

## Sources

[1] Principled BSDF — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/principled.html — official-docs — 2026
[2] Principled BSDF — Blender 4.3 Manual — https://docs.blender.org/manual/en/4.3/render/shader_nodes/shader/principled.html — official-docs — 2024
[3] Subsurface Scattering — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/shader_nodes/shader/sss.html — official-docs — 2026 (harvested; no specific claim extracted)
[4] Subsurface Scattering — Blender 3.6 Manual — https://docs.blender.org/manual/en/3.6/render/shader_nodes/shader/sss.html — official-docs — 2023
[5] Cycles: Tweak Principled BSDF Subsurface parameters (PR #110989) — https://projects.blender.org/blender/blender/pulls/110989 — repo / developer notes — 2023
[6] Subsurface Scattering colour — Blender Artists — https://blenderartists.org/t/subsurface-scattering-colour/1502627 — forum (practitioner opinion) — year unknown
[7] Principled BSDF: Subsurface Anisotropy — Blender Artists — https://blenderartists.org/t/principled-bsdf-subsurface-anisotropy/1629688 — forum (practitioner opinion) — year unknown
[8] Subsurface Scattering is producing flat-shaded artifacts — Blender Artists — https://blenderartists.org/t/subsurface-scattering-is-producing-flat-shaded-artifacts/1594573 — forum — year unknown
[9] Volumetric SSS — Blender Tests — Blender Artists — https://blenderartists.org/t/volumetric-sss/1102733 — forum — year unknown (harvested; no specific claim extracted)
[10] This material? How to — Blender Artists — https://blenderartists.org/t/this-material-how-to/1233888 — forum (practitioner opinion) — year unknown
[11] Principled BSDF — Blender 3.6 Manual — https://docs.blender.org/manual/en/3.6/render/shader_nodes/shader/principled.html — official-docs — 2023 (URL cited in harvest facts)
