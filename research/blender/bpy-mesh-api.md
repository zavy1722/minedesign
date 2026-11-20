# Blender Python API for procedural heads

> On the Blender side, a photo→head pipeline should be a thin bridge over the pure-NumPy engine that does not depend on context. Bulk geometry moves through `foreach_get`/`foreach_set` with contiguous NumPy buffers of exactly the right type (float32 coordinates, int32 indices). Fits are written as shape keys on a template whose topology never changes, region masks are vertex groups, and every photo gets its own camera and background image. Use `bpy.ops` only where no data-API equivalent exists, and always call it through `context.temp_override`. bpy is not thread-safe, so solve on copied arrays in a worker thread or subprocess and apply the results from a main-thread timer or modal operator. Blender 4.1–4.5 bundle Python 3.11, while 5.1 bundles Python 3.13 [2] (other 5.x versions and the NumPy version are unconfirmed: Python 3.11 or 3.13, NumPy 1.26 or 2.x). This topic had no harvest and no earlier draft, so everything here is expert knowledge awaiting verification.
>
> Evidence status: 0 ✅ / 2 📄 / 86 🧠 / 5 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Bulk mesh I/O**
- `foreach_get`/`foreach_set(attr, buf)` on a `bpy_prop_collection` copies a whole attribute inside C. If the buffer is a contiguous NumPy array whose dtype matches the RNA type (float32 `co`, int32 indices, bool flags), it takes the buffer path at close to memcpy speed. Any other dtype (float64, int64) or a strided view **silently** falls back to per-item conversion, which is about 5–20× slower 🧠. The buffer length must be exactly len × components, or the call raises 🧠.
- **Fast creation:** call `vertices.add(V)`, `loops.add(L)` and `polygons.add(F)`. Then `foreach_set` `"co"`, `polygons` `"loop_start"`, and `loops` `"vertex_index"` (or `polygons.foreach_set("vertices", corner_verts)`). Finish with `me.update(calc_edges=True)` 🧠. `MeshPolygon.loop_total` is now derived from the offsets and is read-only, so never write it. Whether that started in 3.6 or 4.0 is unverified 🧠.
- `Mesh.from_pydata()` is itself built on `foreach_set`, but it flattens Python sequences through tuples first. It is fine up to about 10⁵ elements and about 3–10× slower than pre-typed NumPy 🧠. Since 4.1 its `shade_flat=True` default leaves a head faceted, so call `me.shade_smooth()` afterwards 🧠. `me.validate(verbose=True)` repairs hand-built topology. `me.clear_geometry()` empties a mesh in place and keeps its materials and users 🧠.
- `me.vertices` holds **undeformed** data. To read the result after shape keys and modifiers, use `obj.evaluated_get(depsgraph)` and then either `to_mesh()` followed by `to_mesh_clear()`, or `bpy.data.meshes.new_from_object(obj_eval, preserve_all_data_layers=True, depsgraph=dg)`. The latter is the data-API way to "apply" a modifier stack 🧠.
- **Edit mode owns the geometry.** While an object is in edit mode, `me.vertices` is stale, and writes made in object mode are overwritten when edit mode exits. In edit mode, use `bmesh.from_edit_mesh` with `update_edit_mesh`, or call `obj.update_from_editmode()` before reading 🧠.
- **Attributes:** create one with `me.attributes.new(name, 'FLOAT'|'INT'|'FLOAT_VECTOR'|'FLOAT_COLOR', 'POINT'|'FACE'|'CORNER')` and fill it with `attr.data.foreach_set("value"|"vector"|"color", buf)`. Positions are stored as the `position` attribute. Internal attributes have a dot prefix (`.corner_vert`, and probably `.sculpt_mask` and `.sculpt_face_set`); those names are moderate confidence, so probe before use 🧠.
- **Normals:** read `me.vertex_normals` and `polygon_normals` (3.5+) and `corner_normals` (4.1+) with `foreach_get("vector")` 🧠. **Spatial queries:** `mathutils.bvhtree.BVHTree.FromObject(obj, depsgraph)` gives `ray_cast` and `find_nearest`, and `mathutils.kdtree` gives KD-trees. Each call costs a few µs, which is fine for 10³–10⁴ landmark or visibility queries but not for per-vertex work 🧠.

