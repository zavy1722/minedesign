# Shape keys and blendshape standards

> Blender stores every shape key as a full, absolute copy of the vertex positions. In relative mode it mixes them as Basis + Σ valueᵢ·maskᵢ·(keyᵢ − relative_keyᵢ) before any modifier runs. That makes shape keys the natural non-destructive container for a photo-fitted likeness, artist passes and an expression set, all on one frozen topology. The de facto expression vocabulary is Apple's ARKit 52 coefficients in [0, 1]. MediaPipe Face Landmarker emits 52 named scores with the same camelCase names (minus `tongueOut`, plus `_neutral`), so a clone keyed with exact ARKit names can be driven, and audited, by phone or webcam capture. Linear deltas fail on arcs (eyelids, jaw) and on muscle combinations, so a usable set adds in-betweens and product-driven correctives, and after an identity fit the template's deltas must be transferred, not copied. No harvest or earlier draft existed for this topic: 📄 facts come from sibling harvests in this library (Apple, Google and add-on listings); everything else is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 17 📄 / 109 🧠 / 11 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Blender data model**
- Keys live on a `Key` ID datablock (`mesh.shape_keys`, also listed in `bpy.data.shape_keys`). It holds `key_blocks`, `reference_key` (the first key, "Basis"), `use_relative` and its own `animation_data`. Shape-key drivers and keyframes therefore sit on the Key, not on the object or mesh 🧠.
- Each `ShapeKey` stores absolute float32 coordinates for every vertex: 12 bytes per vertex per key, never sparse 🧠. It also carries `value`, `slider_min`/`slider_max` (defaults 0 and 1, hard limits −10…10), `relative_key`, `vertex_group` (a mask, stored by name), `mute`, `interpolation` (used only in absolute mode) and, in 4.x, `lock_shape` 🧠. Which 4.x release added the lock is unclear (4.0 or 4.1) ↔️.
- **Relative evaluation:** X = X_ref + Σᵢ valueᵢ·wᵢ(v)·(Kᵢ − K_relᵢ). Muted and zero-valued keys are skipped, so the cost scales with the number of *active* keys 🧠. Keys evaluate before the whole modifier stack, so Armature, Corrective Smooth and Surface Deform all see the mixed shape 🧠.
- **Python:** `obj.shape_key_add(name="Basis", from_mix=False)`. The defaults are `name="Key"` and `from_mix=True`, so always pass both 🧠. Fill a key with `kb.data.foreach_set("co", buf_f32)`, or `kb.points` (an optimised accessor in recent versions 🧠), then call `me.update()`. Also useful: `obj.shape_key_remove(kb)`, `obj.shape_key_clear()`, `obj.active_shape_key_index`, `obj.show_only_shape_key` (pin) and `obj.use_shape_key_edit_mode` 🧠.

**Editing semantics (where likeness work goes wrong)**
- Edit Mode and Sculpt Mode write into the **active** key 🧠. Editing the reference key interactively propagates the same offset to the keys that depend on it, so their deltas survive unchanged 🧠. A **Python write to Basis does not propagate**: every dependent key keeps its absolute positions, so its delta silently becomes (old delta − Δ) 🧠. The engine must add Δ to the dependent keys itself, or recompute them.
- Sculpting into a key whose value is not 1, or into an unpinned key while other keys are active, gives unpredictable strokes. Pin the key, or set it to 1 with everything else at 0 🧠.
- Apply is refused on a mesh with shape keys. `object.modifier_apply_as_shapekey(keep_modifier=True)` ("Save as Shape Key") captures a modifier's result as a new key 🧠, and SKkeeper-style add-ons apply a modifier one key at a time 🧠. Multires detail and the output of Dyntopo or Remesh cannot live in keys (see `blender-sculpt-features-5x.md`) 🧠.
- **Operators** 🧠:
  - `object.shape_key_remove(all=True, apply_mix=True)` applies all keys.
  - `shape_key_mirror(use_topology=False)` mirrors a key.
  - `shape_key_transfer` (Copy Shape) needs the same vertex count; `join_shapes` is Join as Shapes.
  - `shape_key_move(type='TOP')` moves a key to the top, which makes it the new reference.
  - In Edit Mode: `mesh.blend_from_shape(shape, blend, add)` and `mesh.shape_propagate_to_all()`.
- **Cross-topology transfer:** bind a **Surface Deform** modifier on the target to the template at rest. Set one template key to 1, run `modifier_apply_as_shapekey(keep_modifier=True)`, and loop over every key 🧠.

