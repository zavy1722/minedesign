# Curated resource lists and communities

> GitHub "awesome" lists for 3D faces, 3DMMs, talking heads and Gaussian avatars are discovery indexes, not vetted catalogues. They give the paper, venue and code link, almost never the licence, weight terms, benchmark protocol or whether the code still installs, and many freeze when the maintainer graduates. Nearly every listed method reuses upstream assets from about a dozen labs, and most of those assets are licensed for non-commercial research. That licence, not the method's code licence, decides what an open-source add-on may ship. For artists the lasting resources are anatomy references (Anatomy For Sculptors, Complete Anatomy, the open Blender-native Z-Anatomy), licensed scan heads (3D Scan Store, Texturing.XYZ, Triplegangers) and searchable forums. No harvest or earlier draft existed for this topic, so everything below is expert knowledge awaiting verification, and every name, licence and status is time-sensitive.
>
> Evidence status: 0 ✅ / 0 📄 / 76 🧠 / 26 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Awesome lists: what they are and what they omit**
- **Origin.** The format comes from Sindre Sorhus's `sindresorhus/awesome` meta-list, which has inclusion rules. Most computer-vision paper lists are not part of it and follow no standard. 🧠
- **Lists I am fairly confident exist:** `MrNeRF/awesome-3D-gaussian-splatting`, `harlanhong/awesome-talking-head-generation`, `Kedreamix/Awesome-Talking-Head-Synthesis`. 🧠
- **Ambiguous names.** "awesome-3D-face", "awesome-3DMM" and "awesome-gaussian-avatars" each exist under several owners. Check which copy is maintained with a GitHub topic search sorted by recent updates. ↔️
- **What entries give:** title, venue and year, arXiv, project page, code. **What they rarely give:** code licence, weight licence, data licence, benchmark numbers with protocol, GPU needs, whether the code runs on current PyTorch and CUDA. 🧠
- **Inclusion is not endorsement.** Lists only grow: superseded methods stay and no negative results are added. Many entries are the authors' own pull requests. 🧠
- **Lists go stale fast.** Gaussian head avatars went from none before mid-2023 to dozens of papers by 2025. A list untouched for 12 months misses most of a research generation. 🧠
- **Leaderboards.** Papers with Code reportedly shut down in 2025. ↔️ NoW results live on MPI's RingNet project site and REALY results on its GitHub. 🧠
- **Start with surveys:** Zollhöfer et al. 2018, Egger et al. 2020, Morales et al. 2021, Tewari et al. 2020/2022. Use lists only for papers published after them. 🧠

**Labs and the assets everyone reuses** (Table 3)
- **The shared base.** Most listed methods rest on FLAME (MPI-IS), BFM (Basel), LSFM and 300-W (Imperial iBUG), LYHM and Headspace (York), FaceScape (Nanjing), MediaPipe (Google) and, for avatars, NeRSemble (TUM). 🧠
- **Commercial routes.** FLAME is licensed commercially through Meshcapade and BFM by agreement with Basel. Terms change, so check them first. ↔️
- **Issue trackers are the real forums.** The issue trackers of FLAME, DECA, MICA and 3DDFA_V2 hold most of the fitting lore: coordinate conventions, metre versus millimetre scale, landmark-embedding files and camera models. 🧠

**Code to read before writing a numpy fitter**
- **`patrikhuber/eos`** (Apache-2.0) fits a PCA model to landmarks and the jaw contour with a scaled-orthographic camera and a linear shape solve. It is the cleanest small design to study. 🧠
- **FLAME fitters:** `Rubikplayer/flame-fitting` (chumpy; fits landmarks and scans), `soubhiksanyal/FLAME_PyTorch`, `HavenFeng/photometric_optimization`. 🧠
- **Landmark and regression code:**
  - `cleardusk/3DDFA_V2` (MIT; ONNX/CPU paths);
  - `1adrianb/face-alignment` (BSD-3; 68 points, 2D or 3D);
  - MediaPipe Face Landmarker (Apache-2.0; 478 points on CPU);
  - menpo/menpofit/menpo3d (iBUG; BSD). 🧠
- **dlib's 68-point model** has Boost-licensed code, but it was trained on 300-W, whose terms exclude commercial use. 🧠

**Communities**
- **Blender:**
  - Blender Artists (`community/blenderartists-forum.md`);
  - Blender Stack Exchange (searchable, CC BY-SA, best for `bpy`/`mathutils`);
  - the developer forum and blender.chat for API changes;
  - unofficial Discord servers. 🧠
