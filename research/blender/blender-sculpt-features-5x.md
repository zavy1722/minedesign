# Blender sculpt mode feature set (4.x-5.x)

> Sculpt mode in 4.x–5.x is a mature toolset that keeps topology intact: per-vertex masks, per-face face sets, auto-masking, Expand, mesh/cloth/mask filters, gesture tools, transform tools and Multires. Three tools rebuild topology (Dyntopo, voxel remesh, QuadriFlow) and must stay off the delivery mesh. Two changes since 4.0 dominate: brushes became assets in 4.3 (the Essentials library, the asset shelf, `brush.asset_activate`), which broke older brush scripts, tutorials and keymaps; and a C++ rewrite of the sculpt internals across roughly 4.2–4.4 made dense meshes much faster. The current releases are 5.3 (10 Nov 2026) and 5.2 LTS [1][2][3], and only a few 5.x sculpt changes are sourced (see Release context), so anything else dated after 4.3 is low-confidence and every brush name, hotkey and operator signature must be probed at runtime.
>
> Evidence status: 1 ✅ / 11 📄 / 49 🧠 / 7 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Release context**
- 5.3 is the current feature release, dated 10 Nov 2026 [1][2] ✅ (the exact date is 📄). 5.2 LTS came out on 14 Jul 2026 and is supported until Jul 2028 [3][4] 📄. 4.5 LTS is supported until Jul 2027 [5] 📄. 5.0 was released on 18 Nov 2025 [6][7] 📄.
- Sculpt features ship in feature releases; LTS lines get fixes 🧠. The 2026 plan was 5.1 (Mar), 5.2 LTS (Jul) and 5.3 (Nov) [10] 📄.
- 5.3 sculpt notes: Sculpt Mode now shows textures and colour attributes on Multires meshes (black in 5.2); Vertex and Weight Paint gain auto-masking; unified paint settings (size, strength, colour) are stored per brush instead of per scene [13] 📄.
- Since 5.0, `np.asarray()` on a mathutils Vector or Matrix returns a float32, non-contiguous view [8] 📄.

