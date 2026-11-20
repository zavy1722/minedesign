# Building a UV texture from photos

> A photo texture is built by rasterising the head's UV layout into per-texel 3D positions and normals, projecting each texel into every solved camera, keeping samples that are visible, front-facing and away from occlusion edges, matching colour across photos, and combining them. The seams that matter are **view-transition seams on the surface**, not UV seams. They come from geometric misregistration (a normal-direction error δn shifts a sample by ≈ δn·tan θ) and from exposure, white-balance and specular differences between views. The robust recipe is per-image gain compensation in linear RGB; then either best-view selection with seam levelling or two-band blending (low frequencies averaged widely, detail taken from one view); then hole filling ranked by honesty: mirror, harmonic/push-pull, statistical albedo, and only last generative (GAN or diffusion) inpainting, masked and recorded in a confidence map. Useful texel density is capped by photo sampling (about 0.05–0.15 mm/px for good capture). No harvest or prior draft exists for this topic, so every item is expert knowledge or arithmetic.
>
> Evidence status: 0 ✅ / 1 📄 / 59 🧠 / 17 ↔️ — 🧠 items are queued for web verification.

## Key facts

**Projection**
- **UV G-buffer first.** Rasterise each triangle in UV space; per texel (centre at (i+0.5)/N) store face id, barycentrics, interpolated 3D position and smoothed normal. Texels outside charts are gutter 🧠
- **Project forward, texel → pixel.** This is exact, including lens distortion; `Camera.project` already applies k1, k2. If the solver used a richer model (tangential, k3, fisheye), undistort the photos in that tool and use its pinhole intrinsics 🧠
- **Footprint-aware sampling.** A texel of pitch p at depth z covers ≈ p·f/z px, stretched by 1/cos θ along the tilt. Bilinear sampling is fine up to about 1–2 px; beyond that, sample pyramid level log₂(footprint) or stubble, brows and pores alias into moiré 🧠
- **Resolution is capped by the photos.** Texels finer than the best view's ground sample distance (GSD) are upsampled, not detailed (Table 1; camera GSDs in `reconstruction/photogrammetry-heads.md`) 🧠

**Visibility and occlusion**
- **Three tests per texel per view:** in frame (with a margin), front-facing (angle θ between normal and view ray below θ_max), and a depth test against a z-buffer of the same mesh rendered from that camera, with tolerance ε 🧠
- **ε must exceed the geometric error:** about 0.5–1 mm for a scan, 2–5 mm for a landmark-fitted template. Too small gives speckled holes; too large lets the side of the nose take cheek colour, and vice versa 🧠
- **Occlusion edges are wrong first.** Near silhouettes and depth discontinuities (nose side, alar crease, ear, jaw over neck, upper lid), small pose or shape errors sample the occluder. Erode visibility about 3–10 source px, or ramp weights over 1–3 mm of surface 🧠
- **Things not in the mesh still occlude:** hair, lashes, glasses, earrings, collars, hands. Give face-parsing labels other than skin (eyes, inner mouth, hair, clothes) weight 0 for the skin layer; dilate hair masks a few px 🧠
- **Non-rigid differences between views** (blinks, lip seal, gaze, brow) ghost eyelids and lip lines; cull the view *per region*, not globally 🧠

**Weighting**
- **Typical weight:** w = vis · cosᵖθ · s(footprint) · m_semantic · e_edge, with p = 1–4 ↔️. Down-weighting grazing views also tracks the 1/cos θ stretch and specular growth (Table 2) 🧠
- **Skin specular** is about 2.8% at normal incidence (IOR ≈ 1.4) and rises steeply toward grazing (Schlick: ≈15% at 70°, ≈25% at 75°). Highlights move with the view, so with ≥3 views a robust per-texel statistic (median, or a lower percentile after gain matching) suppresses them 🧠
- **Sharpness-aware quality:** Waechter et al. (2014) score a view by image-gradient magnitude integrated over the projected face (favouring close, sharp views) and drop photo-inconsistent views that show a transient occluder 🧠
- **Misregistration is geometric:** Δs ≈ δn·tan θ. Two views at ±45° disagree by ≈2δn, so δn = 1 mm at 0.067 mm/px gives a ≈30 px ghost (Table 3). Weighted averaging over a template-only fit (2–5 mm error) doubles brows, lip lines and lid creases 🧠

