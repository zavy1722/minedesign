# Research library

This library underpins the face3d engine and Blender extension. It covers how to turn photos of a consenting person into a likeness-accurate, anatomically sound, sculpt-ready 3D head in Blender. It has 94 topic notes in five areas. Each area has a README with core principles, quick-reference tables, a Blender checklist and the contradictions found between sources.

## Evidence badges

Every claim carries one badge:

| Badge | Meaning |
|---|---|
| ✅ | Verified: two or more independent sources agree |
| 📄 | Single source: usable with its population and method attached |
| 🧠 | Expert knowledge not yet source-checked: a provisional default, sanity range or heuristic, never a constant |
| ↔️ | Contested: sources disagree; the note gives both sides and a resolution rule |

The notes were drafted knowledge-first and then checked in two budgeted verification passes against web sources. Each note's *Verification log* sections record what each pass did for every claim it checked: confirmed it (with URLs), found it contested (with the competing figures), or could not confirm it (the badge stays 🧠). Many numeric norms are therefore still 🧠 or 📄. The engine treats them as provisional defaults with wide σ, never as constants.

## Reading paths

- **Sculpting a likeness by hand.** Read [community/likeness-mistakes](community/likeness-mistakes.md), [community/reference-photography-protocol](community/reference-photography-protocol.md) and [blender/sculpting-likeness-workflow](blender/sculpting-likeness-workflow.md). Then work through the [anatomy area](anatomy/README.md) feature by feature: [skull](anatomy/skull-osteology.md), then [soft tissue](anatomy/soft-tissue-thickness.md), [eye](anatomy/eye-region.md), [nose](anatomy/nose.md), [mouth](anatomy/mouth-lips-teeth.md) and [ear](anatomy/ear.md). Finish with [anatomy/face-perception-likeness](anatomy/face-perception-likeness.md), on what viewers actually use to recognise someone.
- **Matching photos in Blender.** Read [reconstruction/camera-perspective-distortion](reconstruction/camera-perspective-distortion.md), [blender/reference-camera-setup](blender/reference-camera-setup.md) and [reconstruction/smartphone-camera-pipeline](reconstruction/smartphone-camera-pipeline.md).
- **Understanding the engine.** Read [reconstruction/camera-pose-solving](reconstruction/camera-pose-solving.md), [reconstruction/multi-view-fitting](reconstruction/multi-view-fitting.md), [reconstruction/deformation-fitting-math](reconstruction/deformation-fitting-math.md), [anatomy/metric-3d-landmark-reference](anatomy/metric-3d-landmark-reference.md) and [reconstruction/validation-test-bed](reconstruction/validation-test-bed.md). Then read the design in [../docs/DESIGN.md](../docs/DESIGN.md).
- **Before you use someone's photos.** Read [ethics/consent-likeness-law](ethics/consent-likeness-law.md), [ethics/biometric-privacy](ethics/biometric-privacy.md) and [ethics/licences-tos](ethics/licences-tos.md).

## Machine-readable parts

- `data/*.json`: one file per note (`topic` plus `tables`), holding the note's numeric tables (norms, tissue depths, landmark definitions, priors) in machine-readable form.
- `sources/*.json`: one bibliography per note.
- `_raw/`: working material. It holds the web harvests, the verification queues for both passes, a digest, and `requirements_<area>.md` (the engine-facing requirements each area produced: priors with σ, formats, failure modes, licences). It also has the scripts that build the metric 3D landmark prior.

## Index

### Anatomy (28 notes) - [area README](anatomy/README.md)

How the face and head are built: skull, soft tissue, muscles, fat, ligaments, features, variation, ageing, and what makes a likeness read.

