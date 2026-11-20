# Face recognition embeddings as identity signals

> Face-recognition networks such as ArcFace map an aligned face crop to a unit-length embedding, and two faces count as "the same person" when the embeddings' cosine similarity is above a threshold that has to be calibrated. In photo-to-3D work these embeddings play two different roles: as a frozen **identity encoder** that feeds a supervised shape regressor (this is what MICA does), and as a **likeness score** that compares renders of the sculpt against the source photos. The harvested sources do not support the common idea that MICA trains with an "ArcFace identity loss": its training objective is a masked 3D geometry loss. No canonical similarity threshold exists, and the redistributable InsightFace weights (buffalo_l) carry a non-commercial licence claim that still needs checking. **Verification status: the shared web-search budget ran out before this session could cross-check anything, and direct page fetches are blocked. Every empirical claim below is therefore single-source (the harvester's search snippets) unless it is a mathematical identity.**

## Key facts

- **ArcFace** (Deng, Guo, Yang, Xue, Kotsia, Zafeiriou; CVPR 2019) proposes an additive angular margin loss. The name comes from the fact that the additive angular margin equals a geodesic-distance margin on the normalised hypersphere [1][2]. ⚠️ single-source ([1] and [2] are two versions of the same paper, so they are not independent)
- The ArcFace paper reports state-of-the-art results on **ten** face-recognition benchmarks, and the arXiv abstract also describes a **sub-center** variant for noisy training data [1]. ⚠️
- **MICA** (Zielonka, Bolkart, Thies; ECCV 2022) uses a **pretrained ArcFace network as its identity encoder**, followed by a small mapping network into the latent space of a geometry decoder [3][4]. ⚠️ (the project page [4] is from the same authors, so it is not independent)
- MICA keeps most of ArcFace **frozen** and fine-tunes only the **last 3 ResNet blocks**. The authors report that refining more layers made predictions worse through overfitting [3]. ⚠️
- MICA's training objective (Eq. 1 in the snippet) is a **masked, supervised 3D geometry loss against ground-truth scans**. The snippets showed no separate ArcFace feature-matching or identity term [3]. ⚠️ This means ArcFace serves MICA as an *input representation*, not as a loss.
- MICA reports **15 % (non-metric)** and **24 % (metric)** lower average reconstruction error than the prior state of the art on the **NoW** benchmark [3]. ⚠️
- MICA's argument for this design is that ArcFace features are robust to expression, illumination and camera changes, so a shape regressor trained on top of them generalises well [3]. ⚠️
- **FaceNet** verifies faces by thresholding the **squared L2 distance** between embeddings and reports **99.63 % LFW** accuracy. This figure came from a search-result summary, not the paper text [5]. ⚠️
- **LFW protocol**: accuracy is usually reported over 10 folds. The threshold is tuned on 9 folds, applied to the held-out fold, and the 10 results are averaged [9]. ⚠️
- For unit-normalised embeddings, **‖a−b‖² = 2 − 2·cos θ**, so cosine and L2 thresholds convert into each other exactly [5]. ✅ This is an algebraic identity, checked by derivation rather than by sources.
- **Thresholds depend on the model and the dataset**, and no canonical cosine threshold for ArcFace-family models was found. The recommended practice is to sweep the threshold on your own labelled pairs until you reach the false-accept rate you want [9]. ⚠️
- One LFW study cites a "conventional" fixed **cosine threshold of 0.5** and reports that an adaptive threshold beat it [9]. ⚠️ This is a secondary mention and is not a recommendation.
- InsightFace's **buffalo_l** pack contains SCRFD-10GF detection plus a ResNet50 recognition model trained on WebFace600K, about **326 MB** in total [6]. ⚠️
- Its recognition file **w600k_r50.onnx** is about **166 MB** and outputs **512-d** embeddings, and detection uses `det_10g.onnx` (SCRFD). These figures come from a third-party README [7] and were not matched against the official zoo [6]. ⚠️
- **Licence**: third-party projects state that the InsightFace *pretrained models* are for non-commercial research only, separately from the MIT-licensed code [7]. ⚠️ Confirm against the official model zoo page and licence [6] before any commercial use.
- Downloads of buffalo_l from SourceForge, Hugging Face and GitHub release assets are **community mirrors** [8][10]. One README claims a mirror matches the official file, which is unverified, so check SHA-256 hashes. ⚠️
- In the older 0.3.2 Python package, the official CLI is `insightface-cli model.download buffalo_l`, and the default cache location is `~/.insightface/models/buffalo_l/` [6]. ⚠️

## Numbers & reference tables

**Table 1: Reported results and design numbers** (all single-source)

