# Shape keys and blendshape standards

> Blender stores every shape key as an absolute copy of all vertex positions and, in relative mode, mixes them as Basis + Σ valueᵢ·maskᵢ·(keyᵢ − relative_keyᵢ) before any modifier runs, which makes keys the natural non-destructive container for a photo-fitted likeness, artist passes and an expression set on one frozen topology. The de facto expression vocabulary is Apple's ARKit 52 coefficients in [0, 1]; MediaPipe Face Landmarker emits 52 scores under the same camelCase names (minus `tongueOut`, plus `_neutral`), so a clone keyed with exact ARKit names can be driven and audited by phone or webcam capture. Linear deltas fail on arcs (eyelids, jaw) and on combinations, so a usable set adds in-betweens and product-driven correctives, and after an identity fit the template's deltas must be transferred, not copied. No harvest or earlier draft existed: 📄 facts come from sibling harvests in this library; everything else is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 14 📄 / 66 🧠 / 11 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Blender data model**
- Keys live on a `Key` ID datablock (`mesh.shape_keys`) holding `key_blocks`, `reference_key` (first key, "Basis"), `use_relative` and its own `animation_data`, so shape-key drivers and keyframes sit on the Key, not the object or mesh 🧠.
- Each `ShapeKey` stores absolute float32 coordinates for every vertex (12 bytes/vertex/key, never sparse), plus `value`, `slider_min`/`slider_max` (defaults 0/1, hard limits −10…10), `relative_key`, `vertex_group` (mask, by name), `mute` and `interpolation` (absolute mode only) 🧠. `lock_shape` arrived in 4.0 or 4.1 ↔️.
- Relative evaluation: X = X_ref + Σᵢ valueᵢ·wᵢ(v)·(Kᵢ − K_relᵢ); muted and zero-valued keys are skipped, so cost scales with *active* keys. Keys evaluate before the whole modifier stack 🧠.
- `obj.shape_key_add(name="Basis", from_mix=False)`: defaults are `name="Key"`, `from_mix=True`, so pass both. Fill with `kb.data.foreach_set("co", f32)` (or the optimised `kb.points` in recent versions), then `me.update()` 🧠.

**Editing semantics (where likeness work goes wrong)**
- Edit and Sculpt modes write into the **active** key. Interactive edits to the reference key propagate the same offset to dependent keys, preserving their deltas 🧠. A **Python write to Basis does not propagate**: dependents keep absolute positions, so each delta silently becomes (old delta − Δ) 🧠. The engine must add Δ to dependents itself.
- Sculpting into a key whose value ≠ 1, or while other keys are active, gives unpredictable strokes; pin it (`show_only_shape_key`) or solo it at 1 🧠.
- Apply is refused on meshes with keys; `object.modifier_apply_as_shapekey(keep_modifier=True)` captures a modifier result as a key 🧠. Multires detail and Dyntopo/Remesh output cannot live in keys (`blender-sculpt-features-5x.md`) 🧠.
- Operators 🧠: `shape_key_remove(all=True, apply_mix=True)` (apply all); `shape_key_mirror(use_topology=…)`; `shape_key_transfer` and `join_shapes` (same vertex count); `shape_key_move(type='TOP')` (makes a new reference); Edit-mode `mesh.blend_from_shape` and `mesh.shape_propagate_to_all`.
- Cross-topology transfer: bind **Surface Deform** on the target to the template at rest, set one template key to 1, `modifier_apply_as_shapekey(keep_modifier=True)`, loop 🧠.

**Drivers**
- `kb.driver_add("value")`; read keys with `SINGLE_PROP` variables (`id_type='KEY'`, `id=me.shape_keys`, `data_path='key_blocks["jawOpen"].value'`) and bones with `TRANSFORMS`/`ROTATION_DIFF` (Swing/Twist modes isolate a hinge angle). Use ID pointers, not names 🧠.
- **Simple expressions** (arithmetic, comparisons, conditionals, whitelisted `min`/`max`/`abs`/`clamp`…) run natively; anything else, or "Use Self", needs Python and fails while Auto Run Python Scripts is off, the default 🧠.