**Drivers**
- Create one with `fc = kb.driver_add("value")`. Read other keys through `SINGLE_PROP` variables with `id_type='KEY'`, `id=me.shape_keys` and `data_path='key_blocks["jawOpen"].value'`. Read bones through `TRANSFORMS` or `ROTATION_DIFF` variables; the Swing/Twist rotation modes isolate a hinge angle 🧠. Pass ID pointers, not names, because "Key.001"-style names drift 🧠.
- Blender evaluates **simple expressions** natively, without Python: arithmetic, comparisons, conditional expressions and whitelisted maths functions such as `min`, `max`, `abs` and `clamp` 🧠. Anything else, or "Use Self", needs Python and fails while Auto Run Python Scripts is off, which is the default 🧠. Keep every corrective expression simple.

**ARKit 52**
- ARKit reports `blendShapes` as named coefficients from 0 (neutral) to 1 (maximum movement), updated live [1][3] 📄. The set is called "ARKit 52" [11] 📄. The harvest could not confirm the full name list; a forum list starts with `jawOpen` and `eyeLookDown` [4] 📄.
- **The names** (🧠; verify against [2]): 14 eye, 5 brow, 3 cheek, 2 nose, 4 jaw, 23 mouth and 1 tongue coefficient. The full list and the cross-system spellings are in `data/shapekeys-blendshapes.json`, consistent with `anatomy/facs-expressions.md`.
- **Naming drift is the commonest interop bug** 🧠:
  - Swift case `eyeBlinkLeft`;
  - Apple raw string `eyeBlink_L`;
  - Live Link Face CSV header `EyeBlinkLeft` (61 columns: 52 shapes + 9 head and eye angles);
  - MediaPipe `eyeBlinkLeft`.

  Normalise every spelling to one canonical form at the boundary.
- `mouthClose` means the lips closing *while the jaw is open*. Author it as (jawOpen with lips sealed) − jawOpen, and never fire it alone 🧠.
- ARKit's face mesh (`ARFaceGeometry`) has 1,220 vertices and 2,304 triangles 🧠, consistent with `import-export-scans.md`.

**MediaPipe**
- Face Landmarker outputs 478 landmarks plus 52 blendshape categories with scores in [0, 1] [5][7] 📄. Blendshapes are off unless `output_face_blendshapes=True` [6] 📄. Left and right refer to the subject, so a mirrored (selfie) image swaps them [5] 📄.
- The 52 categories are `_neutral` at index 0, then the 51 ARKit names without `tongueOut` in alphabetical order 🧠. The names match ARKit camelCase, so `key_blocks.get(cat.category_name)` maps directly once `_neutral` is skipped 🧠.
- The blendshape head is a small network fed by landmarks, reportedly a subset of about 146 🧠. Its scores are therefore not independent of the landmarks: never use both as separate likelihood terms.
- Scores are uncalibrated and some channel ranges are compressed. `eyeBlink` often peaks well below 1, and `cheekPuff` and `noseSneer` stay near 0 ↔️. A per-subject remap is standard practice 🧠.

**Other sets and FACS-based bases**
- Table 1 lists the other standards. FACS action units are muscle-based appearance codes, whereas ARKit and MediaPipe are FACS-inspired tracker outputs, not FACS intensities (`facs-expressions.md`) 🧠.
- Semantic (FACS-like) bases are non-orthogonal and redundant, which makes inverse fitting ill-conditioned. PCA bases (FLAME, FaceWarehouse) are orthogonal but not readable by artists (Lewis et al. 2014) 🧠.

**Correctives and in-betweens**
- **Combination model:** X = X₀ + Σ wₖDₖ + Σ wᵢwⱼDᵢⱼ + Σ wᵢwⱼwₗDᵢⱼₗ. Each corrective is driven by the product of its parents' weights (Lewis et al. 2014) 🧠. `min(a, b)` is a common alternative ↔️.
- Blender has no native in-between targets, unlike Maya and Unity 🧠. To emulate an in-between I at w = 0.5 before the full shape F, use two keys: drive I by `max(0, 1-abs(2*w-1))` and F by `max(0, 2*w-1)`. Both are simple expressions 🧠 (derived).
- A **pose-space corrective** is sculpted on a posed rig but must be stored in rest space. That needs either the inverse of the deformation, which the Corrective Shape Keys add-on (formerly bundled) computes 🧠, or sculpting through the armature, where Blender's crazyspace maps strokes back to rest space approximately 🧠.

