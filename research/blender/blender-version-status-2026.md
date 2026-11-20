# Blender release status and roadmap as of late 2026

> Blender's 2026 plan was 5.1 in March, 5.2 LTS in July and 5.3 in November [9]. The plan seems to have held. 5.2 LTS came out on 14 July 2026 with support until July 2028 [6][7], 4.5 LTS stays supported until July 2027 [13], and the developer-docs index lists 5.3 as the current stable release, dated 10 November 2026 [12]. **How reliable this is:** every fact here comes from search-result snippets of official blender.org pages that an earlier harvest step collected. No page was opened. My own cross-check searches were refused because the shared web-search budget had run out, and the one direct fetch (developer.blender.org) failed at DNS. So nothing in this note reaches ✅ verified. No retrieved source confirms which Python and NumPy versions ship inside 5.x. The only clues are two 5.0.1 fixes: one "unbreaks" the Python 3.14 build, and one makes a test pass on Python newer than 3.11 [4]. The one add-on-relevant API change the harvest found is 5.0's native buffer protocol for `mathutils` types. NumPy now receives float32, non-contiguous data from them [3]. For a fitting tool, treat the Blender, Python and NumPy versions as facts to read at runtime, never as constants.

## Key facts

- **Blender 5.0 was released on 18 November 2025.** The date appears only in a search snippet of the official release pages and was not re-read on the page [1][2]. ⚠️
- **5.0.1 corrective release, Python-related fixes:** one fix "unbreaks" the Python 3.14 build, and another makes a driver-evaluation test pass with Python newer than 3.11 [4]. Both show only that the build was being tested against newer interpreters. Neither says which Python is *bundled* with 5.0. ⚠️
- **Blender 5.0 Python API change:** `mathutils` types gained native buffer-protocol support. Through that buffer the element type is float32 (not float64), and the buffer is non-contiguous, so scripts that hand vectors or matrices to NumPy may need changes [3]. The harvester could not tie this wording to exact text on the page, so treat it as a lead to confirm. ⚠️
- **The official 2026 schedule** was 5.1 (March 2026), 5.2 LTS (July 2026) and 5.3 (November 2026) [9]. ⚠️ (one publisher, but the later dates below match it)
- **Blender 5.2 LTS was released on 14 July 2026 and is supported until July 2028** [6][7]. The press release for it [8] was found, but no facts were taken from it. ⚠️ (two pages, one publisher)
- **Blender 4.5 LTS is supported until July 2027** [13]. This fits the same two-year LTS window as 5.2 (July 2026 to July 2028). ⚠️
- **Latest stable release on 2026-11-20:** the developer-docs index lists **5.3 (10 Nov 2026)** as current stable [12]. The download page lists **5.2.4 LTS, dated 10 Nov 2026** [6]. ↔️ The two may not actually conflict, because 5.3 is the feature release and 5.2.x is the LTS line. But neither page was opened, so neither "5.3 is out" nor the 5.2.4 date is confirmed.
- **5.2.4 date conflict:** the Blender Projects 5.2 LTS milestone shows a planned date of 16 Nov 2026 in one view and 17 Nov 2026 in another [10]. The download page says 10 Nov [6]. ↔️ (range: 10–17 Nov 2026)
- **Bundled NumPy version for 5.x:** not found in any retrieved source. **Bundled Python version for 5.0, 5.2 LTS and 5.3:** not confirmed. ⚠️ (gap)
- **Migration information:** Blender keeps a compatibility index of add-on migration notes [5], plus per-release Python API pages [3]. Their full contents were not retrieved.

## Numbers & reference tables

**Table 1 – Release timeline (dates as given in official-site snippets)**

| Version | Track | Release date | Support ends | Status | Source |
|---|---|---|---|---|---|
| 4.5 | LTS | not retrieved | July 2027 | ⚠️ | [13] |
| 5.0 | feature | 2025-11-18 | n/a (feature releases are not LTS) | ⚠️ | [1][2] |
| 5.1 | feature | March 2026 (planned) | n/a | ⚠️ plan only | [9] |
| 5.2 | LTS | 2026-07-14 | July 2028 | ⚠️ | [6][7] |
| 5.2.4 | LTS corrective | 2026-11-10 / 11-16 / 11-17 | (inherits 5.2) | ↔️ | [6][10] |
| 5.3 | feature | 2026-11-10 (plan said November 2026) | n/a | ⚠️ / ↔️ | [9][12] |