**Blending and seams**
- **Weighted average** is seam-free but blurs and ghosts; **winner-take-all or MRF selection** is sharp but shows brightness steps at label boundaries 🧠
- **Lempitsky & Ivanov (2007)** label faces by graph cut (view quality + colour agreement along seams). **Waechter et al. (2014)** add global colour levelling (a per-vertex additive correction solved by least squares along seam edges) and local Poisson editing on a narrow seam strip (about 20 px) 🧠
- **Multiband** (Burt & Adelson 1983; Brown & Lowe 2007): blend each Laplacian level with weights smoothed at that level's scale, using 4–6 bands with nearly binary masks in the finest band. In an atlas, pyramids cross chart borders, so pad charts by push-pull before every level 🧠
- **Poisson (gradient domain):** take gradients from the selected view and solve for colour, which absorbs low-frequency offsets. Across UV cuts it needs a seam-aware Laplacian (Prada et al. 2018), otherwise it makes new seams 🧠
- **Two-band on the surface** (recommended for the engine): low frequency as a per-vertex weighted mean, shared by both sides of every UV seam; high frequency = best view's (image − its own low-pass). This is seam-free by construction and keeps pores from one view 🧠

**Colour consistency**
- **Causes:** exposure, white balance (WB), camera tone curves, vignetting (often 0.5–1.5 stops at the corners wide open), lighting that moves when the sitter rotates, and specular ↔️
- **Work in linear RGB.** Averaging sRGB-encoded values darkens transitions and biases gains 🧠
- **Gain compensation:** log I(v,k) = log g_v + log a_k over texels k seen by several views v. Solve by robust least squares with mean log g = 0; per channel, or a 3×3 matrix per image, plus a per-lens radial vignetting polynomial 🧠
- **A 24-patch colour chart** in one frame per lighting set lets a 3×3 linear matrix normalise the camera. Typical post-correction mean ΔE2000 is about 1.5–3 ↔️
- **Photometric pose refinement** (Zhou & Koltun 2014, colour map optimisation) helps landmark-solved cameras; never let it move SfM cameras 🧠

**Completion (inpainting)**
- **Usually unseen:** under the chin, nostril interiors, ear backs, scalp under hair, inner lips, inner canthi and, unless shot, the occiput 🧠
- **Rank fills by honesty:** (1) mirror via the template's symmetric UV map, Poisson-matched; (2) harmonic or push-pull for small holes; (3) PatchMatch for texture-like areas (neck, scalp); (4) statistical albedo (BFM, FLAME, AlbedoMM) for low frequency; (5) GAN (UV-GAN 2018, OSTeC 2021) or diffusion (Relightify 2023, TEXTure 2023, Paint3D 2024, Hunyuan3D-Paint) last 🧠
- **Generative fills invent identity marks** (moles, freckles, scars, pigment asymmetry). Never overwrite observed texels; restrict to confidence below about 0.2 with a feathered mask ↔️
- **Mirror fill copies marks and lighting.** Mirror only the low band plus generic texture, not unique marks 🧠
- **Bias:** statistical albedo models and learned de-lighters are trained mostly on lighter skin (BFM 2009: 200 mostly European adults, `reconstruction/single-image-regression.md`) and can lighten or grey darker skin ↔️

**De-lighting**
- **Cross-polarisation removes surface specular only.** Shading, ambient occlusion and subsurface blur remain (`blender/skin-shading.md`) 🧠
- **Spherical-harmonic (SH) de-lighting:** 9 coefficients per channel represent Lambertian irradiance closely (Ramamoorthi & Hanrahan 2001). Estimate them from texture + normals under a low-variance-albedo assumption, then divide. The paper reports about 1% average error for 9 parameters [3] 📄
- **Divide only part of the AO** (AO^γ, γ ≈ 0.3–0.6): skin's subsurface scattering and interreflection fill creases, so full division over-brightens nasolabial folds and orbits ↔️
- **The high-pass "de-light" is a myth:** it also removes real low-frequency albedo (cheek flush, under-eye pigment, beard shadow) 🧠
- **Double diffusion:** photo albedo already contains subsurface blur, so Random Walk SSS on top reads slightly soft or waxy. A mild unsharp mask (radius ≈ 0.5–1 mm) is a common, contested fix ↔️
- **Tools** (time-sensitive): Agisoft's free stand-alone Texture De-Lighter (free and stand-alone confirmed [4]; it needs rough brush strokes marking lit and shadowed areas and is tuned for 8-bit JPEG-compressed textures [4]); Unity's De-Lighting tool (2017, likely unmaintained; unverified) ↔️