**Blender add-ons** (time-sensitive)
- **Faceit** (paid) semi-automatically generates ARKit-style, Audio2Face, tongue and phoneme keys. It bakes modifier, pose and sculpt deformation into keys, and its listing states Blender 3.0–5.2 [8] 📄.
- **Face Shape Key Rig** (free, GPL) builds viewport sliders and 2D pads, driven by bones and drivers, for *existing* keys, with iFacialMocap and audio lipsync [9][10] 📄. It requires Blender 5.2+ [10] 📄.
- **CaptureForge** (GPL-3.0) converts a posed face rig into the ARKit 52 shapes and drives them from video or webcam, without an iPhone [11] 📄.
- **mediapipe-facecap-for-blender** pairs a MediaPipe transmitter program with a Blender receiver add-on [12] 📄.

**Export**
- FBX stores blendshape channels with a 0–100 weight. Unity also uses 0–100, while Unreal morph targets and glTF use 0–1 🧠. glTF stores morph-target names in `mesh.extras.targetNames` by convention 🧠.
- Do not rely on any exporter to honour a key's `vertex_group`, a non-Basis `relative_key` or drivers. In FBX, keys can also be dropped on a mesh with active non-Armature modifiers. Bake all of these first ↔️.

## Numbers & reference tables

**Table 1. Blendshape standards** (counts are time-sensitive)

| Standard | Count | Range | Naming; left/right | Tongue | Badge |
|---|---|---|---|---|---|
| ARKit (Apple) | 52 [11] | 0–1 [1] | camelCase Swift; raw `_L`/`_R`; subject's side (wink-test) | `tongueOut` | 📄 count, range; names 🧠 |
| MediaPipe Face Landmarker | 52 incl. `_neutral` [5] | 0–1 [5][7] | ARKit camelCase; subject's side [5] | none | 📄; composition 🧠 |
| Live Link Face CSV | 52 + 9 head/eye angles | 0–1 | PascalCase | yes | 🧠 |
| Meta Movement SDK face | 63 (≈70 with tongue, v2) | 0–1 | FACS-style UPPER_SNAKE | v2 | 🧠 ↔️ |
| VRM 1.0 / 0.x presets | 18 / 17 | 0–1 | happy, aa, blink… | no | 🧠 |
| Oculus/Meta visemes | 15 | 0–1 | sil PP FF TH DD kk CH SS nn RR aa E ih oh ou | n/a | 🧠 |
| FaceWarehouse (Cao et al. 2014) | 47 (neutral + 46 FACS); 150 people | 0–1 | bilinear model | no | 🧠 |
| FLAME 2020 | 100 expression PCA + 36 pose correctives; 5,023 vertices | unbounded | non-semantic | no | 🧠 |
| ICT FaceKit | ≈53 FACS-based expressions + 100 identity PCA (recalled) | 0–1 | ARKit-like | unknown | 🧠 |
| MetaHuman | ≈250 `CTRL_expressions_*` controls → joints + correctives | 0–1 | FACS-style | yes | 🧠 (`metahuman-cc-bridges.md`) |

**Table 2. Error of a linear delta at w = 0.5** (derived: r·(1 − cos θ/2))

| Motion | Radius r | Sweep θ | Mid-weight error | Visible failure | Badge |
|---|---|---|---|---|---|
| Upper lid over the globe | 12–13 mm (globe ≈24 mm long) | 40–60° (≈49° for a 10 mm fissure) | 0.7–1.7 mm inward | lid cuts into the cornea mid-blink | 🧠 derived |
| Jaw, at incisor or chin | 100–120 mm | 15–30° | 0.9–4.1 mm toward the condyle | chin shortens mid-open; lips over-stretch | 🧠 derived |

**Table 3. Plausibility bounds at weight 1** (adult; QA only, not norms; calibrate on 4D data such as D3DFACS)

