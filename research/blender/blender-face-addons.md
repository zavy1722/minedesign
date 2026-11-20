# Blender add-ons for heads and faces

> The Blender head/face add-on landscape splits into three layers that a photo→likeness pipeline must connect. The first is landmark capture: MediaPipe-based tools, where MediaPipe Face Mesh outputs 468 landmarks, or 478 with refinement. The second is parametric base humans: MPFB2/MakeHuman is the best-documented open option, with GPL-3-or-later code, CC0/CC-BY assets and distribution through Blender Extensions. The third is expression and rig tooling: Faceit is paid and generates ARKit-style shape keys, while CaptureForge and Face Shape Key Rig are GPL tools that convert to or drive ARKit-style keys. None of the tools in this evidence set is described as fitting a specific person's identity shape to photos, and that gap is what this project's fitting engine must fill. **Verification caveat:** this run's own cross-check searches could not execute because the shared web-search budget was used up, and GitHub API access to the third-party repos was not available. The badges below therefore reflect only the harvester's evidence. MB-Lab, CharMorph, Human Generator, the FLAME Blender add-on, Auto-Rig Pro and FaceBuilder have **no collected evidence** yet.

## Key facts

### Landmark capture (MediaPipe)
- MediaPipe Face Mesh estimates **468 3D face landmarks** per face in real time [3][2] ✅
- When refined landmarks are enabled, the output grows to **478 landmarks** per face. An attention-mesh model refines coordinates around the eyes and lips and adds iris landmarks [2]. ⚠️ The official legacy page [3] was not re-checked for the 478 figure in this run.
- No add-on literally named "FaceMesh Capture" was found. The closest match, `mozi1924/mediapipe-facecap-for-blender`, has two parts: an external **transmitter** program runs MediaPipe, and a Blender add-on (**receiver**) takes in the stream [1] ⚠️. Its licence, its Blender-version range and whether it outputs raw landmarks or only animation channels were not captured.
- Other MediaPipe face-mesh projects are listed under the GitHub topic `mediapipe-facemesh` [4]. None was reviewed individually. ⚠️

### Expression and rig layer
- **Faceit** is a paid add-on sold on Superhive (formerly Blender Market). It semi-automatically generates facial shape keys and ships presets for ARKit-style expressions, Audio2Face, tongue and phonemes. A **bake** step turns modifier-stack, pose and sculpt deformation into shape keys [5] ⚠️
- Faceit's listing states **Blender 3.0–5.2** compatibility [5] ⚠️. The price was not captured.
- **Face Shape Key Rig** is a free add-on under GPL on Blender Extensions. It builds in-viewport sliders and 2D pads, driven by bones and drivers, that animate **existing** shape keys, and it supports iFacialMocap capture and audio lipsync [6][7] ⚠️
- Face Shape Key Rig's GitHub page states that it **requires Blender 5.2 or newer** [7] ⚠️
- Face Shape Key Rig does **not** generate shape keys. Faceit is the comparable tool that creates them [6][5] ⚠️
- **CaptureForge** is a Blender extension suite under **GPL-3.0**. It converts a posed face rig into the **ARKit 52** blendshapes and drives them from video or webcam without an iPhone. It also lists a quality inspector and an auto face rig [8] ⚠️
- Leads whose content was not examined: wk FaceRig, a commercial add-on on Superhive [10], and a Faceit notes file inside the `met4citizen/TalkingHead` repository [9].

### Parametric base human (MPFB2 / MakeHuman)
- MPFB2 code is licensed **GPL v3 or later**, per the Blender Extensions listing and the repo's `LICENSE.CODE.md` [11][14] ✅. Both are primary documents controlled by the project.
- MPFB asset packs are **CC0 or CC-BY** according to the Extensions listing [11]. A third-party project's notes say MakeHuman base assets are **CC0 1.0** [16] ↔️
- Latest version **2.0.18**, compatible with **Blender 4.2 LTS and newer** [11][12] ⚠️. Both facts come from search-result snippets, not fetched pages. The release date "October 10, 2026" rests on a single snippet.
- The project's preferred install method is the Blender extension platform [13] ⚠️
- MPFB1 (`makehuman-plugin-for-blender`) is **deprecated** and replaced by MPFB2 [15] ⚠️