**ARKit 52**
- `blendShapes` are named coefficients from 0 (neutral) to 1 (maximum), updated live [1][3] 📄; the set is known as "ARKit 52" [11] 📄. The harvest could not confirm the full list; a forum list starts `jawOpen`, `eyeLookDown` [4] 📄.
- Names 🧠 (verify against [2]): 14 eye, 5 brow, 3 cheek, 2 nose, 4 jaw, 23 mouth, 1 tongue; full list and spellings in `data/shapekeys-blendshapes.json`.
- **Naming drift is the commonest interop bug** 🧠: Swift `eyeBlinkLeft`, Apple raw string `eyeBlink_L`, Live Link Face CSV `EyeBlinkLeft` (61 columns: 52 + 9 head/eye angles), MediaPipe `eyeBlinkLeft`. Normalise at the boundary.
- `mouthClose` = lips closing *while the jaw is open*: author it as (jawOpen with lips sealed) − jawOpen, never alone 🧠. `ARFaceGeometry` has 1,220 vertices, 2,304 triangles 🧠.

**MediaPipe**
- 478 landmarks plus 52 blendshape categories scored in [0, 1] [5][7] 📄; off unless `output_face_blendshapes=True` [6] 📄; left/right are the subject's, and a mirrored selfie swaps them [5] 📄.
- Categories: `_neutral` at index 0, then the 51 ARKit names minus `tongueOut`, alphabetical 🧠, so `key_blocks.get(cat.category_name)` maps directly 🧠.
- The blendshape head is a small network fed by landmarks (reportedly ≈146) 🧠: scores are not independent of the landmarks, so never use both as likelihood terms.
- Ranges are compressed and uncalibrated (`eyeBlink` often peaks well below 1; `cheekPuff`, `noseSneer` near 0) ↔️; per-subject remap is standard 🧠.

**FACS-based sets, correctives, in-betweens**
- ARKit/MediaPipe are FACS-inspired tracker outputs, not FACS intensities (`facs-expressions.md`) 🧠. Semantic bases are non-orthogonal, so inverse fits are ill-conditioned; PCA bases (FLAME, FaceWarehouse) are orthogonal but unreadable (Lewis et al. 2014) 🧠.
- Combination model: X = X₀ + Σ wₖDₖ + Σ wᵢwⱼDᵢⱼ + Σ wᵢwⱼwₗDᵢⱼₗ (Lewis et al. 2014) 🧠; `min(a,b)` is a common alternative ↔️.
- Blender has no native in-betweens (Maya and Unity do) 🧠. Emulate in-between I at w = 0.5 with two keys: I driven by `max(0,1-abs(2*w-1))`, full F by `max(0,2*w-1)` 🧠 (derived).
- Pose-space correctives must be stored in rest space: use the inverse deformation (the formerly bundled Corrective Shape Keys add-on) or sculpt through the armature, where crazyspace maps strokes back approximately 🧠.

**Add-ons and export** (time-sensitive)
- **Faceit** (paid) generates ARKit-style, Audio2Face, tongue and phoneme keys and bakes modifier/pose/sculpt deformation into keys; listing states Blender 3.0–5.2 [8] 📄.
- **Face Shape Key Rig** (free, GPL): viewport sliders and 2D pads, via bones and drivers, for *existing* keys; iFacialMocap and lipsync [9][10] 📄; requires 5.2+ [10] 📄.
- **CaptureForge** (GPL-3.0) converts a posed face rig to ARKit 52 and drives it from video or webcam [11] 📄; **mediapipe-facecap-for-blender** pairs a MediaPipe transmitter with a Blender receiver [12] 📄.
- FBX and Unity weights are 0–100; Unreal and glTF 0–1; glTF names targets in `mesh.extras.targetNames` 🧠. Do not trust exporters with `vertex_group` masks, non-Basis `relative_key`, drivers, or (FBX) keys under non-Armature modifiers: bake first ↔️.

## Numbers & reference tables

**Table 1. Blendshape standards** (counts time-sensitive)

