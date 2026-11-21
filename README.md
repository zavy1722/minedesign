# face3d: photos of a face to a sculpt-ready 3D head in Blender

This repository has three parts:

- **A research library.** [`research/`](research/README.md) holds 94 topic notes, about 390,000 words, on facial anatomy, photo-to-3D reconstruction, Blender, community likeness practice, and ethics and licensing. Every claim carries an evidence badge.
- **A fitting engine in pure Python.** [`face3d/`](face3d) needs only numpy. It reads photographs of one consenting person, solves for cameras, focal lengths, scale and 44 anatomical landmarks with honest uncertainty, and warps a template head onto them.
- **A Blender extension.** [`blender_ext/face3d_likeness/`](blender_ext/face3d_likeness) takes you from photos to cameras, a fitted head and a shape-key stack ready for sculpting. It shows which parts of the head were measured and which are educated guesses.

The design is in [`docs/DESIGN.md`](docs/DESIGN.md), the plan in [`docs/wbs.json`](docs/wbs.json) (24 work packages), and measured results in [`docs/RESULTS.md`](docs/RESULTS.md) (written by the release-gate package WP-23).

> **Status: not validated against a scan.** Every accuracy and honesty number in this repository comes from a synthetic test bed: simulated subjects, phone rigs and detector noise. Real-world calibration (WP-24) needs Blender, MediaPipe, human annotators, a 3D-printed head and consenting sitters. None of that existed where this was built, so it is a documented offline programme ([below](#what-still-needs-doing-offline)). The engine prints this banner on every report until a configuration passes tiers 3 and 4.

## How a face gets from photos to a head

```
photos ─► triage ─► landmarks ─► solve ─► observe ─► fit ─► texture ─► hand-off ─► report
          (QA,      (MediaPipe   (bundle   (honest    (template  (gated,   (shape keys,
          EXIF      in your own  adjust:   sigma,     warp A-D:  consent   protect mask,
          focal)    Python, or   cameras,  claims     similarity,+ rights) multires cage)
                    manual pins) focal,    ledger,    RBF,
                                 scale,    tiers,     Laplacian,
                                 prior)    next-best  contours)
                                           photo)
```

- **Cameras are solved, not assumed.** Each photo gets a perspective camera: rotation, inverse depth, focal length from EXIF where it can be trusted, and principal point. Selfie-distance distortion is the biggest single source of "it doesn't look like them". The solver models it instead of using orthographic shortcuts.
- **Scale is explicit.** It comes from a measured caliper or card reference when you have one, then the iris diameter (only when it is at least 20 px, sharp and not behind glasses), and otherwise a population prior (log-scale σ 0.045, reported after inflation, typically ±5 %). The report states which one was used.
- **Anatomy is the prior.** A 44-landmark, 18-factor metric prior is built from the anthropometric notes. It is never conditioned on ancestry, and it widens for unknown populations. Robust estimation (Huber, then Tukey, then rejection) and a mirror-flip test guard against detector errors and selfie mirroring. A mirror flip is only ever suggested to you, never applied silently.
- **Honesty is a hard requirement.** Every region of the head is labelled *measured*, *constrained*, *prior-driven* or *unobserved*, with a ±mm figure. These figures are calibrated: they are checked to really contain the error at the stated rate, through the NEES and coverage gates on the test bed. The report also names the next photo that would help most.
- **Hand-off is made for artists.** The fit lands as shape keys on a clean, symmetric, quad template: `Basis`, `ID_fit` (the symmetric part of the fit) and `Asym` (the person's real asymmetry, never symmetrised away). Optional extras are a sculpt mask that protects measured regions and a Multires cage fitted through limit stencils.

## Quick start

Requirements: Python ≥ 3.11, numpy, and pytest for the tests. Blender ≥ 4.5 for the extension.

```bash
python -m pytest -q                          # the full suite (about 5 min on one core)
python -m face3d --help                      # triage | solve | fit | report | job | testbed
python -m face3d report --project my_head/project.json --landmarks my_landmarks/
python -m face3d testbed scorecard --help    # the synthetic benchmark
python tools/build_extension.py --no-store dist/face3d_likeness.zip   # installable Blender extension
```

Landmarks come from one of two places. You can run [`tools/detect_mediapipe.py`](tools/detect_mediapipe.py) in **your own** Python, with a MediaPipe `.task` model you downloaded and pinned by SHA-256; the extension never downloads or bundles models. Or you can place pins by hand with the extension's pin tool. Consent is checked before any landmark is read. Photo hashes must be covered by a consent record, and the default is deny.

In Blender: **Edit → Preferences → Get Extensions → Install from Disk**, choose the zip, then open the *Face3D* tab in the 3D Viewport sidebar. Its guided rail walks through Consent, Photos, Check (decision cards), Landmarks, Cameras, Shape, Confidence, Sculpt, Texture and Share. When a step is unavailable, the rail says why.

## Repository map

| Path | What it is |
|---|---|
| `research/` | Research library: anatomy (29 notes), reconstruction (29), blender (22), community (15), ethics (4), each with an area README. Also `data/` (machine-readable tables), `sources/` (bibliographies) and `_raw/` (harvests, verification queues, engine requirement digests) |
| `docs/DESIGN.md` | The final design, synthesised from three competing proposals in `docs/design/` and a judge panel |
| `docs/wbs.json` | Work breakdown: specs, files, dependencies and acceptance tests, with integration notes added between packages |
| `docs/maintainer-tools.md` | How to build the MediaPipe scheme, calibrate it by render-and-detect, and refit the prior |
| `face3d/geometry` | Cameras (OpenCV convention, Blender conversion), RBF warps, Procrustes, symmetry planes |
| `face3d/solve` | PnP, Levenberg-Marquardt, bundle adjustment, robust schedule, noise model, focal, scale, mirror test, expression handling, camera models, observability and next-best view |
| `face3d/fit` | Staged template warp, silhouettes, contours, edge snapping, symmetry, per-vertex uncertainty, claims ledger |
| `face3d/mesh` | Mesh core, sparse matrices with CG, cotangent Laplacian, reduced deformer, rasteriser, Catmull-Clark limit stencils |
| `face3d/model` | Template registry, procedural CC0 head, landmark factor prior, conditional prior |
| `face3d/io`, `face3d/qa` | EXIF and HEIF readers, PNG, landmark files; photo quality checks |
| `face3d/texture` | Gated texture projection and blending |
| `face3d/handoff` | Shape-key stack with exact rebase, protect mask, topology guard |
| `face3d/pipeline` | Project file, cached stages, CLI, job-folder protocol |
| `face3d/testbed`, `face3d/eval` | Synthetic subjects, rigs, detector simulator, scenarios, scorecards, fault injection; alignment and coverage metrics |
| `blender_ext/face3d_likeness` | The Blender extension (GPL-3.0-or-later; all `bpy` access goes through `bridge.py`) |
| `tools/` | Extension builder, MediaPipe scheme builder and detector wrapper, scheme calibration, prior refit, template-kit builder |
| `tests/` | About 540 tests, a bpy stub, golden files (baseline scorecard v0, pipeline golden) |

## Licences

- **Engine and extension code:** GPL-3.0-or-later, for extensions.blender.org.
- **Bundled assets:** CC0 only. The default template is a procedural CC0 head.
- **Third-party models and datasets are never bundled.** This covers the MediaPipe weights, ANSUR II and FLAME 2023 Open (CC-BY-4.0, attribution required).
- **Non-commercial resources are excluded by design.** These are other FLAME versions, BFM, dlib-68 and InsightFace. The licensing notes are in [`research/ethics/licences-tos.md`](research/ethics/licences-tos.md).

## Ethics boundaries (built into the code)

- Photos only of yourself or of a person who consented. The consent record is checked per photo hash, and texture needs its own scope.
- Landmarks and fitted geometry are biometric data. They are session-only by default, and CI checks that no real-person data is committed.
- Never built: face matching or identification (1:N), URL or social-media importers, telemetry, and symmetrising or anonymising someone's face.

## What still needs doing offline

**WP-24** is the calibration programme, and it cannot run in a sandbox:

1. **Real CC0 template.** Replace the 3,458-vertex procedural head with a production CC0 base mesh, such as the Blender Studio Human Base Meshes. Two annotators place the landmarks.
2. **MediaPipe index map.** Verify the 478-point index semantics by render-and-detect. They are unverified today, and the iris L/R assignment is contested, so the engine resolves left and right geometrically.
3. **Calibration tiers 2-4.** Simulated phone renders, then a 3D-printed head shot with three or more phones, then consenting sitters with reference scans. These replace the provisional ("🆕/🧠") defaults with measured ones and refit the prior from ANSUR II.

The steps and tools are in `docs/wbs.json` (WP-24) and [`docs/maintainer-tools.md`](docs/maintainer-tools.md).