| Key | Measure | Bound | Badge |
|---|---|---|---|
| eyeBlink | upper-lid margin travel; closure gap | 8–12 mm; gap 0–0.5 mm, never crossing | 🧠 |
| eyeWide / eyeSquint | upper-lid rise / lower-lid rise | 1–4 mm / 1–3 mm | 🧠 |
| browInnerUp, browOuterUp | brow rise | 5–12 mm | 🧠 |
| browDown | brow drop plus medial pull | 3–8 mm | 🧠 |
| cheekSquint | malar lift | 2–5 mm | 🧠 |
| mouthSmile / mouthStretch | cheilion displacement | 7–15 mm / 3–8 mm lateral | 🧠 |
| mouthPucker, mouthFunnel | lip protrusion | 6–12 mm | 🧠 |
| jawOpen | interincisal opening | 40–60 mm (`facs-expressions.md`) | 🧠 ↔️ |
| jawForward, jawLeft/Right | protrusion / lateral shift | 5–10 mm | 🧠 |
| cheekPuff / noseSneer | cheek outward / alar lift | 5–15 mm / 1–4 mm | 🧠 |

**Table 4. Corrective and in-between starter set** (`jo` = jawOpen, `eb` = eyeBlink and so on; all simple expressions)

| Shape | Driver | Purpose | Priority | Badge |
|---|---|---|---|---|
| mouthClose guard | `min(mc, jo)` | lips never cross when the jaw is shut | high | 🧠 |
| jawOpen in-between | `max(0,1-abs(2*jo-1))` | jaw arc (or use a jaw bone) | high | 🧠 |
| eyeBlink in-between L/R | `max(0,1-abs(2*eb-1))` | lid arc over the cornea | high | 🧠 |
| jawOpen × mouthSmile L/R | `jo*s` | open smile | high | 🧠 |
| jawOpen × mouthFunnel / mouthPucker | `jo*f` | "oh" / "oo" visemes | medium | 🧠 |
| eyeBlink × eyeLookDown/Up | `eb*ld` | lid follows gaze | medium | 🧠 |
| eyeBlink × eyeSquint / cheekSquint | `eb*sq` | lower-lid bunching | medium | 🧠 |
| browDown × browInnerUp | `bd*bi` | AU1+4 grief brow | medium | 🧠 |
| mouthSmile × cheekSquint | `s*cs` | AU6+12 infraorbital bulge | medium | 🧠 |
| mouthPucker × mouthFunnel | `p*f` | lip volume | low | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Freeze the topology, then key everything.**
   - Basis = the template mean.
   - `ID_fit` = the engine output, written with `from_mix=False`.
   - `artist` = the sculpt layer.
   - Give `ID_fit` a `slider_max` of 1.5. Values of 1.1–1.3 exaggerate the deviation from the mean, which aids recognisability (the caricature effect, Rhodes, Brennan & Carey 1987) 🧠. This holds only if Basis really is a mean face.
2. **Author the expression set once, on the template.** Use exact ARKit camelCase names, built with Faceit [8], CaptureForge [11], your own sculpting, or deformation transfer from a rig you are licensed to use.
   - **Splitting left and right:** sculpt the shape symmetric, then split it with masks whose weights sum to 1 across a 10–20 mm smoothstep band at the midline. L + R then reproduces the symmetric key exactly 🧠.
   - The character faces −Y, so the subject's left is +X (Rigify `.L`) 🧠.
3. **Transfer the deltas after the identity fit; do not copy them.**
   - First pass: scale each delta by s = IOD_subject / IOD_template and rotate it into the local frame. For production, use deformation transfer.
   - Then re-fit eyelid closure and lip seal to the subject's own fissure and lip geometry.
   - Bake: Basis_new = Basis + Δ_ID, and each key becomes Basis_new + T(Δ_k). Then delete `ID_fit`.
   - UI shortcut: in Edit Mode on Basis, select all, Blend from Shape `ID_fit` (add off, blend 1), then exit. The offset propagates to the dependent keys (a naive copy) 🧠. Verify this on a copy first.