| Item | Value | Unit | Population / benchmark | Source |
|---|---|---|---|---|
| MICA error reduction vs prior SOTA, non-metric | 15 | % lower average reconstruction error | NoW benchmark (sample size not retrieved) | [3] |
| MICA error reduction vs prior SOTA, metric | 24 | % lower average reconstruction error | NoW benchmark (metric variant) | [3] |
| ArcFace ResNet blocks fine-tuned in MICA | 3 | blocks (the rest frozen) | n/a | [3] |
| Benchmarks on which ArcFace reports SOTA | 10 | benchmarks | per the ArcFace abstract | [1] |
| FaceNet LFW verification accuracy | 99.63 | % | LFW (10-fold protocol) | [5] (from a summary, unchecked) |
| "Conventional" fixed cosine threshold cited | 0.5 | cosine similarity | LFW-based study | [9] (secondary) |

**Table 2: InsightFace buffalo_l files** (sizes are approximate; nothing hash-verified)

| File / pack | Role | Approx. size | Output | Source |
|---|---|---|---|---|
| buffalo_l (pack) | SCRFD-10GF detector + ResNet50 recogniser (WebFace600K) | ~326 MB | n/a | [6] |
| w600k_r50.onnx | identity embedding | ~166 MB | 512-d vector | [7] (third-party) |
| det_10g.onnx | face detection (SCRFD) | not retrieved | boxes and keypoints | [7] |

**Table 3: Converting between cosine and L2 for unit vectors** (worked arithmetic from d² = 2 − 2cos; these are *not* recommended thresholds)

| cos θ | Squared L2 (d²) | L2 (d) | Angle θ (deg) |
|---|---|---|---|
| 1.0 | 0.0 | 0.000 | 0.0 |
| 0.7 | 0.6 | 0.775 | 45.6 |
| 0.5 | 1.0 | 1.000 | 60.0 |
| 0.3 | 1.4 | 1.183 | 72.5 |
| 0.0 | 2.0 | 1.414 | 90.0 |

## Applying this to photo→3D face sculpting in Blender

1. **Use the embedding as a scorecard, not a target.** Detect and align each reference photo with the pack's detector, then embed it with the recogniser. Render the Blender head from a camera matched to each photo (same pose and similar focal length and crop), embed the render the same way, and report cosine similarity between each render and its photo. Always L2-normalise before taking the dot product.
2. **Calibrate your own threshold** instead of trusting any published number [9]. For each subject, embed several *different* real photos of the same person to get a "genuine" distribution, and embed photos of other consenting people to get an "impostor" distribution. A render's score only means something relative to these two. The 10-fold idea from LFW [9] applies whenever you have enough labelled pairs.
3. **Separate texture from geometry.** *This is a hypothesis; no source on it was retrieved.* A recogniser sees pixels, so if photo texture is projected onto the mesh, the score can come mostly from the skin, brows and eye colour rather than the shape. Score at least three render conditions:
   - (a) the projected photo texture;
   - (b) Workbench or Solid shading with a single flat colour ("clay");
   - (c) clay with lighting that matches the photo.

   If (a) is high and (b)/(c) are low, the likeness lives in the texture, so keep sculpting.
4. **Do not use the embedding to check metric dimensions.** MICA needed supervised 3D scans to turn ArcFace features into metric shape [3]. Robustness to expression, lighting and camera [3] also means the embedding is deliberately insensitive to some things a sculptor cares about. Check proportions in millimetres with landmark reprojection and scale references, not with cosine scores.
5. **Watch for the render-versus-photo domain gap** (unsourced reasoning). Synthetic renders without hair, eyes or neck can score low even when the shape is right. Keep the render framing consistent and compare *relative* gains between sculpt iterations rather than absolute scores.
6. **Model acquisition.** Do not bundle buffalo_l in an add-on. The weights' licence is reported as non-commercial [7], and mirrors are unofficial [8][10]. Let the user download from the official route [6], record the SHA-256 of each ONNX file, and refuse to load files whose hash differs from one the user has pinned.
7. **Ethics and consent.** An identity embedding is a biometric template: it can link a 3D head back to a real person.
   - Run everything locally.
   - Do not persist embeddings by default, and store only scores.
   - Show a consent checkbox ("I have the subject's permission") before any photo is embedded.
   - Never offer search or matching against other people's photos.

   Biometric-data laws (for example the EU GDPR and AI Act, or Illinois BIPA) may apply. Their applicability was not researched in this session.

## Algorithmic implications