**bmesh**
- bmesh is the **topology** toolkit: `bmesh.ops.bisect_plane`, `symmetrize`, `remove_doubles`, `subdivide_edges`, `triangulate`, `recalc_face_normals`. It is not a bulk-coordinate path: it has no `foreach_*`, so per-vertex access runs at about 0.3–1 µs per element in Python 🧠. Call `ensure_lookup_table()` before indexing and `bm.free()` when finished 🧠.
- bmesh layers expose shape keys (`bm.verts.layers.shape`) and weights (`dl = bm.verts.layers.deform.verify(); v[dl][group_idx] = w`). The deform layer is the fastest pure-Python way to write many distinct weights 🧠.

**Shape keys**
- `obj.shape_key_add(name="Basis", from_mix=False)` creates the first key, which becomes the reference. Add later keys the same way, fill them with `kb.data.foreach_set("co", buf)`, then call `me.update()`, and also `obj.update_tag()` if the viewport stays stale 🧠.
- Keys store **absolute** positions, not deltas. A relative mix is basis + Σ valueᵢ·wᵢ·(keyᵢ − relative_keyᵢ), with wᵢ from `kb.vertex_group` 🧠. `slider_min` and `slider_max` accept −10…10, which allows anti-caricature or exaggeration (for example −1…2) 🧠.
- Once keys exist, the reference key is the source of truth for rest positions. A write to `me.vertices` alone is overwritten from Basis on the next entry into edit mode, so write the Basis key or both 📄 [1].
- The normal modifier Apply refuses meshes that have shape keys. `bpy.ops.object.modifier_apply_as_shapekey(modifier=…, keep_modifier=True)` turns a modifier's result into a key instead 🧠. Multires detail cannot live in a shape key 🧠.

**Vertex groups**
- Create a group with `vg = obj.vertex_groups.new(name="nose")` and fill it with `vg.add(indices, weight, 'REPLACE')`, which takes one weight per call. Weights have no `foreach` path. For continuous weights, bucket them into 256 levels (at most 256 calls, error at most 1/512) or use the bmesh deform layer 🧠. `vg.weight(i)` raises RuntimeError when vertex i is not in the group 🧠.
- A shape key's `vertex_group`, Corrective Smooth, Laplacian Deform, Surface Deform and Data Transfer all consume vertex groups, not generic attributes. Sculpt masks and face sets are separate data 🧠.

**Cameras, background images, images**
- Create a camera with `bpy.data.cameras.new` and `bpy.data.objects.new(n, cd)`, link it, set `lens`, `sensor_width`, `sensor_fit`, `shift_x/y` and `clip_start`, assign `matrix_world = Matrix(M.tolist())`, and set `scene.camera`. **Resolution and pixel aspect are per scene**, not per camera 🧠.
- **Shift units:** `BKE_camera_params_compute_viewplane` multiplies shift by the *fitted* dimension: W under HORIZONTAL, H under VERTICAL, max(W,H) under AUTO. So under HORIZONTAL, shift_x = (W/2 − cx)/W and shift_y = (cy − H/2)/W 🧠. This agrees with the reference-camera-setup note.
- `Object.calc_matrix_camera(depsgraph, x=W, y=H)` returns Blender's own 4×4 projection. Combined with `matrix_world.inverted()`, it gives a vectorised reprojection check. `bpy_extras.object_utils.world_to_camera_view()` is the per-point version and returns normalised frame coordinates with (0,0) at the bottom left 🧠.
- **Background images:** set `cd.show_background_images = True`, then `bg = cd.background_images.new(); bg.image = img`, and use `frame_method` (`STRETCH`, `FIT`, `CROP`), `display_depth` (`BACK`, `FRONT`), `alpha`, `offset`, `rotation`, `scale` and `use_flip_x` 🧠. They show only in the viewport while looking through that camera, and never render 🧠. The alternative is an Image Empty: `empty_display_type='IMAGE'`, `obj.data = img`, `empty_image_depth`, `show_empty_image_only_axis_aligned` 🧠.
- **Images:** load with `bpy.data.images.load(path, check_existing=True)`. Use colour space `sRGB` for photos and `Non-Color` for depth or normals. Read pixels with `img.pixels.foreach_get(np.empty(w*h*4, np.float32))`: RGBA floats, **rows ordered bottom to top**. `list(img.pixels)` is orders of magnitude slower 🧠. For 8-bit files the values are the encoded value / 255, not linearised (moderate confidence) 🧠. A 24 MP photo takes about 384 MB as float RGBA 🧠. Blender ignores EXIF orientation and does not read HEIC, so preprocess photos outside Blender 🧠.