| Standard | Count | Range | Naming; L/R | Badge |
|---|---|---|---|---|
| ARKit | 52 [11] | 0–1 [1] | camelCase; raw `_L/_R`; subject's side (wink-test); has `tongueOut` | 📄; names 🧠 |
| MediaPipe Face Landmarker | 52 incl. `_neutral` [5] | 0–1 [5][7] | ARKit camelCase; subject's side [5] | 📄; composition 🧠 |
| Live Link Face CSV | 52 + 9 angles | 0–1 | PascalCase | 🧠 |
| Meta Movement SDK | 63 (≈70 with tongue) | 0–1 | FACS-style UPPER_SNAKE | 🧠 ↔️ |
| VRM 1.0 / 0.x | 18 / 17 presets | 0–1 | happy, aa, blink… | 🧠 |
| Oculus visemes | 15 | 0–1 | sil PP FF TH DD kk CH SS nn RR aa E ih oh ou | 🧠 |
| FaceWarehouse | 47 (neutral + 46 FACS); 150 people | 0–1 | bilinear | 🧠 |
| FLAME 2020 | 100 expression PCA + 36 pose correctives; 5,023 verts | unbounded | non-semantic | 🧠 |
| ICT FaceKit | ≈53 FACS-like + 100 identity PCA (recalled) | 0–1 | ARKit-like | 🧠 |
| MetaHuman | ≈250 `CTRL_expressions_*` → joints + correctives | 0–1 | FACS-style | 🧠 |

**Table 2. Linear-delta error at w = 0.5** (derived, r·(1 − cos θ/2))

| Motion | r | Sweep θ | Mid-weight error | Failure | Badge |
|---|---|---|---|---|---|
| Upper lid over globe | 12–13 mm | 40–60° (≈49° for a 10 mm fissure) | 0.7–1.7 mm inward | lid cuts into cornea | 🧠 |
| Jaw (incisor/chin) | 100–120 mm | 15–30° | 0.9–4.1 mm toward condyle | chin shortens mid-open | 🧠 |

**Table 3. Plausibility bounds at weight 1** (adult; QA only, not norms)

| Key | Measure | Bound | Badge |
|---|---|---|---|
| eyeBlink | upper-lid travel; closure gap | 8–12 mm; 0–0.5 mm, never crossing | 🧠 |
| eyeWide / eyeSquint | upper-lid rise / lower-lid rise | 1–4 / 1–3 mm | 🧠 |
| browInnerUp, browOuterUp / browDown | brow rise / drop + medial | 5–12 / 3–8 mm | 🧠 |
| cheekSquint | malar lift | 2–5 mm | 🧠 |
| mouthSmile / mouthStretch | cheilion displacement | 7–15 / 3–8 mm | 🧠 |
| mouthPucker, mouthFunnel | lip protrusion | 6–12 mm | 🧠 |
| jawOpen | interincisal opening | 40–60 mm | 🧠 ↔️ |
| jawForward, jawLeft/Right | protrusion / lateral | 5–10 mm | 🧠 |
| cheekPuff / noseSneer | cheek outward / alar lift | 5–15 / 1–4 mm | 🧠 |

**Table 4. Corrective starter set** (all simple expressions; `jo` = jawOpen, `eb` = eyeBlink…)

| Shape | Driver | Purpose | Priority |
|---|---|---|---|
| mouthClose guard | `min(mc, jo)` | lips never cross when shut | high |
| jawOpen, eyeBlink L/R in-betweens | `max(0,1-abs(2*w-1))` | jaw and lid arcs | high |
| jawOpen × mouthSmile L/R | `jo*s` | open smile | high |
| jawOpen × mouthFunnel / mouthPucker | `jo*f` | "oh"/"oo" | medium |
| eyeBlink × eyeLookDown/Up; × eyeSquint/cheekSquint | `eb*ld` | lid follows gaze; lower-lid bunching | medium |
| browDown × browInnerUp | `bd*bi` | AU1+4 grief brow | medium |
| mouthSmile × cheekSquint | `s*cs` | AU6+12 infraorbital bulge | medium |

All rows 🧠.

## Applying this to photo→3D face sculpting in Blender