## Numbers & reference tables

**Table 1 — Texel pitch by map size** (70% UV fill; head + neck ≈ 0.16 m², face alone ≈ 0.04 m²; arithmetic)

| Map | Whole head, mm/texel | Face on own tile, mm/texel | Texels used | float32 RGB layer | Badge |
|---|---|---|---|---|---|
| 1K | 0.47 | 0.23 | 0.7 M | 13 MB | 🧠 |
| 2K | 0.23 | 0.12 | 2.9 M | 50 MB | 🧠 |
| 4K | 0.12 | 0.058 | 11.7 M | 201 MB | 🧠 |
| 8K | 0.058 | 0.029 | 47 M | 805 MB | 🧠 |

Match to capture: a 24 MP full-frame camera framing 400 mm gives 0.067 mm/px; a 12 MP phone gives 0.099 mm/px nominal, ≈0.14–0.2 effective ↔️. So use 4K whole-head for phones, 8K (or a 4K face tile) for ≥24 MP 🧠.

**Table 2 — Incidence angle effects** (arithmetic; Schlick Fresnel with F₀ = 0.028)

| θ | Stretch 1/cos θ | cos θ | cos²θ | cos⁴θ | Specular F | Badge |
|---|---|---|---|---|---|---|
| 0° | 1.00 | 1.00 | 1.00 | 1.00 | 0.028 | 🧠 |
| 30° | 1.15 | 0.87 | 0.75 | 0.56 | 0.028 | 🧠 |
| 45° | 1.41 | 0.71 | 0.50 | 0.25 | 0.030 | 🧠 |
| 60° | 2.00 | 0.50 | 0.25 | 0.063 | 0.058 | 🧠 |
| 70° | 2.92 | 0.34 | 0.12 | 0.014 | 0.15 | 🧠 |
| 75° | 3.86 | 0.26 | 0.067 | 0.005 | 0.25 | 🧠 |

**Table 3 — Sample shift from a normal-direction geometry error, Δs = δn·tan θ** (px at 0.067 mm/px; arithmetic)

| δn (typical source) | θ = 15° | 30° | 45° | 60° | Badge |
|---|---|---|---|---|---|
| 0.5 mm (scan) | 0.13 mm / 2 px | 0.29 / 4 | 0.50 / 7 | 0.87 / 13 | 🧠 |
| 1 mm (good multi-view fit) | 0.27 / 4 | 0.58 / 9 | 1.00 / 15 | 1.73 / 26 | 🧠 |
| 3 mm (template-only fit) | 0.80 / 12 | 1.73 / 26 | 3.00 / 45 | 5.20 / 78 | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Freeze UVs first.** Project only onto the final layout. Put seams behind the ears, along the hairline, under the chin and down the back of the neck, never through eyes, lips or nose. In the UV editor, Overlay ▸ Display Stretch should show no face over about 25% area stretch (`blender/skin-shading.md`).
2. **Camera gate.** Import cameras with `to_blender_camera` (lens, sensor fit HORIZONTAL, shift x/y, render resolution = photo size). Set each photo as that camera's background image. Inner canthi, alar base, mouth corners, tragus and jawline must sit within about 1–2 px of the wireframe; otherwise fix the fit first or the texture ghosts (Table 3; `blender/reference-camera-setup.md`).
3. **Prepare photos.** Use a separate texture pass under flat light, cross-polarised if possible, with manual exposure and WB and a chart in the first frame. Develop RAW to 16-bit with chart and vignetting correction, no sharpening, light noise reduction. Undistort if the lens model exceeds k1, k2. Blender has no camera distortion.
4. **Project.**
   - **Recommended:** run the engine (below); Blender only loads `albedo.exr` (Linear) and `confidence.png` (Non-Color).
   - **Pure Blender, small jobs:** subdivide to edges ≤2–3 mm (the UV Project modifier interpolates affinely within a face). Per camera, make a duplicate with a UV Project modifier (projector = camera, aspect = image aspect) and an Emission material reading the photo through that UV map, then bake Emit into the main UV (Cycles, margin 16 px, margin type Extend or Adjacent Faces; 16 px is the documented default and both types exist [1]). For the weight, put a point light at the camera centre (radius 0, shadows on) and bake Diffuse ▸ Direct on a white material: that gives vis·cos θ/d², with true occlusion. Combine the layers outside Blender.
   - **Manual:** stencil or projection paint (Image ▸ Apply Camera Image) per view, with painted masks.