**Brushes as assets (4.3)**
- **Brushes are asset datablocks.** Defaults come from the bundled, read-only "Essentials" library. You pick them from an asset shelf with catalogs along the bottom of the viewport, or from its popup 🧠 (high confidence).
- **Edits stay in the file.** Editing an Essentials brush changes a local copy in the current .blend. "Save as Asset" or duplicating writes it to a user library, and "Revert" restores it 🧠.
- **One Brush tool.** The per-brush tools collapsed into a single Brush tool. Gesture, filter, Edit Face Set, Mask by Color and transform tools stay in the toolbar 🧠 (moderate).
- **Python changes:**
  - Brushes are activated with `bpy.ops.brush.asset_activate(asset_library_type, asset_library_identifier, relative_asset_identifier)`, with an identifier such as `brushes/essentials_brushes-mesh_sculpt.blend/Brush/Draw` [11][12] 📄.
  - `paint.brush_set` was removed in 4.3 and replaced by `brush.asset_activate` [12] 📄 (corrected in verification; the note's `paint.brush_select` and `tool_settings.sculpt.brush` claims are unconfirmed).
  - `Brush.sculpt_tool` → `sculpt_brush_type` happened in 5.0, not 4.3 [8] 📄 (corrected in verification).
  - Brush hotkeys are keymap items that call `brush.asset_activate`; right-click a brush in the shelf and choose "Assign Shortcut" 🧠.
- **Presets.** Essentials adds Crease, Grab, Pose/Boundary and Cloth variants whose names differ from older tutorials 🧠.
- **Plane brush.** A brush type that unifies Flatten, Fill and Scrape is reported for 4.5 or 5.0 ↔️ (low confidence).

**Masks, auto-masking, Expand**
- **Storage.** The mask is a per-vertex float from 0 to 1, where 1 means protected. It is stored in the hidden attribute `.sculpt_mask` (POINT, FLOAT) from about 4.1 🧠 (moderate). On Multires it lives in the grids 🧠.
- **Mask tools:** the Mask brush; Box, Lasso, Line and Polyline Mask; the A pie (invert, clear, smooth, sharpen, grow, shrink, contrast); Mask Filter; Mask by Color; Mask from Cavity (3.5); Random Mask (≈4.2); Mask Extract (a shell with thickness) and Mask Slice 🧠.
- **Auto-masking** works per brush or globally through the Alt+A pie (3.5). Its modes are Topology, Face Sets, Mesh Boundary, Face Set Boundary (with propagation steps), Cavity, View Normal (with occlusion) and Area Normal 🧠.
- **Expand** (2.93): Shift+A for masks and Shift+W for face sets. Falloff can be geodesic, topology, normals, sphere or boundary, with snapping to face sets 🧠.

**Face sets**
- **Storage.** A face set is a per-face integer in the hidden attribute `.sculpt_face_set` 🧠 (moderate). Its colour is a hash of the ID, seeded by `Mesh.face_sets_color_seed`; the ID in `face_sets_color_default` draws white 🧠.
- **Create:** draw them (Draw Face Sets brush; Box/Lasso/Line/Polyline Face Set), make them from the mask, visibility or an edit-mode selection, or initialise them by loose parts, materials, normals, UV seams, creases or sharp edges. **Edit:** Grow, Shrink, Delete Geometry, Fair Positions/Tangency 🧠.
- **Used by** visibility (H, Shift+H, Alt+H), auto-masking, Pose brush origins, the Relax Face Sets filter, Expand and the Cloth filter 🧠.
- **Hidden geometry** is stored in `.hide_vert` and `.hide_poly`, and brushes and filters skip it. Line and polyline hide and Grow/Shrink Visibility arrived in about 4.2 🧠 (moderate).

**Filters, gestures, deformers**
- **Mesh Filter:** Smooth, Scale, Inflate, Sphere, Random, Relax, Relax Face Sets, Surface Smooth, Sharpen, Enhance Details, Erase Displacement; on local, world or view axes; respects masks 🧠. **Cloth Filter:** Gravity, Inflate, Expand, Pinch, Scale 🧠.
- **Trim:** Box and Lasso (2.91), Line and Polyline (≈4.2); modes Difference, Union and Join 🧠.
- **Cloth brush:** eight deformation types (Drag, Push, Pinch Point, Pinch Perpendicular, Inflate, Grab, Expand, Snake Hook). Simulation area is Local, Global or Dynamic. Cost scales with the number of simulated vertices 🧠.
- **Pose brush:** origin from Topology, Face Sets or Face Sets FK, with IK segments. Use it for jaw opening, head tilt and ear angle 🧠.
- **Other deformers** 🧠:
  - Elastic Deform (Kelvinlets), with volume preservation;
  - the Boundary brush, for open edges such as lid margins and the mouth slit;
  - transform tools with an Elastic mode and a pivot at the mask border.

**Multires**
- **Operators:** Subdivide (Catmull-Clark, Simple or Linear), Unsubdivide, Rebuild Subdivisions, Delete Higher/Lower, Apply Base and Reshape 🧠.
- **Options:** Sculpt Base Mesh, Optimal Display, Quality (default 4), UV Smooth, Boundary Smooth, Use Creases and Use Custom Normals. The Displacement Eraser and Smear brushes work on its displacement 🧠.
- **Limits:** Python cannot write displacement; shape keys do not carry Multires detail; editing base topology corrupts higher levels 🧠. **Reshape** copies coordinates from an object whose topology matches the current level, which makes it the scriptable write path [14] 📄 (the manual and API confirm it copies vertex coordinates from another object with matching topology and indices; whether it acts only on the current level is unconfirmed).

**Topology-rebuilding tools**
- **Dyntopo:** detail modes Relative, Constant, Brush and Manual; Subdivide/Collapse refine; Detail Flood Fill; Symmetrize. It destroys vertex order, shape keys and clean UVs, and it cannot be combined with Multires 🧠.
- **Voxel remesh:** R sets the size and Ctrl+R remeshes. Voxel size is in object units and **defaults to 0.1** 🧠. Options are Adaptivity, Fix Poles, Preserve Volume, and keeping the mask, face sets and colour 🧠.
- **QuadriFlow:** gives quads, slowly 🧠.

**Performance and other**
- **Internals rewrite.** Around 4.2–4.4 the PBVH tree, brush loops and undo were rewritten in C++. Entering sculpt mode on dense meshes became several times faster, and memory use fell [12][15] 📄. Official figures for 4.3: entering sculpt mode about 5× faster (16M-face mesh, 11 s → 1.9 s), brush evaluation about 8× faster, memory about 30% lower (corrected in verification; the earlier 2–10× range is replaced by these figures).
- **Node tools** (4.0) run Geometry Nodes groups as sculpt-mode operators; selection = unmasked area 🧠 (moderate).
- **Shape keys:** strokes write into the active shape key 🧠.
- **Painting:** colour attributes since 3.2; sculpt-mode texture painting had not shipped as of the author's knowledge 🧠.

## Numbers & reference tables

**Table 1 — When features landed** (🧠 unless marked)

| Version | Sculpt items | Confidence |
|---|---|---|
| 2.81–2.93 | voxel remesh, QuadriFlow, Pose brush, filters (2.81); face sets, cloth (2.83); Multires rewrite (2.90); trim, Boundary (2.91); Expand (2.93) | moderate–high |
| 3.2 / 3.5 | colour painting / cavity, view-normal and area-normal auto-masking, Alt+A pie | moderate |
| 4.0 / 4.1 | node tools in sculpt mode / mask stored as `.sculpt_mask` | moderate / low |
| 4.2 LTS | line/polyline hide, mask, face-set and trim tools; random mask; refactor begins | moderate |
| 4.3 | brush assets, Essentials, asset shelf, `brush.asset_activate`, large speed-ups | high (assets) |
| 4.4–4.5 LTS | refactor continues; Plane brush type? | low ↔️ |
| 5.0–5.3 | `sculpt_tool`→`sculpt_brush_type` (5.0) [8]; mathutils→NumPy float32 view [8]; 5.3 items above [13] | 📄 / open |

**Table 2 — Resolution arithmetic** 🧠

Head + neck ≈ 0.14–0.18 m² (rule of nines: 9 % of 1.6–2.0 m²); face region ≈ 0.03–0.045 m²; faces ≈ A/v².

| Voxel size v | Head + neck faces | Face region | Use |
|---|---|---|---|
| 0.1 m (default) | collapses to a blob | — | never at real scale |
| 2 mm | 35k–45k | 8k–11k | block-out |
| 1 mm | 140k–180k | 30k–45k | primary forms |
| 0.5 mm | 0.56–0.72 M | 0.12–0.18 M | secondary forms (lid crease, alar groove, vermilion) |
| 0.25 mm | 2.2–2.9 M | 0.5–0.7 M | tertiary detail; better as maps |

Multires: faces = base × 4^L, edge = base edge ÷ 2^L.

| Level L | Faces (10k-quad base) | Edge (3 mm base) |
|---|---|---|
| 2 | 160k | 0.75 mm |
| 3 | 640k | 0.38 mm |
| 4 | 2.56 M | 0.19 mm |
| 5 | 10.2 M | 0.09 mm |

**Table 3 — Defaults to change for a real-scale head (1 unit = 1 m)** 🧠

| Setting | Default | Recommended |
|---|---|---|
| Remesh voxel size | 0.1 (object units) | 0.001–0.002 for block-out, 0.0003–0.0005 for detail |
| Viewport clip start | 0.01 m | 0.001 m (close-ups otherwise clip) |
| Brush radius | 50 px, view-relative | Radius Unit = Scene: 20–40 mm for grab, 3–8 mm for detail |
| Stroke spacing | 10 % | 5–10 % for creases |
| Dyntopo relative detail | 12 px | use constant detail or voxel instead |
| Undo steps | 32 | 32–64, with a memory limit if RAM < 32 GB |

**Table 4 — Default-keymap hotkeys** (4.3+; check Preferences ▸ Keymap) 🧠

| Action | Key | Confidence |
|---|---|---|
| Radius / strength / texture angle | F / Shift+F / Ctrl+F | high |
| Invert / temporary Smooth | hold Ctrl / hold Shift | high |
| Mask pie / clear / invert / box mask | A / Alt+M / Ctrl+I / B | moderate |
| Expand mask / face set | Shift+A / Shift+W | moderate |
| Face set under cursor: hide / isolate; reveal all | H / Shift+H; Alt+H | moderate |
| Auto-mask pie; stroke-method pie | Alt+A; E | moderate |
| Voxel size / remesh; Dyntopo / detail size | R / Ctrl+R; Ctrl+D / Shift+D | moderate |
| Multires sculpt level | PageUp / PageDown | moderate |
| Brush keys (Draw, Smooth, Grab, Snake Hook, Mask, Layer, Inflate, Clay Strips) | X S G K M L I C | low ↔️ (remapped in 4.3) |

**Table 5 — Data names to probe** 🧠

| Data | Name | Domain / type |
|---|---|---|
| Mask | `.sculpt_mask` | POINT / FLOAT |
| Face sets | `.sculpt_face_set` | FACE / INT |
| Hidden | `.hide_vert`, `.hide_edge`, `.hide_poly` | BOOLEAN |
| Remesh | `Mesh.remesh_voxel_size`, `remesh_voxel_adaptivity` | float |
| Symmetry | `Mesh.use_mirror_x/y/z` | bool |
| Brush type | `sculpt_brush_type` (5.0+) / `sculpt_tool` (≤4.5) (corrected in verification) | enum |

**Table 6 — Practical budgets** ↔️ (32–64 GB desktop; hardware-dependent)

| Workflow | Comfortable | Upper practical |
|---|---|---|
| Plain mesh (4.3+) / Multires total | 1–5 M / 2–10 M faces | 10–30 M / 20–40 M |
| Dyntopo | 0.2–1 M | 2–3 M |

## Applying this to photo→3D face sculpting in Blender

1. **Prepare the object.** Metric units, scale 1.0, midsagittal plane on local X = 0, rotation and scale applied: symmetry, filter axes, voxel size and scene-unit radii all work in local space 🧠. Viewport clip start 1 mm.
2. **Freeze topology and sculpt into shape keys.** The engine writes a "likeness" key. The artist sculpts on a second, active "artist" key, so both can be dialled and diffed. Ban Dyntopo, remesh, Decimate and merge-Symmetrize on this object (`blender-face-addons.md`).
3. **Match the photos in sculpt mode.** Look through each solved camera (Numpad 0) with the photo at 30–50 % opacity. **Turn off "Lock Camera to View"**, or the first orbit moves the solved camera 🧠. Fix silhouettes with Grab, Elastic Grab or Snake Hook at 20–40 mm, then recheck every other camera. A fix that helps one view and hurts another is a depth error (`reference-camera-setup.md`).
4. **Use the engine's face sets.** Isolate regions with Shift+H. Face Set Boundary auto-masking keeps lip, lid and nostril edges crisp under smoothing; Topology auto-masking lets you move the upper lid without dragging the lower one. Use the Pose brush with a Face Sets origin for jaw angle, chin projection and ear flare, and Relax Face Sets on region seams.
5. **Relax after big moves.** Use the Relax mesh filter. Protect the eye openings and mouth slit with Mesh Boundary auto-masking, and never smooth across them.
6. **Mirror only for block-out.** Real faces differ by about 0.8 mm RMS, bilateral landmarks by 0.6–4.6 mm, and people notice about 2–4 mm (`anatomy/facial-asymmetry.md`). Turn symmetry off for likeness passes.
7. **Add detail last.** Add Multires only once identity is final. Use L2–3 for secondary forms and L4–5 for wrinkles; pores go into displacement or normal maps. For late proportion fixes, use Sculpt Base Mesh rather than dropping to level 0.
8. **Explore on a separate object.** Remesh or Dyntopo concepts (ears, neck) live on their own object and are projected back with Shrinkwrap or Data Transfer.
9. **What goes wrong** 🧠: the default voxel size wipes out the head; a hidden face set or leftover partial mask silently weakens strokes; Essentials edits are lost, or a shared .blend points at a brush library the recipient lacks; pre-4.3 tutorials name tools that no longer exist; Python writes made in sculpt mode are overwritten; base topology is edited under Multires; Windows Ink/Wintab mismatch kills pressure.

## Algorithmic implications

- **Topology contract.** The engine owns vertex order and outputs shape keys "likeness" and "artist" plus a JSON sidecar. A refit treats "artist" − "likeness" as intent and never overwrites it.
- **Face-set schema.** Write fixed integer region IDs to `.sculpt_face_set` in object mode: 1 = default skin, then forehead, orbit L/R, nose, upper and lower lip, cheek L/R, chin, ears, and so on. Aim for about 15–25 regions matching the planes in `community/art-anatomy-books.md`, and give `face_sets_color_seed` a fixed value.
- **Masks as constraints.** Read the mask m ∈ [0,1] from `.sculpt_mask`. Multiply the data and landmark weights by (1 − m), and add a pin term m·‖x − x_artist‖²/σ_pin² with σ_pin ≈ 0.1–0.3 mm. Feather any mask the engine writes with a Gaussian of σ ≈ 1.5–2.5 mm (2–4 edge rings) so no ridge forms at its edge 🧠.
- **Smoothing prior.** Reproduce Relax and Surface Smooth with an HC or cotangent Laplacian term, σ_lap ≈ 0.05–0.1 × the local mean edge length. Leave open boundaries out.
- **Symmetry prior.** Store a mirror map and apply it as a soft prior, never as hard mirroring: σ_sym ≈ 1–2 mm laterally, ≈ 0.5 mm along the upper-face midline.
- **Resolution defaults.** Fit on a base of 5k–25k vertices (edges ≈ 2–4 mm) and hand Multires L2–L4 to the artist. Concept voxels are 1–1.5 mm for block-out and 0.3–0.5 mm for detail.
- **Multires write path.** Subdivide a copy of the base with identical settings, set its coordinates with `foreach_set`, and call `object.multires_reshape` with the copy as the source. Then verify the vertex correspondence 🧠 (moderate).
- **Mode discipline.** Switch to OBJECT mode, write with `foreach_set` (shape keys: `data.foreach_set("co")`), call `mesh.update()`, and restore the mode. Wrap all of it in one `bl_options={'REGISTER','UNDO'}` operator.
- **Queries.** Use `mathutils.bvhtree`/`kdtree` (SciPy is not bundled) and cast results to float64 [8].
- **Probe features, not versions:** `hasattr(bpy.ops.brush, "asset_activate")`, `"sculpt_brush_type" in bpy.types.Brush.bl_rna.properties`, the attribute names after a test mask fill, and whether `sculpt.mesh_filter` runs without a modal event.
- **Shipped brushes.** Ship a .blend of Radius-Unit-Scene brushes ("Likeness Grab 30 mm", "Lid Crease 3 mm"), activated by append plus `brush.asset_activate`; never edit the user's asset-library preferences without consent 🧠.

## Disagreements, myths & open questions

- **"Dyntopo is the modern way to sculpt faces."** ↔️ Fine for concepts, but triangles and lost vertex order rule it out for template-driven likeness; the norm is remesh or a fixed template, plus Multires 🧠.
- **"Multires is deprecated."** No: it is still the only non-destructive level-based detail system 🧠.
- **"Blender now matches ZBrush on polycount."** ↔️ Closer, but ZBrush's ceiling (HD Geometry, tens of millions per SubTool) is higher 🧠.
- **"Use the cloth brush for skin wrinkles."** ↔️ It works for neck and eyelid folds but is slow and non-deterministic. Crease, Draw Sharp and Layer give more control 🧠.
- **"Brush assets broke old files."** Old brushes survive and can be marked as assets; scripts and keymaps break 🧠.
- **Open questions:** (1) sculpt items in 5.0–5.3 (Plane brush, new filters); (2) are `.sculpt_mask`/`.sculpt_face_set` still the names in 5.3; (3) did `brush.asset_activate` change in 5.x; (4) can extensions register asset libraries; (5) any Python access to Multires displacement; (6) unified paint settings: 5.3 stores them per brush, not per scene [13] (answered; per-mode was wrong).

## Sources

[1] Blender Release Notes — Blender Developer Documentation (index) — https://developer.blender.org/docs/release_notes/ — official-docs — n.d.
[2] Cameras — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/render/cameras.html — official-docs — 2026 (from the reference-camera-setup harvest; supports only "the latest manual is 5.3")
[3] 5.2 LTS — Blender — https://www.blender.org/download/releases/5-2/ — official-docs — 2026
[4] Blender 5.2 LTS — Blender — https://www.blender.org/releases/5-2/ — official-docs — 2026
[5] Release Notes — Blender (index) — https://www.blender.org/download/releases/ — official-docs — n.d.
[6] Blender 5.0 — Blender — https://www.blender.org/releases/5-0/ — official-docs — 2025
[7] Blender 5.0 Release Notes — https://developer.blender.org/docs/release_notes/5.0/ — official-docs — 2025
[8] Blender 5.0: Python API — https://developer.blender.org/docs/release_notes/5.0/python_api/ — official-docs — 2025
[9] Index – Blender Developer Documentation (compatibility) — https://developer.blender.org/docs/release_notes/compatibility/ — official-docs — n.d. (lists breaking API changes; no sculpt facts extracted)
[10] Projects to Look Forward to in 2026 — Blender — https://www.blender.org/development/projects-to-look-forward-to-in-2026/ — official-docs — 2026
[11] Brush Operators — Blender Python API — https://docs.blender.org/api/current/bpy.ops.brush.html — official-docs — 2026
[12] Blender 4.3: Sculpt, Paint, Texture — https://developer.blender.org/docs/release_notes/4.3/sculpt/ — official-docs — 2024
[13] Blender 5.3: Sculpt, Paint, Texture — https://developer.blender.org/docs/release_notes/5.3/sculpt/ — official-docs — 2026
[14] Multiresolution Modifier — Blender 5.3 Manual — https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/multiresolution.html — official-docs — 2026
[15] This Summer's Sculpt Mode Refactor — Blender Developers Blog — https://code.blender.org/2024/11/this-summers-sculpt-mode-refactor/ — official-docs — 2024

[1] and [3]–[10] come from the blender-version-status-2026 harvest; this topic has no harvest, so no sculpt-feature fact is sourced.

**Further reading (by name, not yet linked)**
- Blender Manual: the Sculpt Mode chapter and the Multiresolution modifier page
- Blender 4.2–4.5 release notes: "Sculpt, Paint, Texture", and "Brush Assets" (4.3)
- Blender Python API reference: `bpy.ops.sculpt`, `bpy.ops.brush`, `bpy.types.Brush`, `mathutils.bvhtree`, `mathutils.kdtree`
- de Goes & James, "Regularized Kelvinlets", SIGGRAPH 2017 (basis of Elastic Deform)
- Vollmer, Mencl & Müller, "Improved Laplacian Smoothing of Noisy Surface Meshes", 1999 (HC smoothing)
- Huang et al., "QuadriFlow", SGP 2018

## Verification log (2026-11-20)

- Brush assets / `brush.asset_activate`: confirmed (📄). Corrected: `paint.brush_set` was removed in 4.3 [12]; `Brush.sculpt_tool` → `sculpt_brush_type` is a 5.0 change, not 4.3 [8]. `paint.brush_select` / `tool_settings.sculpt.brush` claim: unconfirmed. Sources: https://docs.blender.org/api/current/bpy.ops.brush.html , https://developer.blender.org/docs/release_notes/4.3/sculpt/ , https://developer.blender.org/docs/release_notes/5.0/python_api/
- `.sculpt_mask` / `.sculpt_face_set` names, `.hide_vert`/`.hide_poly`: unconfirmed (no release note names them; only the 5.4 sculpt notes mention the mesh `.sculpt_mask` value). Sources seen: https://developer.blender.org/docs/release_notes/5.4/sculpt/
- 5.x sculpt changes: partly confirmed. 5.3 notes sourced (Multires texture display, paint auto-masking, per-brush unified paint settings; the "per mode" guess was corrected to per brush). Plane brush type: unconfirmed. Source: https://developer.blender.org/docs/release_notes/5.3/sculpt/
- Voxel size default 0.1 and clip start 0.01 m: unconfirmed (manual Remesh page found but the search text did not state the default). Source seen: https://docs.blender.org/manual/en/latest/sculpt_paint/sculpting/tool_settings/remesh.html

## Verification log, pass 2 (2026-11-20)

- Multires Reshape copies vertex coordinates from another object with matching topology/indices: confirmed (📄); the "current level" part is unconfirmed. Sources: https://docs.blender.org/manual/en/latest/modeling/modifiers/generate/multiresolution.html
- C++ refactor speed-ups: corrected. 4.3 notes: sculpt-mode entry about 5x faster (11 s to 1.9 s, 16M faces); blog: brush evaluation about 8x, memory about 30% lower. The 2-10x range is replaced by these figures. Sources: https://developer.blender.org/docs/release_notes/4.3/sculpt/ , https://code.blender.org/2024/11/this-summers-sculpt-mode-refactor/