**Table 2 – Support-window overlap for an add-on (computed from Table 1)**

| Window | LTS lines under support | Implication |
|---|---|---|
| Jul 2026 – Jul 2027 | 4.5 LTS and 5.2 LTS | Supporting both covers every studio still on an LTS release |
| Jul 2027 – Jul 2028 | 5.2 LTS only (plus any later LTS) | 4.5 support can be dropped |

**Table 3 – Runtime constants a fitting engine depends on (unconfirmed, so they must be measured)**

| Quantity | Value | How to obtain |
|---|---|---|
| Bundled Python (5.0 / 5.2 / 5.3) | not confirmed; 5.0.1 fixed the 3.14 build and a >3.11 test [4] | `sys.version_info` at register time |
| Bundled NumPy | not found | `numpy.__version__` |
| Precision of the `mathutils` buffer seen by NumPy (5.0+) | float32, non-contiguous [3] | `np.asarray(vec).dtype`, `.flags` |

## Applying this to photo→3D face sculpting in Blender

1. **Choose the support matrix:** run CI on 4.5 LTS (minimum, until July 2027), 5.2 LTS (main target, until July 2028) and the current feature release (5.3 if it really shipped on 10 Nov 2026) [6][12][13]. Set the manifest's minimum Blender version to match, and drop 4.5 after July 2027.
2. **Log versions with every fit.** Write `bpy.app.version_string`, `sys.version` and `numpy.__version__` into the metadata of each saved fit (landmarks, camera solve, shape coefficients). If a re-fit on another Blender build gives a slightly different head, the log will show whether the build was the cause.
3. **Watch NumPy precision on `mathutils` objects.** From 5.0, `np.asarray(obj.matrix_world)` or `np.asarray(Vector(...))` can come back as a float32 view that is non-contiguous [3]. Camera intrinsics and extrinsics, Procrustes alignments and landmark reprojection residuals should all be computed in double precision. So:
   - convert with `np.array(m, dtype=np.float64)`, never with bare `np.asarray(m)`;
   - call `np.ascontiguousarray` before passing data to compiled routines;
   - never write into such a view expecting to change the Blender object; copy, compute, then assign back.
4. **Bulk mesh I/O** *(standard practice from background knowledge; not checked in this run)*: read and write vertex positions with `foreach_get` / `foreach_set` into preallocated NumPy arrays, then convert to float64 inside the solver. Python-level per-vertex loops are the usual bottleneck on head meshes with tens of thousands of vertices.
5. **Landmark overlays in the viewport** *(background; confirm against [3][5])*: draw 2D/3D landmark markers and reprojection error lines with the `gpu` module only. Older add-ons that use the legacy OpenGL wrapper are the first thing to break on 5.x.
6. **Common failures:**
   - checking the Python minor version instead of detecting features;
   - shipping compiled wheels built for one CPython ABI, which fail to load once Blender's bundled Python changes;
   - tests that compare results bit-for-bit and fail once mathutils→NumPy goes through float32;
   - assuming "latest" means LTS. Studios usually stay on LTS, while hobbyists track 5.3.

## Algorithmic implications

- **Precision boundary:** the solver runs in float64 throughout. All Blender I/O goes through one adapter that converts float32 to float64 on the way in and float64 to float32 on the way out. Express tolerances relative to head scale, for example a fraction of inter-pupillary or bizygomatic width, not as absolute numbers in metres. That keeps convergence tests stable under float32 round-trips.
- **Compatibility layer:** a single `compat.py` detects features (`hasattr`, try/except on API calls) rather than branching on `bpy.app.version`. The version is recorded for diagnostics only.
- **Dependency policy:** keep the core landmark and shape fitting engine to pure Python plus NumPy. Because the bundled NumPy version is unconfirmed, use only APIs that are stable across NumPy 1.x and 2.x (no removed aliases, explicit dtypes). Treat SciPy, PyTorch and similar libraries as optional. Either run them out of process in a separate Python environment, talking to Blender through files or sockets, or ship per-ABI wheels whose builds are checked against the Python that `sys.version_info` reports.
- **Reproducibility defaults:** fixed random seeds for any stochastic initialization; store the solver config, versions and float64 landmark arrays alongside the .blend file; give golden-file regression tests a tolerance, not exact equality.
- **Release-cadence assumption:** plan for three releases a year (spring, summer LTS, autumn), as the 2026 plan shows [9], with an LTS each July and a two-year support window [6][13]. Budget one compatibility pass per feature release and full support for two LTS lines at a time.