1. **Freeze topology, key everything.** Basis = template mean; `ID_fit` = engine output (`from_mix=False`); `artist` = sculpt layer. Set `ID_fit.slider_max = 1.5`: 1.1–1.3 exaggerates deviation from the mean, aiding recognisability (caricature effect, Rhodes et al. 1987), valid only if Basis is a mean face 🧠.
2. **Author expressions once, on the template**, with exact ARKit camelCase names (Faceit [8], CaptureForge [11], own sculpt, or deformation transfer from a licensed rig). Split L/R from a symmetric sculpt with masks summing to 1 across a 10–20 mm smoothstep midline band, so L + R reproduces it exactly. Characters face −Y, so subject's left = +X (Rigify `.L`) 🧠.
3. **Transfer deltas after the identity fit.** First pass: scale by s = IOD_subject/IOD_template and rotate into local frames; production: deformation transfer. Then re-fit lid closure and lip seal to the subject. Bake Basis_new = Basis + Δ_ID, each key = Basis_new + T(Δ_k), delete `ID_fit`. UI shortcut (naive copy): Edit Mode on Basis, select all, Blend from Shape `ID_fit` (add off), exit; verify on a copy 🧠.
4. **Check every key at 1 on the clone** 🧠: lid gap 0–0.5 mm with no crossing; lips sealed at jawOpen+mouthClose; no teeth/eyeball penetration; L/R mirror RMS ≤ 0.5 mm on the template; spill (displacement energy outside the region mask) ≤ 1–2 %; magnitudes within Table 3.
5. **Satellites:** teeth, tongue, lashes and caruncle get same-named keys driven by the face keys, or ride a jaw bone; hair follows via Deform Curves on Surface (`hair-blender.md`) 🧠.
6. **Expression-likeness test:** run MediaPipe on the subject's own expression photos [5][6], remap, set keys, render through the solved camera, compare landmarks. Good neutral but bad expressions means the deltas need personalising (example-based rigging) 🧠.
7. **Export:** bake masks, non-Basis relatives and drivers to plain keys; FBX (Unity 0–100, Unreal) or glTF with `targetNames`; keep vertex order.

**What goes wrong** 🧠: Python writes to Basis without propagation ("anti-applied" expressions); sculpting identity with an expression key active or into a key at 0.4; mirrored selfies swapping L/R [5]; un-remapped MediaPipe `eyeBlink` never closing lids; linear jaw/lid chords (Table 2); `mouthClose` fired alone; drivers dead because they need Python; Multires/Dyntopo/Remesh destroying keys; exporters dropping masked or relative-chained keys.

## Algorithmic implications

- **Structure:** `{names[K], D: K×V×3 float32, masks, lr_pairs, antagonists, combos[(idx…), D_c], inbetweens[(k, w, D_i)]}`; canonical names ARKit camelCase, with adapters for `_L/_R`, PascalCase and `_neutral` 🧠.
- **Forward model:** X(ψ) = X₀ + Σ ψₖDₖ + Σ_c (Π_{k∈c} ψₖ)·D_c (+ in-betweens); ∂X/∂ψₖ = Dₖ + Σ_{c∋k} (Π_{j∈c∖k} ψⱼ)·D_c. Precompute D only at landmark barycentrics (L×3×K): K = 51 (drop `tongueOut`) gives a dense 51×51 system per view 🧠.
- **Priors** (🧠 engineering defaults, consistent with `facs-expressions.md`, `expression-neutralization.md`):
  - ψ ∈ [0, 1] by projected Gauss–Newton or bounded LM.
  - Neutral views: half-normal σ = 0.07 (0.05–0.10) + L1 λ ≈ 0.01–0.05 on IOD-normalised residuals; expressive views σ = 0.5.
  - MediaPipe score as observation of ψ: σ = 0.15–0.25 calibrated, 0.3 uncalibrated; initialise or prior only, never a second data term beside landmarks.
  - Antagonist penalty λ_a·ψ_a·ψ_b (1–10× data scale) only for blink/wide and lookIn/lookOut on the same eye, jawLeft/Right, mouthLeft/Right.
  - Correctives are deterministic functions of ψ; keep them in the forward model so identity cannot absorb combination geometry.
  - Fit jaw rotation θ about the TMJ, not `jawOpen` deltas; neutral prior N(1.5°, 1°²).