- [Facial aging mechanics](anatomy/aging-face.md)
- [Quantitative facial anthropometry norms (Farkas and successors)](anatomy/anthropometric-norms.md)
- [Craniofacial growth: child and adolescent faces](anatomy/child-growth.md)
- [Hard- and soft-tissue anthropometric landmarks](anatomy/craniometric-landmarks.md)
- [Cranial vault and back-of-head shape under hair](anatomy/cranium-under-hair.md)
- [External ear](anatomy/ear.md)
- [Eye, eyelids and orbit](anatomy/eye-region.md)
- [Psychology of face recognition and likeness](anatomy/face-perception-likeness.md)
- [Natural facial asymmetry](anatomy/facial-asymmetry.md)
- [Facial proportions, neoclassical canons and the golden-ratio myth](anatomy/facial-proportions-canons.md)
- [FACS action units and expression mechanics](anatomy/facs-expressions.md)
- [Facial fat compartments](anatomy/fat-compartments.md)
- [Forehead, brow ridge, temple and hairline](anatomy/forehead-brow-temple-hairline.md)
- [Forensic facial reconstruction rules (skull to face)](anatomy/forensic-reconstruction.md)
- [Mandible, chin and neck](anatomy/jaw-chin-neck.md)
- [Metric 3D mean landmark configuration and covariance](anatomy/metric-3d-landmark-reference.md)
- [Lips, mouth and dental support](anatomy/mouth-lips-teeth.md)
- [Muscles of the lower face, lips and chin](anatomy/muscles-lower-face.md)
- [Masseter, temporalis and the jaw line](anatomy/muscles-mastication-jaw.md)
- [Muscles of the mid face](anatomy/muscles-mid-face.md)
- [Muscles of the upper face](anatomy/muscles-upper-face.md)
- [Nose anatomy and morphology](anatomy/nose.md)
- [Craniofacial variation across human populations](anatomy/population-variation.md)
- [Sexual dimorphism of the face and skull](anatomy/sexual-dimorphism.md)
- [Skin thickness, wrinkles, pores and microdetail](anatomy/skin-wrinkles-microdetail.md)
- [Skull osteology that shapes the face surface](anatomy/skull-osteology.md)
- [SMAS and facial retaining ligaments](anatomy/smas-ligaments.md)
- [Facial soft-tissue thickness (forensic tissue depth tables)](anatomy/soft-tissue-thickness.md)

### Reconstruction (28 notes) - [area README](reconstruction/README.md)

How faces are recovered from images: cameras and perspective, landmarks, morphable models, fitting maths, texture, datasets, benchmarks and the 2025-2026 state of the art.

- [3D morphable models: survey](reconstruction/3dmm-overview.md)
- [Albedo, lighting and inverse rendering for faces](reconstruction/albedo-lighting-inverse-rendering.md)
- [Benchmarks and metrics for face reconstruction accuracy](reconstruction/benchmarks-metrics.md)
- [Focal length, subject distance and perspective distortion](reconstruction/camera-perspective-distortion.md)
- [Solving camera pose and intrinsics from face images](reconstruction/camera-pose-solving.md)
- [Commercial photo-to-head tools](reconstruction/commercial-head-tools.md)
- [Math for landmark-driven mesh fitting](reconstruction/deformation-fitting-math.md)
- [Reconstructing and sculpting the ear from photos](reconstruction/ear-reconstruction-sculpting.md)
- [Separating identity from expression](reconstruction/expression-neutralization.md)
- [Public 3D face scan datasets](reconstruction/face-scan-datasets.md)
- [Face, hair and skin segmentation for silhouettes and occlusion](reconstruction/face-segmentation-contours.md)
- [FLAME head model in depth](reconstruction/flame-model.md)
- [Generative / large reconstruction models for heads (2024-2026)](reconstruction/generative-3d-heads.md)
- [Reconstructing hair, eyes and teeth from images](reconstruction/hair-eyes-teeth-recon.md)
- [Face recognition embeddings as identity signals](reconstruction/identity-embeddings.md)
- [Facial landmark detectors](reconstruction/landmark-detection.md)
- [Verified landmark index tables and cross-convention correspondences](reconstruction/landmark-index-correspondence.md)
- [Monocular depth and surface normals for faces](reconstruction/monocular-depth-normals.md)
- [Multi-image and video 3DMM fitting](reconstruction/multi-view-fitting.md)
- [NeRF and Gaussian-splatting head avatars](reconstruction/neural-head-avatars.md)
- [Open-source end-to-end photo-to-3D-face pipelines](reconstruction/open-source-pipelines.md)
- [Phone video and depth-sensor capture as engine input](reconstruction/phone-video-depth-capture.md)
- [Photogrammetry of human heads](reconstruction/photogrammetry-heads.md)
- [Single-image 3D face reconstruction methods](reconstruction/single-image-regression.md)
- [Smartphone camera processing, metadata and lens calibration for face capture](reconstruction/smartphone-camera-pipeline.md)
- [State of the art 2025-2026 in 3D face reconstruction](reconstruction/sota-2025-2026.md)
- [Building a UV texture from photos](reconstruction/texture-extraction.md)
- [Ground-truth test bed and threshold calibration for the fitting engine](reconstruction/validation-test-bed.md)