**Operators vs data API; threading**
- `bpy.ops` calls depend on context, run `poll()`, push undo and often trigger depsgraph updates. They cost milliseconds per call and are fragile in timers and under `-b` 🧠. 4.0 removed context-override dicts; use `with context.temp_override(window=…, area=…, region=…, object=obj, active_object=obj, selected_objects=[obj]):` instead (available since 3.2) 🧠.
- This pipeline still needs operators for: `mode_set`, `multires_subdivide`, `multires_reshape`, `voxel_remesh`, `modifier_apply`, `surfacedeform_bind`, `laplaciandeform_bind`, `shape_key_mirror`, and sculpt and brush operators 🧠.
- **No bpy access from other threads, not even reads** 🧠. NumPy releases the GIL in vectorised kernels and LAPACK, so a vectorised solve in a worker overlaps with the UI. Python-level loops in the worker still take GIL time and make the UI stutter 🧠.
- **Getting back onto the main thread:** one option is `bpy.app.timers.register(fn, first_interval=0.1)`, where `fn` returns the seconds until its next run, or None to stop, and `persistent=True` survives a file load. The other is a modal operator using `wm.event_timer_add(0.1, window=context.window)` and `modal_handler_add` that handles `TIMER` and `ESC` 🧠. Timer callbacks get a minimal context with no area 🧠. `blender -b` has no event loop, so batch runs must fit synchronously 🧠.
- Python references to IDs become invalid after undo, redo or a file load. Store names and re-fetch with `bpy.data.objects.get(name)`. Writes made from timers are not on the undo stack 🧠.
- `sys.executable` is the bundled Python interpreter (since roughly 2.91), so `subprocess.Popen([sys.executable, worker, in.npz, out.npz])` gives an isolated solver that cannot crash Blender 🧠.

**Versions** (release dates and probes are in library note blender-version-status-2026)
- **Bundled Python:** 3.10 in 4.0 and 3.11 in 4.1–4.5 🧠. 5.0 probably still bundles 3.11, 5.1 bundles Python 3.13 📄 [2] (corrected in verification), and 5.2–5.3 bundle 3.11 or 3.13 ↔️. NumPy is 1.2x in 4.x and unknown in 5.x (1.26 or 2.x) ↔️.
- **API changes that touch this topic** 🧠:
  - 4.0: override dicts and face maps removed; node-group sockets moved to `NodeTree.interface.new_socket`.
  - 4.1: Auto Smooth removed, replaced by `corner_normals` and `set_sharp_from_angle`.
  - 4.2: extensions arrived (`blender_manifest.toml`, wheels; never bundle numpy).
  - 4.3: brush assets.
  - 5.0: `np.asarray(Vector/Matrix)` returns a float32, non-contiguous view (sourced in the sibling note); `bgl` removed; `bpy.props` values no longer readable through `id["x"]` (moderate confidence).
- Blender is also published on PyPI as the `bpy` module, pinned to one CPython minor version (cp311 for 4.x), which makes headless CI of the bridge possible. Whether 5.x wheels exist is time-sensitive 🧠.

## Numbers & reference tables

**Table 1 – `foreach_*` attribute map** (no buffer path unless the dtype matches)