- **Conditioning:** if cond(DᵀD) at the landmarks exceeds ≈10⁴, add ridge or solve in an orthogonalised basis and map back 🧠.
- **Transfer:** deformation transfer (Sumner & Popović 2004) = one sparse Poisson factorisation per subject + 52 back-substitutions; numpy-only fallback is Jacobi-preconditioned CG. First-pass scale s ∈ [0.86, 1.14] from adult IPD ≈54–72 mm vs a 63 mm template 🧠 (derived).
- **MediaPipe → rig remap** 🧠: w′ = clamp((w − lo)/(hi − lo), 0, 1)^γ; lo = 90th–95th percentile on neutral frames, hi = 95th–99th over a range-of-motion clip, γ = 1 (0.7–1.5); video: One Euro filter, min_cutoff ≈ 1 Hz, β ≈ 0.005–0.05.
- **Blender bridge** 🧠: float32 `foreach_set`; explicit `relative_key`; drivers with ID pointers and simple expressions; propagate Δ on every Basis write; respect `getattr(kb, "lock_shape", False)`; log per-key max displacement, spill, mirror RMS, lid and lip gaps, penetrations.

## Disagreements, myths & open questions

- **Myth: "shape keys store offsets."** They store absolute positions; deltas exist only at evaluation 🧠.
- **Product vs min combination drivers** ↔️: product has a quadratic onset (0.25 at 0.5/0.5), min a linear one; match the sculpted half-way combination.
- **Copy vs transfer vs personalise deltas** ↔️: copy is fast but wrong for large identity changes; transfer keeps semantics; example-based personalisation from the subject's photos is most faithful.
- **Blendshapes vs bones for jaw and eyes** ↔️: ARKit is pure blendshape; production rigs add a jaw bone plus correctives.
- **ARKit left/right** ↔️: Apple's face frame defines the face's own left, but community reports differ; wink-test every capture app.
- **Is 52 enough?** For identity capture yes (expression only needs removing); for animation likeness it lacks AU11, 13, 21, 31, 38/39, cheek suck, independent lower-lid raise and neck 🧠.
- **Open:** MediaPipe range compression and `_neutral` semantics; `lock_shape` version, any make-basis operator, `kb.points`, 5.x shape-key changes, exporter behaviour ↔️; Faceit's listed ceiling is 5.2 while 5.3 is current [8] 📄.

## Sources

URLs [1]–[7] come from the facs-expressions harvest, [8]–[12] from the blender-face-addons harvest.

[1] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d.
[2] Apple ARKit: ARFaceAnchor.BlendShapeLocation — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation — official docs (list not confirmed by harvest) — n.d.
[3] Apple Tech Talks 601: Face Tracking with ARKit — https://developer.apple.com/videos/play/tech-talks/601/ — official video — n.d.
[4] Apple Developer Forums thread 703686 — https://developer.apple.com/forums/thread/703686 — forum — n.d.
[5] MediaPipe Face Landmarker (Google AI Edge) — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d.
[6] MediaPipe Face landmark detection guide for Python — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python — official docs — n.d.
[7] MediaPipe FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — API reference — n.d.
[8] Faceit (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d.
[9] Face Shape Key Rig (Blender Extensions) — https://extensions.blender.org/add-ons/face-shapekey-rig/ — extension listing — n.d.
[10] Fragid/face-shapekey-rig — https://github.com/Fragid/face-shapekey-rig — repository — n.d.
[11] H0wZy/captureforge — https://github.com/H0wZy/captureforge — repository — n.d.
[12] mozi1924/mediapipe-facecap-for-blender — https://github.com/mozi1924/mediapipe-facecap-for-blender — repository — n.d.

**Further reading (by name, not yet linked)**
- Lewis et al., "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Li, Weise & Pauly, "Example-Based Facial Rigging", SIGGRAPH 2010
- Cao et al., "FaceWarehouse", IEEE TVCG 2014
- Li et al., FLAME, SIGGRAPH Asia 2017
- Ekman, Friesen & Hager, *Facial Action Coding System* (2002)
- Casiez, Roussel & Vogel, "1€ Filter", CHI 2012
- Rhodes, Brennan & Carey, "Identification and ratings of caricatures", 1987
- Cosker, Krumhuber & Hilton, D3DFACS, ICCV 2011
- Blender Manual and Python API: Shape Keys, Drivers (Simple Expressions), `bpy.types.ShapeKey`