## Disagreements, myths & refuted claims

- **"Current stable is 5.3" vs "current is 5.2.4 LTS"** [12] vs [6]: probably two tracks rather than a real conflict. It is still unresolved because neither page was opened. ↔️
- **5.2.4 release date:** 10 Nov (download page [6]) vs 16 Nov and 17 Nov (two views of milestone/33 [10]). The milestone dates may be plans that later moved. ↔️
- **Myth to avoid: "Blender 5.x bundles Python 3.14."** The 5.0.1 notes show only that a Python 3.14 *build* was fixed and that a test was fixed for Python newer than 3.11 [4]. That is evidence of build-system support, not of the bundled interpreter. Unconfirmed.
- **Possible misreading: "mathutils changed from float64 to float32 in 5.0."** The harvester's wording suggests the element type changed. A likelier reading is that the new buffer protocol exposes the existing single-precision storage directly to NumPy, where before NumPy went through the sequence protocol and created float64 arrays. That reading comes from background knowledge and is unverified. In practice the advice is the same: specify `dtype=np.float64` explicitly [3].
- **Refuted:** none. No independent searches could run, so no claim could be tested to refutation.

## Open questions

1. Which Python version is bundled in 5.0, 5.2 LTS and 5.3? (Check `sys.version` in each official build, or the Python API release-notes pages [3].)
2. Which NumPy version is bundled in 5.x, and did any 5.x release move from NumPy 1.x to 2.x?
3. What is the full list of 5.0 → 5.3 Python API breaking changes affecting add-ons (bpy.props / IDProperty access, `gpu` vs legacy GL, mesh attribute API, sculpt operators)? The compatibility index [5] was not retrieved.
4. What are the sculpt and modeling roadmap items for 5.3 and 2027 (for example sculpt-mode performance, brush assets, multires and dyntopo status)? [9] was found, but its sculpt content was not extracted.
5. Did 5.3 actually ship on 10 Nov 2026, and was 5.2.4 released on 10, 16 or 17 November?
6. How compatible are 5.x add-ons in practice, according to practitioners (BlenderArtists, Reddit, extensions.blender.org issue trackers)? This was not searched.
7. Is a 5.4 or 6.0 planned for 2027, and is the next LTS still due in July 2027? Not searched.

**Process note:** in this run the shared WebSearch budget was already used up (0 of the planned 12 verification and gap-filling searches ran), and developer.blender.org failed to resolve at DNS, so it would need to be allowed in the session's network settings before it can be fetched. A follow-up run should first open [3], [4], [5], [6] and [12] directly.

## Sources

[1] Blender 5.0 — https://www.blender.org/releases/5-0/ — official-docs — 2025
[2] Blender 5.0 Release Notes — https://developer.blender.org/docs/release_notes/5.0/ — official-docs — 2025
[3] Blender 5.0: Python API — https://developer.blender.org/docs/release_notes/5.0/python_api/ — official-docs — 2025
[4] Blender 5.0: Corrective Releases — https://developer.blender.org/docs/release_notes/5.0/corrective_releases/ — official-docs — 2025
[5] Index – Blender Developer Documentation (compatibility) — https://developer.blender.org/docs/release_notes/compatibility/ — official-docs — n.d.
[6] 5.2 LTS — Blender (download/releases) — https://www.blender.org/download/releases/5-2/ — official-docs — 2026
[7] Blender 5.2 LTS — Blender — https://www.blender.org/releases/5-2/ — official-docs — 2026
[8] Blender 5.2 LTS Release — Blender (press) — https://www.blender.org/press/blender-5-2-lts-release/ — official-docs — 2026
[9] Projects to Look Forward to in 2026 — Blender — https://www.blender.org/development/projects-to-look-forward-to-in-2026/ — official-docs — 2026
[10] 5.2 LTS milestone — Blender Projects — https://projects.blender.org/blender/blender/milestone/33 — repo — 2026
[11] 5.0 milestone — Blender Projects — https://projects.blender.org/blender/blender/milestone/20 — repo — 2025
[12] Blender Release Notes — Blender Developer Documentation (index) — https://developer.blender.org/docs/release_notes/ — official-docs — n.d.
[13] Release Notes — Blender (index) — https://www.blender.org/download/releases/ — official-docs — n.d.