- **Likeness critique:** ZBrushCentral (Top Row), Polycount (character art, sketchbooks), ArtStation, r/ZBrush, r/blender, r/photogrammetry (`community/reddit-face-from-photos.md`). 🧠 CGSociety's forums reportedly closed in 2023–24. ↔️
- **Vendor forums** (KeenTools, Reallusion, Epic MetaHuman, Agisoft, Capturing Reality) are the place for tool bugs. 🧠
- **Research channels:** GitHub issues; Hugging Face Spaces (try a method before installing it); arXiv cs.CV/cs.GR; paper-digest accounts on X and Bluesky (part of the field moved to Bluesky from late 2024 ↔️).
- **Teaching:** FlippedNormals, Gnomon Workshop, Scott Eaton, Proko, Anatomy For Sculptors (`community/art-anatomy-books.md`). 🧠
- **Discord** is fast, but search engines don't index it, history vanishes and access is gated. Take hints from it; never cite it. 🧠

**Scan, texture and photo references**
- **3D Scan Store** (Ten24, UK) sells cleaned, retopologised heads, expression sets and multi-angle photo sets under a commercial licence, with occasional free samples. 🧠
- **Texturing.XYZ** sells multichannel displacement (secondary, tertiary and micro detail packed into RGB) and VFace full-head UDIM sets (`blender/skin-shading.md`). 🧠
- **Triplegangers** sells scanned heads, including expression sets. 🧠
- **The "Lee Perry-Smith" head** (Infinite-Realities) is a free head scan used in the three.js examples 🧠, believed to be CC BY 3.0. ↔️
- **Digital Emily 2.0** (USC ICT's "Wikihuman" release): terms unclear. ↔️
- **Smithsonian Open Access 3D** (CC0, 2020) includes the Lincoln life masks: real-scale faces cast from life. 🧠
- **Sketchfab:** a Download button is not a commercial licence, so filter by licence. Its store moved into Epic's Fab, launched in October 2024. ↔️
- **Photo turnarounds** (3d.sk, Anatomy 360, Ten24) show one sitter in one session from many angles. That is ideal solver test data, but the licences rarely allow ML or test use. 🧠
- **MetaHuman** is free; a 2025 licence update reportedly allows use outside Unreal. ↔️

**Anatomy references**
- **Complete Anatomy** (3D4Medical, owned by Elsevier since 2019) gives a layered skull, muscles and attachments. It is a subscription product and its EULA forbids extracting meshes. 🧠
- **Zygote Body** (from Google Body, 2010), **BioDigital Human** and **Visible Body:** browser and app atlases; free tiers vary. 🧠
- **Anatomy For Sculptors** (Uldis Zarins with Sandis Kondrats, Riga) offers *Anatomy for Sculptors* (2014), *Anatomy of Facial Expression*, *Form of the Head and Neck*, free infographics and paid 3D models. The approach is artist planes, not dissection. 🧠
- **Z-Anatomy** is an open atlas shipped as a .blend file, built from BodyParts3D and other open data, reportedly CC BY-SA 4.0. ↔️ It is the only free Blender-native skull-and-muscle set I know. 🧠
- **BodyParts3D** (DBCLS, Japan) is CC BY-SA 2.1 Japan. 🧠
- **CT-derived skulls:** NIH 3D (formerly NIH 3D Print Exchange), MorphoSource, University of Dundee models on Sketchfab, NLM Visible Human. The licence differs per item. 🧠
- **No variance.** Each atlas is one specimen or an idealised composite, with no population variance. 🧠

## Numbers & reference tables

**Table 1: Upstream face models and datasets** (counts approximate; verify licences)

| Asset (lab) | Population / size | Geometry | Licence posture | Badge |
|---|---|---|---|---|
| FLAME (MPI-IS, 2017; 2020/2023 releases) | identity from ~3,800 CAESAR scans | 5,023 vertices; 300 shape + 100 expression components | non-commercial research; "FLAME 2023 Open" possibly CC BY 4.0 | ↔️ |
| BFM 2009 (Basel) | 200 adults (100 f / 100 m), mostly European | 53,490 vertices; 199 components | non-commercial, registration | 🧠 |
| BFM 2017 (Basel) | same identity base plus an expression model | face and full-head variants | non-commercial | 🧠 |
| LSFM (Imperial) | ~9,700 subjects | face | non-commercial | 🧠 |
| LYHM / Headspace (York) | ~1,200 (model) / ~1,500 (dataset) | full head with cranium | academic | ↔️ |
| FaceWarehouse (Zhejiang) | 150 people aged 7–80, 20 expressions | Kinect RGB-D | research | 🧠 |
| FaceScape (Nanjing) | 938 subjects × 20 expressions ≈ 18,700 models, mostly East Asian | textured, uniform topology | research, non-commercial | 🧠 |
| ICT-FaceKit (USC ICT) | ~100 identity, ~53 expression shapes | ARKit-like | MIT | ↔️ |
| NoW (MPI-IS) | 100 subjects, ~2,050 images | hidden-truth scans | research | 🧠 |
| NeRSemble (TUM) | >220 subjects; 16 cameras, ~73 fps, ~7 MP | multi-view video | on request, non-commercial | ↔️ |
| Ava-256 (Meta) | 256 subjects | multi-view capture | non-commercial | ↔️ |
| FFHQ (NVIDIA) | 70,000 images at 1024² | 2D | CC BY-NC-SA 4.0 dataset; images licensed individually | 🧠 |
| MPFB2 / MakeHuman | synthetic targets | parametric head and body | CC0 assets, GPL code | 🧠 |

**Table 2: Landmark and topology schemes**

| Scheme | Points | Notes | Badge |
|---|---|---|---|
| iBUG 300-W / dlib | 68 (2D) | the 17 jaw points slide along the contour | 🧠 |
| WFLW | 98 (2D) | ~10,000 images | 🧠 |
| AFLW2000-3D | 68 (3D) | 2,000 images; fitted, not scanned, ground truth | 🧠 |
| MediaPipe Face Mesh | 468; 478 with irises | Apache-2.0, CPU | 🧠 |
| ARKit face | 1,220 vertices; 52 blendshapes | Apple devices only | 🧠 |
| FLAME landmark embedding | 51 static + 17 dynamic contour | barycentric on 5,023 vertices | 🧠 |
| Dense landmarks (Wood et al. 2022) | ~700 | synthetic training data; weights not open, as far as I know | ↔️ |

**Table 3: Labs to watch** (people listed are not exhaustive)

| Lab | People | Assets and methods | Badge |
|---|---|---|---|
| MPI-IS Perceiving Systems | Michael J. Black, Timo Bolkart, Radek Daněček | FLAME, RingNet/NoW, DECA, EMOCA, TEMPEH | 🧠 |
| TU Munich Visual Computing & AI | Matthias Nießner, Simon Giebenhain, Tobias Kirschstein, Shenhan Qian | NPHM, NeRSemble, GaussianAvatars, VHAP, Pixel3DMM | 🧠 |
| Justus Thies (now TU Darmstadt) | Wojciech Zielonka | MICA, metrical-tracker, INSTA | 🧠 |
| Univ. Basel Graphics & Vision | Thomas Vetter, Bernhard Egger (alumnus) | BFM, Scalismo, probabilistic fitting | 🧠 |
| Imperial College iBUG | Stefanos Zafeiriou, Jiankang Deng | 300-W, LSFM, GANFit, AvatarMe, ArcFace | 🧠 |
| Univ. York | Nick Pears, William Smith, Hang Dai | Headspace, LYHM | 🧠 |
| Disney Research Zurich | Thabo Beeler, Derek Bradley | passive capture, anatomically constrained models | 🧠 |
| USC ICT | Paul Debevec (alumnus) | Light Stage, Digital Emily, ICT-FaceKit | 🧠 |
| Meta Reality Labs Pittsburgh | Yaser Sheikh, Jason Saragih, Shunsuke Saito | Codec Avatars, Multiface, Ava-256, URAvatar | 🧠 |
| Microsoft Cambridge | Erroll Wood, Tadas Baltrušaitis | FaceSynthetics, dense landmarks, OpenFace | 🧠 |
| CASIA | Xiangyu Zhu, Jianzhu Guo, Zhen Lei | 3DDFA/3DDFA_V2, 300W-LP, AFLW2000-3D | 🧠 |

**Table 4: Resource triage** (costs change)

| Resource | Cost | Can ship in a GPL add-on? | Best use | Badge |
|---|---|---|---|---|
| Z-Anatomy / BodyParts3D | free | yes with attribution, if BY-SA (BY-SA 4.0 → GPLv3 one-way compatible) | skull/muscle underlay, region labels | ↔️ |
| Smithsonian life masks | free, CC0 | yes | real-scale test surfaces | 🧠 |
| Lee Perry-Smith head | free, CC BY? | probably, with attribution | regression test head | ↔️ |
| 3D Scan Store, Triplegangers | paid per asset | no | plane/volume reference, wrap practice | 🧠 |
| Texturing.XYZ | paid per pack | no | micro-detail after likeness | 🧠 |
| Complete Anatomy, Visible Body | subscription | no (EULA) | layered study, attachments | 🧠 |
| Anatomy For Sculptors | paid; infographics free | no | planes, expression | 🧠 |
| 3d.sk, Anatomy 360 | paid | no | multi-angle photo reference | 🧠 |
| MetaHuman | free (EULA) | no | rig and topology reference | ↔️ |

**Table 5: List-health heuristics** (my thresholds, not a standard)

| Signal | Healthy | Stale | Badge |
|---|---|---|---|
| Last commit | ≤ 3 months | > 12 months | 🧠 |
| Newest venue covered | 2026 (CVPR/SIGGRAPH) | ≥ 2 years old | 🧠 |
| Open unanswered PRs | < 10 | > 30 | 🧠 |
| Licence/code-status columns | present | absent (the norm) | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Skull underlay.** Append the Z-Anatomy skull, or a CT skull from NIH 3D or MorphoSource, into its own collection with wire display and In Front. Scale it uniformly so that bizygomatic width and nasion–menton height match your solved landmarks minus soft-tissue thickness (`anatomy/skull-osteology.md`, `anatomy/craniometric-landmarks.md`). Use it to place the orbits, zygomatic arches, gonial angle and mastoid. Never sculpt the skull to fit the face.
2. **Scan heads are for planes and volume, not likeness.** A licensed 3D Scan Store head beside your sculpt quickly shows a shallow cranium, thin neck or flat cheek. Starting from a scan pulls the result toward that person.
3. **Work in order.** Proportions and depth come from the solved cameras, planes from anatomy references, and micro-detail (Texturing.XYZ or scan displacement on Multires) last, only after the overlay matches through every camera.
4. **Triage list entries before installing.** Note for each:
   - input (single image, multi-view or video);
   - camera model (weak-perspective or perspective);
   - output (FLAME/BFM, own topology, or splats);
   - whether it gives metric scale;
   - weight and asset licences;
   - whether it needs CUDA;
   - date of the last commit.

   Run methods outside Blender and import OBJ/PLY plus landmarks as an initialiser. Splat avatars (GaussianAvatars, NPGA) cannot be sculpted; their FLAME tracking stage (VHAP, metrical-tracker) is the reusable part.
5. **Asking communities.** Post wireframes, overlays and residual heat-maps, not the sitter's photos, unless the sitter agrees. Ask concrete questions ("ears too high in view 3, overlay attached"). Use Stack Exchange for `bpy`, vendor forums for tool bugs, and Polycount or ZBrushCentral for likeness critique.
6. **Keep provenance** for every asset: source, licence, version, date, attribution.

| Symptom | Cause | Fix |
|---|---|---|
| Client project contains FLAME- or BFM-derived geometry | research licence ignored | refit on a CC0 or MIT template |
| Repo from a list won't install | pinned old PyTorch/CUDA, pytorch3d build | container, ONNX export or CPU fork; or drop it |
| Sketchfab model used commercially | download ≠ licence | read and store the licence field |
| Mesh exported from an anatomy app | EULA breach | Z-Anatomy or BodyParts3D, with attribution |
| Likeness drifts toward the reference scan | scan used as base mesh | neutral template; keep the scan side-by-side only |
| Forum fix fails | thread predates the current version | check the post date (`blender/blender-version-status-2026.md`) |

## Algorithmic implications

- **Asset registry.** Ship `assets.toml` with one row per external file: `name`, `version`, `sha256`, `spdx_licence`, `commercial_ok` (true / false / unknown), `attribution`, `source_ref` and `retrieved`. 🧠
  - Bundle nothing whose `commercial_ok` is false or unknown.
  - Load FLAME and BFM only from paths the user downloaded, and warn when the project is flagged commercial (same guard as `reconstruction/identity-embeddings.md`).
- **Permissive default template.** Use the MPFB2 topology (CC0), or ICT-FaceKit once its licence is verified. Research models plug in as optional priors through one adapter: `mean`, `basis`, `sigma`, `landmark_embedding` (face index plus barycentric weights). 🧠
- **Landmark adapters.** Store every Table 2 scheme as barycentric embeddings on the working template. Ship a 68↔478 correspondence so that iBUG, MediaPipe and FLAME points share one `levenberg_marquardt` residual. Jaw contour points slide along the silhouette normal only. 🧠
- **Single-specimen atlases are weak priors.** Use an atlas skull for region masks, landmark definitions and initial placement, never as variance. If it enters the energy at all, use a similarity-aligned skull-to-template term with σ ≈ 4–6 mm, and let the soft-tissue-thickness tables carry depth. 🧠
- **Scan heads as shape priors:** σ ≈ 3–5 mm per vertex after `umeyama` alignment (as for AI meshes in `community/reddit-face-from-photos.md`). Never treat them as landmark ground truth. 🧠
- **Population bias.** BFM and FLAME skew European-descent, and FaceScape is mostly East Asian. Make the prior mean selectable. When ancestry lies outside the prior's population, widen σ by about 1.5×; that factor is a guess, so tune it on held-out views. ↔️
- **Synthetic test harness.** Render CC0 or CC BY heads (Smithsonian masks, MPFB2 characters, Lee Perry-Smith once confirmed) in Blender through 3–8 cameras with known focal length (24–135 mm equivalent), distance (0.4–3 m) and yaw (±90°). Assert that the solver recovers the cameras. 🧠
  - Suggested targets: focal error < 5 % and rotation error < 2° when the views span at least 60° of yaw.
  - Score the shape with the NoW protocol: rigid alignment on 7 points, then vertex-to-surface distance in mm.
- **Offline by design.** Extensions must declare the `network` permission. Ship no scraping and no "new methods" feed; resource links belong in the docs. 🧠
- **Re-verify upstream licences every release.** FLAME, MetaHuman and Sketchfab/Fab terms all changed in 2023–25. ↔️

## Disagreements, myths & open questions

- **Myth: "on an awesome list = vetted".** Lists are self-submitted indexes that check neither reproducibility nor licences. 🧠
- **Myth: "stars = quality".** Stars follow demo videos. NoW and REALY errors and issue-tracker health are better signals. 🧠
- **Myth: "free download = free use".** It is not: Sketchfab models, GitHub weights (InsightFace, dlib-68) and research datasets all carry terms. 🧠
- **FLAME 2023 "Open":** is it CC BY 4.0, and does it include the expression basis? ↔️
- **MetaHuman 2025 EULA:** does "use outside Unreal" cover test data for an open-source tool? ↔️
- **Unverified closures and moves:** Papers with Code shutting down, CGSociety closing, and the Sketchfab store moving to Fab are all reported but not confirmed. ↔️
- **Medical atlases against artist references.** Medical apps are right about attachments but show lean, idealised surfaces; artist sites stylise plane breaks and fat pads. Neither gives variance; anthropometric tables do (Farkas). ↔️
- **Discord against forums.** Discord answers faster, forums keep knowledge. Practical lore (FaceBuilder tricks, scan cleanup) increasingly lives where it cannot be searched. ↔️
- **Open questions:**
  - Is any list maintained with licence columns?
  - Is there any multi-subject head-scan dataset that permits commercial use? I know of none.
  - Which "awesome-3DMM" and "awesome-gaussian-avatars" repositories are active in late 2026?

## Sources

No harvested sources or earlier draft exist for this topic, so no URLs are cited. Repository names (`owner/repo`) are from memory and need checking.

**Further reading (by name, not yet linked)**
- Blanz & Vetter, "A Morphable Model for the Synthesis of 3D Faces", SIGGRAPH 1999
- Paysan et al., Basel Face Model, 2009
- Li, Bolkart, Black, Li, Romero, FLAME, "Learning a model of facial shape and expression from 4D scans", SIGGRAPH Asia 2017
- Zollhöfer et al., "State of the Art on Monocular 3D Face Reconstruction, Tracking, and Applications", Eurographics STAR 2018
- Egger et al., "3D Morphable Face Models — Past, Present, and Future", ACM TOG 2020
- Morales, Piella, Sukno, "Survey on 3D face reconstruction from uncalibrated images", Computer Science Review 2021
- Tewari et al., "State of the Art on Neural Rendering" (2020); "Advances in Neural Rendering" (2022)
- Booth et al., Large Scale Facial Model (LSFM), CVPR 2016 / IJCV 2018
- Dai, Pears, Smith, Duncan, Liverpool-York Head Model, ICCV 2017
- Cao et al., FaceWarehouse, IEEE TVCG 2014
- Yang et al., FaceScape, CVPR 2020
- Sagonas et al., 300 Faces in-the-Wild (300-W), 2013/2016
- Kartynnik et al., "Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs", 2019
- Wood et al., "Fake It Till You Make It", ICCV 2021; "3D Face Reconstruction with Dense Landmarks", ECCV 2022
- Qian et al., GaussianAvatars, CVPR 2024; Kirschstein et al., NeRSemble, SIGGRAPH 2023
- Huber et al., "A Multiresolution 3D Morphable Face Model and Fitting Framework" (eos), VISAPP 2016
- Zarins & Kondrats, *Anatomy for Sculptors: Understanding the Human Figure*, 2014
- Farkas, *Anthropometry of the Head and Face*, 1994