5. **Inspect** the confidence overlay, view-transition seams (cheek, temple, under the nose), lid margins and nose highlights.
6. **Order of operations:** colour-match → blend → fill → de-light → optional mild sharpen → save. Base Color is sRGB for 8/16-bit PNG and Linear for EXR. Keep confidence and best-view maps as Non-Color.
7. **Use it honestly for sculpting.** A projected photo makes wrong geometry look right in the front view. Judge form in matcap and profile first (`community/ai-assisted-sculpting.md`). Conversely, doubled brows or lip lines in the projection are a *diagnostic*: the geometry is wrong exactly there.

**What goes wrong**

| Symptom | Cause | Fix |
|---|---|---|
| Doubled brows, lip line, lid crease | misfit (δn·tan θ) or expression change | fix the fit; selection or two-band; cull view per region |
| Brightness steps | exposure, WB or vignetting differences | gain compensation in linear RGB; levelling |
| Nose colour on cheek, or vice versa | ε too large; no edge erosion | erode 3–10 px; ε ≈ 2σ geometry |
| Speckled holes | ε too small; noisy normals | raise ε; smooth normals |
| Hair painted on forehead | hair not in mesh | parsing mask, dilated |
| White blotches on nose and forehead | specular | cross-polarise; robust median; lower θ_max |
| Blurry despite 8K | beyond GSD, JPEG, phone denoise, averaging | size to Table 1; RAW; selection |
| Moiré on stubble | bilinear sampling of large footprints | pyramid sampling |
| Dark lines at UV seams | no gutter, mip bleed | 16 px margin at 4K |
| Waxy in Cycles | double diffusion; residual shading | de-light; mild sharpen |
| Mole on both cheeks | mirror fill | mirror the low band only; mask marks |

## Algorithmic implications

Proposed module `face3d/texture/`, numpy-only, built on `Mesh` (`uvs`, `face_uvs`) and `Camera` 🧠:

- `uv_gbuffer(mesh, size)`: rasterise UV triangles with the same fan triangulation as `Mesh.triangles()`; return face id, barycentrics, position and normal per texel.
- `zbuffer(mesh, cam, scale)`: depth raster at ≈1,000–2,000 px wide (enough for visibility), sampled at texel projections with tolerance ε.
- `view_weights(...)`, `solve_gains(...)`, `blend(mode="two_band"|"multiband"|"select_poisson"|"average")`, `fill(order=("mirror","harmonic","patch","model"))`, `delight(sh_order=2, ao_gamma=0.5)`.
- **Outputs:** linear float32 albedo, confidence ∈ [0,1], best-view index, a per-texel source flag (observed / mirrored / harmonic / patch / model / generated) and a cross-view variance map, which doubles as a photometric residual for the shape fit (only after gain matching).
- **Template masks:** eye, inner-mouth, nostril and scalp vertex groups become texel masks; a symmetric vertex map becomes the mirror texel map.
- **Memory:** stream views; keep the top 3 views per texel and resample in a second pass; tile at 8K.
- **Tests:** render a known texture through `face3d/synthetic.py` cameras with random gains and ±1 mm shape noise; require gains within 2% and no nose colour on nose-occluded cheek texels.

**Table 4 — Engine defaults** (starting values to tune on synthetic and real sets)