- **Two separate components.** (i) An **identity scorer**: ONNX inference, no gradients, used for evaluation, early stopping and model selection. (ii) An optional **identity prior**: a MICA-style regressor from the embedding to shape coefficients, which needs 3D-supervised training [3]. Do not describe the scorer as a "loss" in docs or the UI. MICA itself does not use it that way [3].
- **If a differentiable identity loss is ever added** (a PyTorch recogniser), weight it low relative to landmark reprojection and shape-prior terms. Optimising directly against a classifier can produce adversarial texture or detail changes that raise the score without improving shape. This is a general concern, not sourced for this setting. Apply it only to clay renders (step 3) so that texture cannot satisfy it.
- **Fine-tuning defaults** for anyone training an embedding→shape regressor: freeze the backbone and fine-tune at most the last 3 ResNet blocks, since MICA found that unfreezing more layers overfits [3].
- **Configuration the engine should store per model** (no hard-coded constants):
  - `model_sha256`;
  - `embedding_dim` (read from the ONNX output shape, expected 512 for w600k_r50 [7]);
  - `input_shape` (read from the ONNX input, never assumed);
  - the alignment template;
  - `metric: cosine`;
  - `threshold: null` until the user has calibrated one.
- **Combine scores across views.** Compute one cosine score per matched photo, and report the median plus the worst view. Large spread across views points to pose or camera mismatch rather than a shape error.
- **Report three numbers per iteration**: textured score, clay score, and their gap (`identity_texture_gap`). The fitter's stopping rule should use the clay score.
- **Licence guard.** Store the model's licence string with its config. The add-on should warn when a non-commercial-tagged model is enabled in a project marked commercial.

## Disagreements, myths & refuted claims

- **"MICA uses ArcFace as an identity loss": refuted by the primary source, as read in the harvested snippets.** MICA uses ArcFace as a frozen, partly fine-tuned encoder and trains with a masked 3D geometry loss [3]. The full text was not re-read in this session.
- **Threshold numbers are not comparable across models or metrics.** FaceNet's thresholds are squared-L2 on FaceNet's own scale [5], while the 0.5 figure is cosine and cited secondhand [9]. The harvester also noted another system using 0.08–0.09 but gave no source, so that value is **dropped**.
- **"ArcFace scores 99.83 % on LFW."** The harvester planned this query but never confirmed the figure, so it is dropped from the main text until a primary-source check.
- **"Mirror X equals the official buffalo_l."** This is unverified [8][10]. Treat mirrors as untrusted until hashes match.
- **Myth (my analysis): "higher identity similarity means more accurate geometry."** The recogniser is trained for invariance [3] and sees texture. Without a clay-render control, a high score says nothing specific about shape.

## Open questions

- Get the exact ArcFace hyperparameters and benchmark tables (LFW, IJB-B/C) from the paper text.
- Find the **official** InsightFace model licence wording and the SHA-256 hashes of buffalo_l files.
- Check whether MICA's released training code uses any ArcFace-feature loss, and which morphable model its decoder targets (the harvested snippets do not say).
- Measure how much embedding similarity comes from texture versus geometry in 3D reconstruction. No literature on this was retrieved.
- Survey ArcFace successors (e.g., AdaFace, MagFace) and whether their ONNX weights have more permissive licences. Not searched.
- Find demographic-bias evidence (e.g., NIST FRVT/FRTE) and its effect on likeness scoring for under-represented groups. Not searched.
- Find the identity-similarity metrics used in DECA/EMOCA-style evaluations. Not searched.
- Check the legal status of computing and storing face embeddings of third parties for avatar creation. Not searched.

## Sources

[1] ArcFace: Additive Angular Margin Loss for Deep Face Recognition — https://arxiv.org/abs/1801.07698 — paper — 2019
[2] ArcFace (arXiv HTML v3) — https://arxiv.org/html/1801.07698v3 — paper — 2019
[3] MICA: Towards Metrical Reconstruction of Human Faces (Zielonka, Bolkart, Thies) — https://arxiv.org/abs/2204.06607 — paper — 2022
[4] MICA project page (MPI-IS) — https://is.mpg.de/ncs/en/projects/mica-towards-metrical-reconstruction-of-human-faces — official-docs — 2022
[5] FaceNet: A Unified Embedding for Face Recognition and Clustering — https://arxiv.org/pdf/1503.03832.pdf — paper — 2015
[6] InsightFace python-package model_zoo.md — https://github.com/deepinsight/insightface/blob/master/python-package/docs/model_zoo.md — repo — 2024
[7] Third-party InsightFace buffalo_l wrapper README (licence claim unverified) — https://github.com/wangyifan349/insightface-face-similarity — repo — year unknown
[8] Third-party trimmed buffalo_l release (unverified mirror) — https://github.com/inoveee/eventlens/releases/tag/face-models-v1 — forum — year unknown
[9] Adaptive Threshold for Online Object Recognition and Re-identification Tasks — https://arxiv.org/pdf/2012.14305 — paper — 2020
[10] Third-party weights release (unverified mirror) — https://github.com/finetech-nexus/ai-api/releases/tag/weights-v1 — forum — year unknown