| Collection | Attribute | NumPy dtype | Values per item | Access | Badge |
|---|---|---|---|---|---|
| `me.vertices` | `co` / `normal` | float32 | 3 | RW / R | 🧠 |
| `me.edges` | `vertices` | int32 | 2 | RW | 🧠 |
| `me.loops` | `vertex_index`, `edge_index` | int32 | 1 | RW | 🧠 |
| `me.polygons` | `loop_start` / `loop_total` | int32 | 1 | RW / R | 🧠 |
| `me.polygons` | `vertices` | int32 | flattened, Σ corners | RW | 🧠 |
| `me.polygons` | `use_smooth` / `material_index` | bool / int32 | 1 | RW | 🧠 |
| `me.loop_triangles` (after `calc_loop_triangles()`) | `vertices` | int32 | 3 | R | 🧠 |
| `me.uv_layers[k].data` | `uv` | float32 | 2 per corner | RW | 🧠 |
| `vertex_normals` / `polygon_normals` / `corner_normals` | `vector` | float32 | 3 | R | 🧠 |
| `me.attributes[n].data` | `value` / `vector` / `color` | depends on type | 1 / 2–3 / 4 | RW | 🧠 |
| `key_blocks[k].data` | `co` | float32 | 3 | RW | 🧠 |
| `img.pixels` | — | float32 | 4 per pixel, rows bottom to top | RW | 🧠 |

**Table 2 – Planning timings** (one desktop core, order of magnitude only; measure on target hardware)

| Operation | 10⁵ vertices | 10⁶ vertices | Badge |
|---|---|---|---|
| `foreach_get/set("co")`, float32, contiguous | 0.1–1 ms | 1–10 ms | 🧠 |
| same with float64 (slow path) | 5–20 ms | 50–200 ms | 🧠 |
| Python loop `v.co = …` | 0.1–0.3 s | 1–3 s | 🧠 |
| `from_pydata` with Python lists | 0.1–0.5 s | 1–5 s | 🧠 |
| `bm.from_mesh` + `bm.to_mesh` | 20–100 ms | 0.2–1 s | 🧠 |
| `img.pixels.foreach_get`, 12 MP image | 50–200 ms (`list()`: 5–30 s) | — | 🧠 |
| a single `bpy.ops` call | 0.1–5 ms, more with undo and redraw | — | 🧠 |

**Table 3 – Camera and background settings for photo matching**

| Property | Default | Set to | Badge |
|---|---|---|---|
| `sensor_fit` | AUTO | HORIZONTAL; under AUTO, a portrait photo switches the fit to height | 🧠 |
| `sensor_width` / `lens` | 36 mm / 50 mm | 36 mm / f_px·36/W | 🧠 |
| `shift_x` / `shift_y` | 0 / 0 | (W/2−cx)/W and (cy−H/2)/W, both divided by **W** | 🧠 |
| camera `clip_start` | 0.1 m | 0.01 m | 🧠 |
| viewport `clip_start` | 0.01 m | 0.001 m for close inspection | 🧠 |
| `resolution_x/y` and `percentage` | per scene | photo W×H at 100 %; switch it whenever the active camera changes | 🧠 |
| background `frame_method` | — | FIT, after asserting \|W/H − res_x/res_y\| < 1e-3 | 🧠 |
| background `display_depth` / `alpha` | BACK / ≈0.5 | FRONT at 0.3–0.5 while checking; offset/rotation/scale at identity | 🧠 |

**Table 4 – Bridge defaults** (engineering choices)