| Parameter | Default | Range / σ | Note | Badge |
|---|---|---|---|---|
| Map size N | 4096 | 2048 phone, 8192 ≥24 MP | Table 1 | 🧠 |
| θ_max (hard) / fade start | 75° / 60° | 70–80° | Table 2 | 🧠 |
| cos exponent p | 2 | 1–4 | taste-tuned | ↔️ |
| Depth tolerance ε | max(1 mm, 2σ_geom) | scan 0.5–1, template 2–5 mm | | 🧠 |
| Edge erosion / ramp | 5 px / 10 px source | 3–15 px | or 1–3 mm surface | 🧠 |
| Frame margin | 2% of width | 1–5% | | 🧠 |
| Pyramid sampling | level = log₂(footprint) | max 3 | | 🧠 |
| Gain prior σ (log) | 0.05 manual exposure | 0.3 auto | | 🧠 |
| WB ratio prior σ | 0.03 locked | 0.15 auto | | 🧠 |
| Vignetting corner falloff σ | 0.5 stop | 0.3–1 | per lens | 🧠 |
| Multiband levels | 5 at 4K | 4–6 | | ↔️ |
| Two-band split (Gaussian σ) | 3 mm surface | 2–5 mm | ≈25 texels at 4K head | 🧠 |
| Gutter | 16 px at 4K | 8 at 2K, 32 at 8K | | 🧠 |
| Harmonic-fill max hole | 5 mm | 3–10 mm | larger → mirror/patch | 🧠 |
| Mirror-fill source threshold | w ≥ 0.3·w_max | 0.2–0.5 | | 🧠 |
| Generative fill allowed | confidence < 0.2 | off by default | | ↔️ |
| Min views for specular median | 3 | — | | 🧠 |
| Photometric pose refine σ | 0.1°, 1 mm | landmark cameras only | | 🧠 |
| AO division γ | 0.5 | 0.3–0.6 | | ↔️ |

## Disagreements, myths & open questions

- **Select or blend?** Photogrammetry texturers favour selection plus levelling (Waechter-style); panorama practice favours multiband. For faces with ≤1 mm misfit, two-band or multiband wins; with larger misfit, selection avoids ghosts but exposes seams ↔️
- **Exponent p and θ_max** are tuned by taste; no face-specific study is known to me ↔️
- **"Bigger maps = more detail."** Myth beyond the photo GSD (Table 1) 🧠
- **"Cross-polarised = de-lit."** Myth: only specular is removed 🧠
- **Generative completion for likeness** is contested: diffusion fills look plausible but are not the person. Licences vary (Tencent Hunyuan 3D 2.x licences exclude the EU, UK and South Korea from their Territory [2]), as do identity-safety controls and skin-tone bias ↔️
- **De-light or not?** Sculptors may want residual shading as a form cue; renderers need de-lit albedo. Keep both ↔️
- **Open questions** 🧠 (time-sensitive): the best open face-UV completion model as of late 2026 and its licence; whether baking Gaussian-splat avatars to UV beats classic projection; how well learned de-lighters handle dark skin; whether current Blender versions changed bake margin types or the Apply Camera Image operator.

## Sources

1. Blender Python API, Bake Margin Type Items and BakeSettings (default margin 16; Extend, Adjacent Faces): https://docs.blender.org/api/current/bpy_types_enum_items/bake_margin_type_items.html , https://docs.blender.org/api/current/bpy.types.BakeSettings.html
2. Tencent Hunyuan 3D 2.1 Community License (Territory excludes EU, UK, South Korea): https://gitserver.onethingai.com/ai-models/Hunyuan3D-2.1/raw/branch/main/LICENSE ; 2.0 text: https://huggingface.co/tencent/Hunyuan3D-2/blob/main/LICENSE
3. Ramamoorthi & Hanrahan, SIGGRAPH 2001 (9 SH coefficients, ~1% average error): https://graphics.stanford.edu/papers/envmap/ , https://history.siggraph.org/?p=116946

4. Agisoft Metashape installer page (Texture De-Lighter listed as a free download) and Agisoft forum announcement: https://www.agisoft.com/downloads/installer/ , https://www.agisoft.com/forum/index.php?topic=11086.0

No other sources linked. Related notes: `blender/skin-shading.md`, `reconstruction/photogrammetry-heads.md`, `blender/reference-camera-setup.md`, `community/ai-assisted-sculpting.md`, `reconstruction/single-image-regression.md`, `blender/import-export-scans.md`.