### Not covered (no evidence collected)
MB-Lab, CharMorph, Human Generator, the FLAME Blender add-on, Auto-Rig Pro and KeenTools FaceBuilder (along with alternatives to it). The **Open questions** section lists the exact fields to collect for each.

## Numbers & reference tables

**Table 1 — MediaPipe Face Mesh landmark counts** (model output specification; no population sample)

| Mode | Landmarks per face | Derived | Status | Source |
|---|---|---|---|---|
| Default | 468 | — | ✅ | [3][2] |
| Refined landmarks on | 478 | +10 vs default (478−468); iris added, eyes and lips refined | ⚠️ | [2] |

**Table 2 — Stated Blender version support** (Blender release numbers)

| Add-on | Add-on version | Blender min | Blender max stated | Status | Source |
|---|---|---|---|---|---|
| Faceit | not captured | 3.0 | 5.2 | ⚠️ | [5] |
| Face Shape Key Rig | not captured | 5.2 | open ("or newer") | ⚠️ | [7] |
| MPFB2 | 2.0.18 | 4.2 LTS | open ("and newer") | ⚠️ snippet only | [11][12] |
| CaptureForge | not captured | not captured | — | — | [8] |
| mediapipe-facecap-for-blender | not captured | not captured | — | — | [1] |

**Table 3 — Licence, cost and role**

| Tool | Code licence | Asset/model licence | Cost | Role | Generates shape keys | Source |
|---|---|---|---|---|---|---|
| MPFB2 | GPL-3.0-or-later ✅ | CC0 or CC-BY (listing) / CC0 1.0 (third-party note) ↔️ | not captured | parametric base human | n/a | [11][14][16] |
| Faceit | not captured | — | paid | expression shape-key generator + bake | yes | [5] |
| Face Shape Key Rig | GPL | — | free | slider/pad controller for existing keys | no | [6][7] |
| CaptureForge | GPL-3.0 | — | not captured | rig → ARKit 52 conversion, video/webcam drive | converts | [8] |
| mediapipe-facecap-for-blender | not captured | MediaPipe model terms not captured | not captured | live capture (transmitter + receiver) | not captured | [1] |

**Table 4 — Expression basis size**

| Basis | Count | Used by | Status | Source |
|---|---|---|---|---|
| ARKit blendshapes | 52 | CaptureForge target set; Faceit offers "ARKit-style" presets | ⚠️ | [8][5] |

## Applying this to photo→3D face sculpting in Blender