| Quantity | Default | Badge |
|---|---|---|
| Timer interval / main-thread work per tick | 0.05–0.1 s / ≤ 10–20 ms, which keeps the viewport at ≥ 30 fps | 🧠 |
| Weight quantisation | 256 levels (error ≤ 1/512) | 🧠 |
| Agreement between engine and Blender projections | ≤ 0.01 px; anything more is a convention bug | 🧠 |
| Coordinate round-trip tolerance | 1e-6·s, with s the head scale (≈0.14 m), as in the sibling note | 🧠 |
| Live preview | write the key after every LM iteration while V ≤ 10⁵ | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Set up the scene.** Use metric units with 1 BU = 1 m. Create one parent empty `face3d_root` that holds the head and all cameras, and give it a single rotation of R_x(+90°): this maps an engine frame that is Y-up with the face looking toward +Z onto Blender's Z-up frame, with the face looking toward −Y (Front view). Mesh data then stays identical to the engine frame, so round trips are exact.
2. **Template:** build it with the `foreach` recipe and store `template_vid` as an INT point attribute. Keep the landmark→vertex map and the camera solve in a Text datablock (`face3d_fit.json`), which is saved in the .blend and editable, and also in a JSON sidecar.
3. **Photos:** fix orientation and convert HEIC outside Blender, then create one camera per photo using Table 3 and add its background image. To scrub between views, bind each camera to a marker (`scene.timeline_markers.new(name, frame=i).camera = cam`) and set the resolution in a `@persistent` `frame_change_pre` handler from custom properties on the camera object. Plain ID custom properties still work in 5.x 🧠.
4. **Check before you sculpt:** project the landmark vertices with `calc_matrix_camera` and compare them with the 2D detections. A median above about 1 px with a correct engine fit means a convention bug (shift units, y flip, sensor fit), not a likeness problem.
5. **Fit:** write `fit_identity` at value 1.0. Add region keys (`fit_nose`, `fit_jaw`, …) masked by vertex groups so the artist can dial each region from 0 to 1.2. Store per-vertex residuals as a FLOAT_COLOR attribute and view them in Solid mode with Attribute colour.
6. **Hand off for sculpting:** duplicate the object. Read the evaluated mix, call `shape_key_clear()`, write the mix to `vertices` with `foreach_set`, and only then add Multires. Keep the keyed original as the reversible master.
7. **Common failures:**
   - float64 buffers that are slow without any error;
   - writes to `me.vertices` lost while keys exist, or made while in edit mode;
   - `bpy.ops` called from a timer failing on context;
   - stale `obj` references after Ctrl+Z;
   - `img.pixels` rows treated as top-down;
   - shift divided by max(W,H) under HORIZONTAL;
   - one resolution shared by every camera;
   - viewport clipping cutting off the nose.

## Algorithmic implications

- **Layering:** only `face3d/blender/bridge.py` imports bpy. The engine sees float64 arrays and never an ID. Give the engine's `Mesh.faces` (currently a list of lists) a CSR form, `offsets` plus `corner_verts` int32. That maps one-to-one onto `loop_start` and `vertex_index` and removes the Python loops in `triangles()` and `edges()`.
- **Core bridge calls** 🧠:
  ```python
  def read_co(me):
      b = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", b)
      return b.reshape(-1, 3).astype(np.float64)
  def write_key(obj, name, V):
      if obj.data.shape_keys is None: obj.shape_key_add(name="Basis", from_mix=False)
      kb = obj.data.shape_keys.key_blocks.get(name) or obj.shape_key_add(name=name, from_mix=False)
      kb.data.foreach_set("co", np.ascontiguousarray(V, np.float32).ravel()); obj.data.update()
  fut = pool.submit(engine.fit, read_co(me), cams)          # copies only
  def poll():
      if not fut.done(): return 0.1
      obj = bpy.data.objects.get(obj_name)                  # re-fetch, undo-safe
      if obj: write_key(obj, "fit_identity", fut.result())
  bpy.app.timers.register(poll, first_interval=0.1)
  ```