4. **Check every key at 1 on the cloned head** 🧠:
   - lid closure gap 0–0.5 mm, without crossing;
   - lips sealed at jawOpen + mouthClose;
   - no teeth or eyeball penetration;
   - L/R mirror RMS ≤ 0.5 mm on the template;
   - spill (displacement energy outside the key's region mask) ≤ 1–2 %;
   - magnitudes inside Table 3.
5. **Drive the satellite meshes.** Teeth, tongue, eyelashes and caruncle get same-named keys driven by the face keys through `SINGLE_PROP` drivers, or ride a jaw bone 🧠. Hair curves follow through Deform Curves on Surface (`hair-blender.md`).
6. **Run an expression-likeness test.** Run MediaPipe on the subject's own expression photos [5][6], remap the scores, set the keys, render through the solved camera and compare landmarks. If the neutral matches but the expressions do not, the deltas need personalising (example-based rigging) 🧠.
7. **Export.** Bake masks, non-Basis relatives and drivers into plain keys. Use FBX for Unity (0–100) and Unreal, and glTF with `targetNames`. Keep the vertex order.

**What goes wrong** 🧠:
- A Python write to Basis without propagating, which makes the expression keys "anti-apply" the edit.
- Sculpting identity while an expression key is active, or sculpting into a key that sits at 0.4.
- A mirrored selfie swapping left and right [5].
- MediaPipe `eyeBlink` never closing the lids without a remap.
- Linear jaw and lid chords (Table 2).
- `mouthClose` used on its own.
- Drivers silently dead because they need Python.
- Multires, Dyntopo or Remesh destroying the keys.
- Exporters dropping masked or relative-chained keys.

## Algorithmic implications

- **Data structure.** `Basis = {names[K], D: K×V×3 float32, masks, lr_pairs, antagonists, combos[(idx…), D_c], inbetweens[(k, w, D_i)]}`. The canonical names are ARKit camelCase, with adapters for `_L`/`_R`, PascalCase and `_neutral` 🧠.
- **Forward model.** X(ψ) = X₀ + Σ ψₖDₖ + Σ_c (Π_{k∈c} ψₖ)·D_c, plus in-betweens. The Jacobian is ∂X/∂ψₖ = Dₖ + Σ_{c∋k} (Π_{j∈c∖k} ψⱼ)·D_c 🧠.
  - Precompute D only at the landmark barycentric coordinates (L×3×K), so K = 51 gives a dense 51×51 normal system per view.
  - Exclude `tongueOut` from photo fits.
- **Bounds and priors** (🧠 engineering defaults, consistent with `facs-expressions.md` and `expression-neutralization.md`):
  - Box constraint ψ ∈ [0, 1], enforced by projected Gauss–Newton or bounded Levenberg–Marquardt.
  - Neutral views: a half-normal prior with σ = 0.07 (0.05–0.10), plus an L1 term with λ ≈ 0.01–0.05 on residuals normalised by IOD.
  - Expressive views: σ = 0.5.
  - MediaPipe score as an observation of ψ: σ = 0.15–0.25 once calibrated, 0.3 uncalibrated. Use it to initialise and as a prior, never alongside the landmarks as a second data term.
  - Antagonist penalty λ_a·ψ_a·ψ_b, weighted 1–10× the data term, only for blink/wide on the same eye, jawLeft/Right, mouthLeft/Right, and lookIn/lookOut on the same eye.
  - Correctives are deterministic functions of ψ. Keep them in the forward model so the identity does not absorb combination geometry.
  - Fit a jaw rotation θ about the TMJ hinge instead of `jawOpen` deltas. Neutral prior: N(1.5°, 1°²).
- **Conditioning.** Compute G = DᵀD at the landmarks. If cond(G) exceeds about 10⁴, add a ridge term, or solve in an orthogonalised basis and map back to the semantic weights 🧠.
- **Transfer.** Deformation transfer (Sumner & Popović 2004) needs one sparse factorisation of the Poisson system per subject, then 52 back-substitutions 🧠. A numpy-only fallback is conjugate gradient with a Jacobi preconditioner. For the first-pass delta scaling, expect s ∈ [0.86, 1.14], from an adult IPD of about 54–72 mm against a 63 mm template 🧠 (derived).
- **Remap from MediaPipe to the rig** 🧠:
  - w′ = clamp((w − lo)/(hi − lo), 0, 1)^γ.
  - lo = the 90th–95th percentile on neutral frames; hi = the 95th–99th percentile over a range-of-motion clip.
  - γ = 1 (0.7–1.5).
  - For video, smooth with a One Euro filter (Casiez et al. 2012): min_cutoff ≈ 1 Hz, β ≈ 0.005–0.05.
- **QA log.** Per key: maximum displacement, spill, mirror RMS, lid gap, lip-seal gap, penetration count, and the chord error against the in-between 🧠.
- **Blender bridge** 🧠:
  - Write keys with float32 `foreach_set` and set `relative_key` explicitly.
  - Build drivers with ID pointers and simple expressions.
  - Never write Basis without propagating Δ to its dependents.
  - Respect `getattr(kb, "lock_shape", False)`.

## Disagreements, myths & open questions

- **Myth: "shape keys store offsets."** They store absolute positions; the deltas are computed at evaluation 🧠.
- **Product vs min combination drivers** ↔️. A product gives a quadratic onset (0.25 at 0.5/0.5) and min gives a linear one. Studios use both, so pick the one that matches the sculpted half-way combination.
- **Copy, transfer or personalise deltas** ↔️. Copying is fast but wrong for large identity changes. Transfer preserves the semantics. Personalising from the subject's own expression photos (example-based rigging) is the most faithful.
- **Blendshapes vs bones for the jaw and eyes** ↔️. ARKit is pure blendshapes; production rigs use a jaw bone plus correctives.
- **ARKit left/right** ↔️. Apple's face coordinates define the face's own left, but community reports differ, so wink-test every capture app.
- **Open:** MediaPipe's range compression and what `_neutral` means; whether 52 shapes are enough. For identity capture they are, since the expression only needs removing. For animation likeness they lack AU11, 13, 21, 31 and 38/39, cheek suck, an independent lower-lid raise and the neck 🧠.
- **Unverified versions:** `lock_shape` (4.0 or 4.1), any make-basis operator, `kb.points`, 5.x shape-key changes, and glTF and FBX exporter behaviour ↔️. Faceit's listed ceiling is 5.2 while 5.3 is current [8] 📄.

## Sources

[1] Apple ARKit: ARFaceAnchor.blendShapes — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapes — official docs — n.d. (facs-expressions harvest)
[2] Apple ARKit: ARFaceAnchor.BlendShapeLocation — https://developer.apple.com/documentation/arkit/arfaceanchor/blendshapelocation — official docs (name list not confirmed by the harvest) — n.d. (facs-expressions harvest)
[3] Apple Tech Talks 601: Face Tracking with ARKit — https://developer.apple.com/videos/play/tech-talks/601/ — official video — n.d. (facs-expressions harvest)
[4] Apple Developer Forums thread 703686 — https://developer.apple.com/forums/thread/703686 — forum — n.d. (facs-expressions harvest)
[5] MediaPipe Face Landmarker (Google AI Edge) — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — n.d. (facs-expressions harvest)
[6] MediaPipe Face landmark detection guide for Python — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python — official docs — n.d. (facs-expressions harvest)
[7] MediaPipe mp.tasks.vision.FaceLandmarkerResult API — https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarkerResult — API reference — n.d. (facs-expressions harvest)
[8] Faceit: Facial Expressions and Performance Capture (Superhive) — https://superhivemarket.com/products/faceit — commercial listing — n.d. (blender-face-addons harvest)
[9] Face Shape Key Rig (Blender Extensions) — https://extensions.blender.org/add-ons/face-shapekey-rig/ — extension listing — n.d. (blender-face-addons harvest)
[10] Fragid/face-shapekey-rig — https://github.com/Fragid/face-shapekey-rig — repository — n.d. (blender-face-addons harvest)
[11] H0wZy/captureforge — https://github.com/H0wZy/captureforge — repository — n.d. (blender-face-addons harvest)
[12] mozi1924/mediapipe-facecap-for-blender — https://github.com/mozi1924/mediapipe-facecap-for-blender — repository — n.d. (blender-face-addons harvest)

**Further reading (by name, not yet linked)**
- Lewis, Anjyo, Rhee, Zhang, Pighin & Deng, "Practice and Theory of Blendshape Facial Models", Eurographics STAR 2014
- Sumner & Popović, "Deformation Transfer for Triangle Meshes", SIGGRAPH 2004
- Li, Weise & Pauly, "Example-Based Facial Rigging", SIGGRAPH 2010
- Cao, Weng, Zhou, Tong & Zhou, "FaceWarehouse: A 3D Facial Expression Database for Visual Computing", IEEE TVCG 2014
- Li, Bolkart, Black, Li & Romero, FLAME, SIGGRAPH Asia 2017
- Ekman, Friesen & Hager, *Facial Action Coding System* manual (2002)
- Casiez, Roussel & Vogel, "1€ Filter", CHI 2012
- Rhodes, Brennan & Carey, "Identification and ratings of caricatures", Cognitive Psychology 1987
- Cosker, Krumhuber & Hilton, D3DFACS, ICCV 2011
- Blender Manual: Shape Keys; Drivers (Simple Expressions); Python API `bpy.types.ShapeKey`, `bpy.types.Key`
- Apple ARKit documentation: `ARFaceGeometry`; Unreal Live Link Face documentation