1. **Landmark input.** Run MediaPipe Face Mesh outside Blender, as the transmitter/receiver split in [1] does, and send landmarks into the add-on. This keeps MediaPipe's dependencies out of Blender's bundled Python. Turn on refined landmarks and **check the count per frame**: 468 means no iris or refined eye and lip points, and 478 means refined [2][3]. Never hard-code one count.
2. **Choosing a base mesh.** For an open-source tool, MPFB2 is the safest documented base among the tools checked: the code is GPL-3-or-later and the assets are CC0/CC-BY [11][14]. **Before shipping any derived mesh, check the licence of each asset**, because CC-BY assets need attribution and CC0 assets do not, and the sources disagree on which applies [11][16] ↔️. Ignore MPFB1 tutorials, since that plugin is deprecated [15].
3. **Keep the topology frozen through the likeness sculpt.** The expression add-ons downstream work on shape keys. Faceit generates and bakes them [5], CaptureForge converts a posed rig to the ARKit 52 set [8], and Face Shape Key Rig drives keys that already exist [6]. Shape keys require the same vertex count and order as the base, so do not use Remesh or Dyntopo on the head that will receive these keys. Sculpt directly on the fitted base mesh, or on a Multires level of it, and apply the result back to that base.
4. **Fit on a neutral expression.** Identity fitting from photos should target a neutral face. Leave expressions to the ARKit-style layer, and use Faceit's sculpt-to-shape-key bake [5] only after the likeness is locked.
5. **Check versions before you commit to a stack.** Face Shape Key Rig runs only on Blender 5.2+ [7]. Faceit states support up to 5.2 [5], and MPFB2 states 4.2 LTS+ [11]. The only overlap among all three is Blender 5.2. Test the user's Blender version at registration and warn if it is outside a dependency's stated range.
6. **What goes wrong**
   - *Name confusion.* A search for "FaceMesh Capture" finds a repo with a different name [1]. Check where a tool came from before you depend on it.
   - *Controller vs generator.* Face Shape Key Rig alone produces no expressions [6].
   - *Licence contamination.* FLAME's licence status is unverified, so never bundle FLAME data until it is checked (see Open questions).
   - *Snippet-only metadata.* The MPFB2 version and date [12] may be stale or wrong.

## Algorithmic implications

- **Landmark-scheme abstraction.** Model the input as `LandmarkSet{scheme ∈ {mp468, mp478}, xyz[N], visibility}`. Branch on `N` rather than on a flag, because 468 and 478 are both valid outputs [3][2]. Treat the 10 extra points (indices 468–477, derived from the counts) as optional eye and iris observations, and confirm the index ranges against [2][3] before relying on them.
- **Depth prior.** Until the MediaPipe coordinate convention is confirmed from [3], weight MediaPipe `z` well below `x,y` in the solver (default `w_z = 0.1·w_xy`, a design choice rather than a sourced value). Recover metric depth from multi-view PnP/triangulation, which already exist in `face3d/solve/`.
- **Correspondence table per base mesh.** Store a mapping from landmark index to vertex ID or barycentric point for each supported base mesh, starting with MPFB2. Version this table by the base mesh's version (e.g. MPFB2 2.0.18 [12]), because it breaks whenever the topology changes.
- **Licence as data.** Every prior, base mesh and asset should carry `{licence, attribution, commercial_ok}`. The export step should refuse to bundle assets with `commercial_ok=false` or with an unknown licence. This covers FLAME by default until its licence is checked.
- **Separate identity from expression.** Output a neutral identity mesh plus an optional set of ARKit-52-named shape keys, so the result works with Faceit, CaptureForge and Face Shape Key Rig [5][8][6]. Fit a small expression basis together with identity only to *absorb* expression in the input photos, then discard it.
- **Topology invariance as a hard constraint.** The solver may only move vertices, never add or remove them. Assert the vertex count and order before writing results back to the mesh.
- **Packaging defaults.** Release as a Blender extension with GPL-3.0-or-later code. This matches MPFB2 [14] and CaptureForge [8], which lets their code be reused. Declare a minimum of Blender 4.2, the same as MPFB2 [11], and gate features that rely on newer releases (5.2+ for Face Shape Key Rig interop [7]).

## Disagreements, myths & refuted claims

- **"MediaPipe gives 468 landmarks" vs "478"** — both are correct; the count depends on whether refinement is on [3][2].
- **MPFB/MakeHuman asset licence** ↔️: the Extensions listing says the asset packs are CC0 *or* CC-BY [11]. A third-party note says the base assets are CC0 1.0 [16]. The likeliest explanation is that the licence differs by asset (base mesh vs extra packs), but this has not been confirmed against MakeHuman's own licence files.
- **"Face Shape Key Rig is a Faceit alternative"**: only partly true. It controls existing keys and does not generate them [6][5].
- **"FaceMesh Capture" as an add-on name**: not confirmed. The closest project found has a different name and a two-part design [1].
- **Release date for MPFB2 2.0.18 (October 10, 2026)**: from one search snippet only. Treat it as unconfirmed.
- **Refuted:** none. No claim could be tested against an independent source in this run, so nothing was refuted. That is not the same as everything being confirmed.