### Blender (21 notes) - [area README](blender/README.md)

How to do it in Blender: camera matching, sculpt tools, shape keys, retopology, eyes, skin, hair, rigging, extension packaging and the bpy API.

- [Packaging as a Blender extension](blender/blender-extensions-packaging.md)
- [Blender add-ons for heads and faces](blender/blender-face-addons.md)
- [Running MediaPipe / OpenCV / ONNX inside Blender](blender/blender-python-ml-deps.md)
- [Blender sculpt mode feature set (4.x-5.x)](blender/blender-sculpt-features-5x.md)
- [Blender release status and roadmap as of late 2026](blender/blender-version-status-2026.md)
- [Blender Python API for procedural heads](blender/bpy-mesh-api.md)
- [Modeling and shading realistic eyes in Blender](blender/eyes-modeling-blender.md)
- [Face retopology and edge flow](blender/face-retopology.md)
- [Face rigging for a reconstructed head](blender/face-rigging.md)
- [KeenTools FaceBuilder for Blender in practice](blender/facebuilder-blender.md)
- [Guided workflow and accessibility for non-expert users](blender/guided-workflow-accessibility.md)
- [Hair in Blender for head reconstructions](blender/hair-blender.md)
- [Importing scans and reconstructions into Blender](blender/import-export-scans.md)
- [Bridges to MetaHuman, Character Creator, Daz](blender/metahuman-cc-bridges.md)
- [Open-licence template head kit for fitting and sculpting](blender/open-template-head-kit.md)
- [Matching photo lighting and verifying likeness renders](blender/portrait-lighting-compare.md)
- [Reference images and camera matching in Blender](blender/reference-camera-setup.md)
- [Blender portrait likeness sculpting workflow](blender/sculpting-likeness-workflow.md)
- [Shape keys and blendshape standards](blender/shapekeys-blendshapes.md)
- [Realistic skin shading in Blender](blender/skin-shading.md)
- [Projection painting and texturing heads in Blender](blender/texture-projection-painting.md)

### Community (14 notes) - [area README](community/README.md)

What practitioners on forums, YouTube, ArtStation, Polycount, Reddit and Instagram actually do, and the mistakes they warn about.

- [AI-assisted head creation: practitioner reviews](community/ai-assisted-sculpting.md)
- [Classic art-anatomy references for heads](community/art-anatomy-books.md)
- [ArtStation: likeness breakdowns and tutorials](community/artstation-likeness.md)
- [Curated resource lists and communities](community/awesome-lists-resources.md)
- [BlenderArtists forum knowledge on faces](community/blenderartists-forum.md)
- [Instagram and social media sculptors' tips](community/instagram-social-sculptors.md)
- [Common likeness mistakes and diagnostics](community/likeness-mistakes.md)
- [Polycount: likeness sculpting knowledge](community/polycount-likeness.md)
- [Reddit: face-from-photos problems and answers](community/reddit-face-from-photos.md)
- [How to shoot reference photos for 3D faces](community/reference-photography-protocol.md)
- [Cleaning scans and wrapping base topology](community/scan-cleanup-wrapping.md)
- [Traditional portrait sculpture methods](community/traditional-portrait-sculpture.md)
- [YouTube: face from photos / likeness in Blender](community/youtube-likeness-blender.md)
- [ZBrush likeness methods translated to Blender](community/zbrush-to-blender-likeness.md)

### Ethics and licences (3 notes) - [area README](ethics/README.md)

Consent, publicity and deepfake law, biometric privacy, and the licences of every model and dataset touched.

- [Biometric privacy law and face geometry](ethics/biometric-privacy.md)
- [Consent, right of publicity and deepfake law](ethics/consent-likeness-law.md)
- [Licences and platform terms](ethics/licences-tos.md)