**Further reading (by name, not yet linked)**
- Debevec, Taylor & Malik, "Modeling and Rendering Architecture from Photographs", SIGGRAPH 1996 (view-dependent texture mapping)
- Lempitsky & Ivanov, "Seamless Mosaicing of Image-Based Texture Maps", CVPR 2007
- Waechter, Moehrle & Goesele, "Let There Be Color! Large-Scale Texturing of 3D Reconstructions", ECCV 2014
- Burt & Adelson, "A Multiresolution Spline with Application to Image Mosaics", ACM TOG 1983
- Brown & Lowe, "Automatic Panoramic Image Stitching using Invariant Features", IJCV 2007
- Pérez, Gangnet & Blake, "Poisson Image Editing", SIGGRAPH 2003
- Prada, Kazhdan, Chuang & Hoppe, "Gradient-Domain Processing within a Texture Atlas", SIGGRAPH 2018
- Liu, Ferguson, Jacobson & Gingold, "Seamless: Seam Erasure and Seam-Aware Decoupling of Shape from Mesh Resolution", SIGGRAPH Asia 2017
- Zhou & Koltun, "Color Map Optimization for 3D Reconstruction with Consumer Depth Cameras", SIGGRAPH 2014
- Eisemann et al., "Floating Textures", Eurographics 2008
- Gortler, Grzeszczuk, Szeliski & Cohen, "The Lumigraph", SIGGRAPH 1996 (pull-push)
- Barnes, Shechtman, Finkelstein & Goldman, "PatchMatch", SIGGRAPH 2009
- Ramamoorthi & Hanrahan, "An Efficient Representation for Irradiance Environment Maps", SIGGRAPH 2001
- Debevec et al., "Acquiring the Reflectance Field of a Human Face", SIGGRAPH 2000
- McCamy, Marcus & Davidson, "A Color-Rendition Chart", Journal of Applied Photographic Engineering, 1976
- Deng, Cheng, Xue, Zhou & Zafeiriou, "UV-GAN: Adversarial Facial UV Map Completion for Pose-invariant Face Recognition", CVPR 2018
- Gecer, Ploumpis, Kotsia & Zafeiriou, "GANFIT", CVPR 2019
- Gecer, Deng & Zafeiriou, "OSTeC: One-Shot Texture Completion", CVPR 2021
- Lattas et al., "AvatarMe: Realistically Renderable 3D Facial Reconstruction 'in-the-wild'", CVPR 2020
- Smith et al., "A Morphable Face Albedo Model", CVPR 2020
- Papantoniou, Lattas, Moschoglou & Zafeiriou, "Relightify: Relightable 3D Faces from a Single Image via Diffusion Models", ICCV 2023
- Richardson et al., "TEXTure: Text-Guided Texturing of 3D Shapes", SIGGRAPH 2023
- Zeng et al., "Paint3D: Paint Anything 3D with Lighting-Less Texture Diffusion Models", CVPR 2024
- Lee, Liu, Wu & Luo, "MaskGAN: Towards Diverse and Interactive Facial Image Manipulation" (CelebAMask-HQ face parsing), CVPR 2020
- Yu et al., "BiSeNet: Bilateral Segmentation Network for Real-time Semantic Segmentation", ECCV 2018

## Verification log (2026-11-20)

- **Waechter et al. 2014 method details** (gradient-magnitude data term, photo-consistency, global additive colour levelling, ~20 px Poisson seam strip): unconfirmed. Search confirmed only the paper's identity and, via a secondary description, the photo-consistency check and improved global colour adjustment; Poisson editing and gradient magnitude were not seen in results. Badges left at 🧠. https://link.springer.com/content/pdf/10.1007/978-3-319-10602-1_54.pdf
- **Blender bake margin (16 px default; Adjacent Faces and Extend types)**: confirmed 📄 [1]. UV Project camera aspect and Image > Apply Camera Image: unconfirmed. https://docs.blender.org/api/current/bpy.types.BakeSettings.html
- **Hunyuan licence excludes EU, UK, South Korea**: confirmed [2] (the bullet stays ↔️ because the surrounding claims are contested). Which model is state of the art in late 2026: unconfirmed. https://gitserver.onethingai.com/ai-models/Hunyuan3D-2.1/raw/branch/main/LICENSE
- **Ramamoorthi & Hanrahan 2001: 9 SH coefficients suffice**: confirmed 📄 [3], about 1% average error (abstract excerpt). https://graphics.stanford.edu/papers/envmap/

## Verification log, pass 2 (2026-11-20)

- **3x3 matrix on 24-patch chart gives mean dE2000 about 1.5-3**: unconfirmed. Search found Imatest's method documentation (default metric is mean squared dE2000; input must be linearised) but no stated typical value; Kasson's blog figures were not visible. Badge left at ↔️. https://www.imatest.com/docs/colormatrix/
- **Agisoft Texture De-Lighter is a free stand-alone tool**: confirmed 📄 [4] (free, stand-alone, brush-stroke input, 8-bit JPEG-optimised). **Unity De-Lighting tool likely unmaintained**: unconfirmed. Bullet stays ↔️ because of the Unity half. https://www.agisoft.com/downloads/installer/