## Open questions

Collect the following for each add-on still to check: code licence; model/asset licence; commercial use allowed; price; latest version and date; stated Blender min/max; whether it is on Blender Extensions; base-mesh vertex count; size and naming of the shape-key set; and whether it supports **photo-based identity fitting**.

1. **KeenTools FaceBuilder** and alternatives to it: licence, pricing, Blender 5.x status and output topology. This is the main competitor for photo→head, and nothing about it was collected.
2. **FLAME Blender add-on**: does the FLAME model licence (reported by its authors as research-only and non-commercial, unverified here) allow redistribution inside, or use by, a commercial or GPL add-on? Read the licence text itself.
3. **MB-Lab** and **CharMorph**: are they maintained in 2025–2026, do they run on Blender 4.2+/5.x, and under what licences are their code and base models released?
4. **Human Generator**: licence, price and Blender 5.x support.
5. **Auto-Rig Pro**: face-rig features, whether it exports ARKit-style keys, and Blender 5.x support.
6. **MediaPipe coordinates**: the convention and scale of `z`, and the exact iris index ranges, from the official docs [3].
7. **Faceit after 5.2**: is support listed for Blender releases newer than 5.2 [5]?
8. **mediapipe-facecap-for-blender** [1]: its licence, and whether the receiver exposes raw landmarks that a fitter could consume.

## Sources

[1] mozi1924/mediapipe-facecap-for-blender — https://github.com/mozi1924/mediapipe-facecap-for-blender — repo — n.d.
[2] MediaPipe Face Mesh: All 478 Landmark Points (DEV Community) — https://dev.to/metsander/mediapipe-face-mesh-all-478-landmark-points-5ec8 — blog — n.d.
[3] MediaPipe Face Mesh (legacy docs mirror) — https://mediapipe.readthedocs.io/en/latest/solutions/face_mesh.html — official docs — n.d.
[4] GitHub topic: mediapipe-facemesh — https://github.com/topics/mediapipe-facemesh — index — n.d.
[5] Faceit: Facial Expressions and Performance Capture (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d.
[6] Face Shape Key Rig (Blender Extensions) — https://extensions.blender.org/add-ons/face-shapekey-rig/ — official listing — n.d.
[7] Fragid/face-shapekey-rig — https://github.com/Fragid/face-shapekey-rig — repo — n.d.
[8] H0wZy/captureforge — https://github.com/H0wZy/captureforge — repo — n.d.
[9] TalkingHead blender/Faceit/FACEIT.md — https://github.com/met4citizen/TalkingHead/blob/main/blender/Faceit/FACEIT.md — repo doc — n.d.
[10] wk FaceRig (Superhive) — https://superhivemarket.com/products/wk-facerig — commercial listing — n.d.
[11] MPFB, Blender Extensions listing — https://extensions.blender.org/add-ons/mpfb/ — official listing — n.d.
[12] MPFB version history, Blender Extensions — https://extensions.blender.org/add-ons/mpfb/versions/ — official listing — 2026 (per one snippet)
[13] makehumancommunity/mpfb2 — https://github.com/makehumancommunity/mpfb2 — repo — n.d.
[14] mpfb2 LICENSE.CODE.md — https://github.com/makehumancommunity/mpfb2/blob/master/LICENSE.CODE.md — licence file — n.d.
[15] makehuman-plugin-for-blender (MPFB1, deprecated) — https://github.com/makehumancommunity/makehuman-plugin-for-blender — repo — n.d.
[16] kblood/CharacterCreator LICENSE-NOTES.md — https://github.com/kblood/CharacterCreator/blob/master/LICENSE-NOTES.md — third-party notes — n.d.