- **Engine bug to fix:** `face3d/geometry/camera.py::to_blender_camera` forces `sensor_fit='HORIZONTAL'` but divides the shift by `max(W,H)`. For portrait photos with an off-centre principal point, the shift comes out too small by a factor of W/H. Divide by W instead 🧠. Add a test that compares `Camera.project` with `calc_matrix_camera` to within 0.01 px for landscape and portrait, centred and shifted, under the PyPI `bpy` module.
- **Constraints the bridge must enforce:** the template vertex count never changes. Refuse to write a key when `len(V) != len(me.vertices)` or the object is in edit mode. Assert float32 and C-contiguous buffers in debug builds. Build mirror maps from a KD-tree on the reflected coordinates, with tolerance 1e-5·s.
- **Painted weights as priors:** treat artist-painted vertex-group weights as per-vertex confidence in [0,1] on the data term, and as a 1/w² scaling of the Laplacian σ inside masked regions (an engineering choice) 🧠.
- **Versions:** probe features (see the sibling note's probe table), and record `bpy.app.version_string`, `sys.version` and `numpy.__version__` with every fit. Convert mathutils values with `np.array(v, dtype=np.float64)`, never with `np.asarray`.

## Disagreements, myths & open questions

- **Myth: "bmesh is the fast API."** It is the topology API. For coordinates, `foreach` on Mesh is 10–100× faster 🧠.
- **Myth: "shape keys store offsets."** They store absolute positions, and the offset is computed relative to `relative_key` 🧠.
- **Myth: "holding the GIL makes bpy safe from a thread."** It does not; the result is a crash or silent corruption 🧠.
- **Real scale or enlarged scale?** ↔️ The library uses 1 BU = 1 m. Some sculptors work at ×10 because default merge distances, clip planes and voxel sizes are friendlier there. float32 precision is no reason to do so, since its spacing is 7.5e-9 m at 0.1 m.
- **Keep the fit as a shape key, or bake it into the base mesh?** ↔️ A key is reversible and can be dialled per region; baking is simpler for Multires and Dyntopo. Keep the key until hand-off.
- **Python and NumPy in 5.x** ↔️: never hard-code either.
- **Open questions:**
  - In which version did `loop_total` become read-only?
  - Does 5.x offer `foreach` or attribute access to vertex-group weights?
  - What are the internal names of the sculpt mask and face-set attributes in 5.x?
  - Is there a Python write path for multires displacement beyond `multires_reshape`?
  - Does the 5.x image loader honour EXIF orientation?
  - Do PyPI `bpy` wheels exist for 5.2 LTS and 5.3, and on which CPython?

## Sources

Verified sources (2026-11-20):
1. Blender issue T98890, editing the Basis shape key from a script does not update mesh vertices; edit-mode round trip re-syncs them: https://developer.blender.org/T98890
2. Blender 5.1 Python API release notes (Python upgraded to 3.13): https://developer.blender.org/docs/release_notes/5.1/python_api/
3. Blender FBX export patch using a buffer that matches the C type of `co` in foreach_get/set (supporting context only, no badge change): https://projects.blender.org/blender/blender-addons/pulls/104448

No other URL sources; remaining facts are unsourced. Related library notes: `blender/blender-version-status-2026.md` (it sources the 5.0 mathutils change and lists release dates and probes) and `blender/reference-camera-setup.md` (camera intrinsics and overlays).

**Further reading (by name, not yet linked)**
- Blender Python API Reference: `bpy_prop_collection.foreach_get/foreach_set`, `Mesh`, `ShapeKey`, `VertexGroup`, `CameraBackgroundImage`, `Image`, `bpy.app.timers`, the modal `Operator` templates, and the "Gotchas" pages
- Blender `bmesh` module and `bmesh.ops` documentation
- Blender Developer Documentation, the Python API release notes for 4.0–4.5 and 5.0, plus the compatibility index
- Blender source: `Mesh.from_pydata` in `bpy_types.py` / `_bpy_types.py`; `BKE_camera_params_compute_viewplane` in `blenkernel/intern/camera.cc`
- Blender Extensions handbook: the `blender_manifest.toml` schema and the Python wheels guidance
- "Blender as a Python Module" (the `bpy` package on PyPI); `fake-bpy-module` (community type stubs)
- NumPy 2.0 migration guide; NEP 50

## Verification log (2026-11-20)

| Claim | Outcome | Source |
|---|---|---|
| Camera shift multiplied by fitted dimension (W under HORIZONTAL); engine divides by max(W,H) | unconfirmed (search returned only source headers and a bug report; no source states the shift units) | https://developer.blender.org/T74577 (context only) |
| Bundled Python 3.11 in 4.1–4.5; 5.0 ~3.11; 5.1–5.3 3.11 or 3.13; NumPy unknown in 5.x | corrected for 5.1: Python 3.13. 5.0, 5.2, 5.3 and NumPy versions unconfirmed | https://developer.blender.org/docs/release_notes/5.1/python_api/ |
| foreach_get/set fast path only for matching dtype and contiguous; silent 5–20× slow fallback otherwise | unconfirmed (a patch supports that matching the C type avoids per-element casting, but no source for silent fallback or the 5–20× figure; Blender tests show some mismatched int/float dtypes raise TypeError) | https://projects.blender.org/blender/blender-addons/pulls/104448 |
| With shape keys, writes to me.vertices co revert from Basis on next edit-mode entry; write the Basis key | confirmed (one source) | https://developer.blender.org/T98890 |
