# Hard- and soft-tissue anthropometric landmarks

> Craniofacial landmarks come in two layers. Bony points (nasion, glabella, orbitale, porion, zygion, gonion, pogonion, menton) are never visible to a camera; skin points (n′, prn, sn, ls, sto, li, pg′, gn′, en, ex, ch, al, t, tr, v) are. Most definitions are extremal ("most anterior", "lowest", "most lateral"), so a point only exists once a head frame is fixed: the Frankfort horizontal through porion and orbitale on bone, approximated on the living by tragion and soft-tissue orbitale. Several names (gonion, gnathion, subnasale, labiale superius, stomion, soft-tissue nasion) have competing constructions, so a tool must store one explicit definition per landmark. Detector schemes (dlib 68, MediaPipe 478) are annotation conventions: eye and mouth corners, nose tip and subnasale approximate anatomical points, but jaw and brow points are spaced contour samples to fit as sliding curves, never as gonion or glabella.
>
> Evidence status: 36 ✅ / 27 📄 / 71 🧠 / 18 ↔️ — 🧠 items remain unconfirmed after the 2026-11-20 verification pass (1 of 4 queued claims confirmed).

## Key facts

Legend: ✅ two or more independent input sources agree · 📄 one input source · 🧠 author knowledge, not yet checked · ↔️ contested. Citations rest on harvested snippets and tables; full texts were not re-read.

**Frames and naming**
- **Frankfort horizontal (FH):** the plane through porion and orbitale [1][3] ✅. Living-subject anthropometry (Farkas) uses tragion and the palpated soft-tissue orbitale (or′) instead 🧠; the offset of that t–or′ line from bony po–or is unquantified here 🧠.
- **Notation.** Anthropometry writes living-surface points in lower case without primes (pg, gn); cephalometry capitalises bone (N, Pog, Me) and primes soft tissue (N′, Pog′) 🧠. A 3D-imaging study uses g, n, sn, pg, en, ex, al, cph, ch, ls, ft [9] 📄. Farkas, *Anthropometry of the Head and Face* (1994), is the standard reference for definitions and North American White norms, many framed in 2D planes [17][18] ✅.
- One name can denote different constructions in different protocols; check the protocol before comparing values [10][11] ✅.

**Hard tissue (bone)**
- **Nasion (n/N):** midline junction of the frontal and nasal bones, where the frontonasal suture meets the internasal suture [1][3] ✅.
- **Glabella (g):** most prominent midline point of the forehead above the nasal root, at about the level of the supraorbital ridges [1][15] ✅.
- **Orbitale (or/Or):** lowest point of the inferior orbital margin [1][3] ✅. A radiographic variant takes the midpoint of the left and right orbitale images [3] ↔️, because bilateral structures do not superimpose on a lateral film [6] 📄.
- **Porion (po/Po):** uppermost point of the external acoustic meatus [1][3] ✅. Porion and orbitale are hard to locate, lying in a vague region of soft tissue, nerves and vessels [3] 📄. Anatomical porion is not "machine porion" (top of the cephalostat ear rod) 🧠.
- **Zygion (zy):** most lateral point of the zygomatic arch [1] 📄; zy–zy is bizygomatic face width.
- **Gonion (go/Go):** the mandibular angle where body meets ramus, constructed three ways: most outward-inferior point of the angle [1][2], point cut by the bisector of the ramus/body tangent angle [4], or intersection of the tangents [5] ↔️.
- **Pogonion (pog/Pog)** is the most anterior and **menton (me/Me)** the lowest midline point of the bony chin [1][2] ✅. Cephalometric **gnathion (Gn)** lies midway between them [1] 📄. Classical anthropometry (Martin–Saller, Farkas) uses gn for the *lowest* chin point, i.e. cephalometric menton, so Farkas "n–gn" ends at me′ 🧠 ↔️.

**Soft tissue (skin)**
- **Soft-tissue nasion (n′):** the deepest point of the frontonasal concavity (cephalometry) or the skin point over bony n (anthropometry); they can differ by several mm 🧠 ↔️.
- **Pronasale (prn):** most anterior (protrusive) midpoint of the nasal tip [7][12][14][16] ✅.
- **Subnasale (sn):** where the columella meets the upper lip in the midsagittal plane [7][12][14] ✅. Constructions differ: a point on the nasolabial contour between columella crest and lip [14], the deepest point of the nose-base/lip junction [15], or the lower columella border meeting the philtrum [16] ↔️.
- **Labiale superius (ls) / inferius (li):** midpoint of the upper (lower) vermilion line [10][16], but the most prominent upper (lower) lip point in a 2D CNN study [15] ↔️. Many 3D papers spell it *labrale*; same point 🧠.
- **Stomion (sto):** midline point where the naturally closed lips meet [9][10][11] ✅; some protocols split it into stomion superius and inferius (Stms/Stmi) [10][11] ↔️.
- **Soft-tissue pogonion (pg′):** most anterior midpoint of the soft-tissue chin [10][11] ✅.
- **Soft-tissue gnathion (gn′):** midpoint between the most anterior and most inferior chin points, or the lowest mental soft-tissue point (slightly lower) [10][11], or in some sources the chin–throat junction [14] ↔️. That junction is properly the cervical point (C) 🧠.
- **Endocanthion (en) / exocanthion (ex):** inner and outer commissures of the palpebral fissure [8][9][16] ✅. en is best seen with upward gaze [8][9] ✅; neither can be located with eyes closed, common in laser scans [13] 📄.
- **Cheilion (ch):** labial commissure [8][9][16] ✅. **Alare (al):** most lateral point of the alar contour [9][16] ✅; a separate *skeletal* alare exists, so always state the tissue [7][8] ✅.
- **Tragion (t):** notch on the upper margin of the tragus [8] 📄.
- **Trichion (tr):** midline point of the anterior hairline [9][16] ✅; a hair landmark that moves with recession 🧠. **Vertex (v):** highest midline point of the head [9][16] ✅, defined with the head in FH 🧠.

**Detector schemes**
- **68-point (iBUG 300-W / Multi-PIE):** the 300-W markup [20][21] 📄 (one lab). dlib's detector outputs 68 (x,y) points trained on 300-W [25][26] 📄. 0-based blocks: jaw 0–16, right brow 17–21, left brow 22–26, nose 27–35, right eye 36–41, left eye 42–47, mouth 48–67 (outer 48–59, inner 60–67) [24][25][26] ✅. "Right" is the subject's right, image left 🧠. The blog's nose range "[27, 35]" [25] drops point 35 if read as a slice; the nose is 27–35 inclusive 🧠.
- Jaw points are evenly spaced along the contour; brow points sit on the arc centre, top or bottom depending on dataset [22] 📄. WFLW's 98 points convert to 68 by dropping alternate jaw points and extra lower-brow points [23] 📄. Sliding jawline points are not 3D-consistent, so a 2024 method dropped them from evaluation [32] 📄.
- **MediaPipe 478** = 468 face-mesh vertices in stable order + 10 iris points at 468–477 [27][28] ✅. An MIT-licensed converter maps 478 → dlib 68 [29] 📄; its index table was not read. The mesh has no ears, scalp or neck, so t, po, tr and v have no vertex; its z is relative depth scaled like x, not metric (check [30][31]) 🧠.
- No 2025 benchmark for 3D anthropometric face landmarks was found; Proto-Former (Oct 2025) is 2D [33] 📄 (time-sensitive).
- **Licences (time-sensitive):** MediaPipe is Apache-2.0, while dlib's distributed 68-point model file is trained on 300-W images whose licence excludes commercial use, so an add-on should not bundle it 🧠.

**Reliability**
- In CBCT, gonion has the largest intra- and inter-observer distances; gonion, nasion, orbitale and ANS have the largest median distances [39][40] ✅. Gnathion, menton and pogonion ICCs are mostly ≥0.9; gonion's inter-observer vertical ICC is about 0.71–0.73 [40] 📄. Manual errors can exceed 2 mm at gonion and orbitale [38] 📄.
- Gonion error runs along the gonion–menton line, so the mandibular-plane angle stays accurate [38] 📄: error is anisotropic, larger along a contour than across it 🧠.
- Farkas norms differ considerably from 3D stereophotogrammetry data, possibly from method, secular trend or ethnic mix [19] 📄.

**Blender tools (time-sensitive)**
- FaceFit (v0.1 prototype) fits MPFB2 heads to photos with 57 "stable" MediaPipe points, solving in an external MCP server; tested on Blender 4.2.3 LTS with MPFB2 2.0.18 [41] 📄. CaptureForge (GPL-3.0) reports worse weights from fitting tracked landmarks than from MediaPipe's own scores on stylized heads [42] 📄.

## Numbers & reference tables

**Table 1: Registry and detector correspondences.** 0-based indices; (R / L) = subject's side; "~" = approximate or convention-placed. MediaPipe indices are author candidates to confirm by rendering index labels on the canonical mesh. Bookstein type: I tissue junction, II curvature extreme, III extremal or constructed.

| Abbr | Tissue, side | Type | dlib 68 | MediaPipe 478 | Status |
|---|---|---|---|---|---|
| n / n′ | bone / skin, mid | I / III | ~27 | ~168 (6 lower) | ✅ def [1][3]; 🧠 map |
| g / g′ | bone / skin, mid | III | — | ~9 | ✅ def [1][15]; 🧠 map |
| or / or′ | bone / skin, bilat | III | — | — | ✅ def [1][3] |
| po | bone, bilat | III | — | — | ✅ def [1][3] |
| t | skin, bilat | I | — (0/16 lie in front of the ear) | — | 📄 def [8]; 🧠 map |
| zy / zy′ | bone / skin, bilat | III | ~0–2 / 14–16, silhouette | ~234 / 454, silhouette | 📄 def [1]; 🧠 map |
| go / go′ | bone / skin, bilat | III | ~3–5 / 11–13, sliding | ~172 / 397 (or 58 / 288) | ↔️ def; 🧠 map |
| pog / pg′ | bone / skin, mid | III | — (profile only) | ~199 | ✅ def [1][2][10][11]; 🧠 map |
| me / me′ (Farkas gn) | bone / skin, mid | III | ~8 | ~152 | ✅ def [1][2]; 🧠 map |
| prn | skin, mid | II | 30 | 1 (4 just above) | ✅ def; 🧠 map |
| sn | skin, mid | I | 33 | ~2 (94 columella, 164 philtrum) | ↔️ def; 🧠 map |
| al | skin, bilat | III | — (31/35 = alar base) | ~129 / 358, verify | ✅ def; 🧠 map |
| ls | skin, mid | I/II | 51 | 0 | ↔️ def; 🧠 map |
| sto | skin, mid | I | mean(62, 66) | mean(13, 14) | ✅ def; ↔️ split |
| li | skin, mid | I/II | 57 | 17 | ↔️ def; 🧠 map |
| en (R / L) | skin | I | 39 / 42 | 133 / 362 | ✅ def; 🧠 map |
| ex (R / L) | skin | I | 36 / 45 | 33 / 263 | ✅ def; 🧠 map |
| ch (R / L) | skin | I | 48 / 54 | 61 / 291 | ✅ def; 🧠 map |
| tr | hair, mid | — | — | — (10 = mesh top, below tr) | ✅ def [9][16]; 🧠 map |
| v | skin, mid | III | — | — | ✅ def [9][16] |
| iris centre (R / L) | — | — | — | 468 / 473 | 🧠 |

**Table 2: Approximate adult linear norms (mm).** Ranges of *means* recalled from Farkas-type data on young North American White adults (not SDs; SDs run ~4–7% of the mean). Weak, population-conditional priors only.

| Measure | Male mean | Female mean | Typical SD | Status |
|---|---|---|---|---|
| en–en | 32–34 | 31–33 | 2–3 | 🧠 |
| ex–ex | 88–92 | 85–89 | 3–4 | 🧠 |
| ex–en (eye fissure) | 30–32 | 29–31 | 1–2 | 🧠 |
| al–al | 33–36 | 30–33 | 2–3 | 🧠 |
| ch–ch | 51–55 | 48–52 | 3–4 | 🧠 |
| zy–zy | 135–141 | 127–132 | 4–6 | 🧠 |
| go–go | 94–100 | 88–94 | 5–7 | 🧠 |
| n–sn | 53–57 | 49–53 | 3–4 | 🧠 |
| sn–prn (tip protrusion) | 18–22 | 17–20 | ~2 | 🧠 |
| sn–sto | 21–24 | 19–22 | 2–3 | 🧠 |
| sn–me′ | 70–75 | 63–67 | 4–5 | 🧠 |
| n–me′ (Farkas n–gn) | 119–125 | 110–115 | 5–7 | 🧠 |
| eu–eu (head width) | 148–155 | 141–147 | ~5 | 🧠 |
| g–op (head length) | 192–200 | 182–190 | 6–7 | 🧠 |

East Asian adults average a larger en–en and African-descent adults a much wider al–al; Farkas's international study showed large between-group differences 🧠 ↔️.

**Table 3: Scale anchors and angles.**

| Quantity | Typical value | Use | Status |
|---|---|---|---|
| Horizontal visible iris diameter | ~11.7 mm, SD ~0.5 (MediaPipe Iris assumption) [54] | absolute scale from one photo, ~±4% | 📄 |
| Interpupillary distance, adults | mean ~61–64 mm; most 55–70 | sanity check | 🧠 |
| FH vs true horizontal, natural head position | mean within a few degrees; between-subject SD ~3–5° | camera level ≠ FH | 🧠 ↔️ |
| Nasolabial angle (columella–sn–ls) | ~90–110°, women more obtuse | profile check | 🧠 |
| Nasofrontal angle (g′–n′–prn) | ~115–135° | profile check | 🧠 |

**Table 4: Measured landmark localization error.**

| Setting | Error | Src | Status |
|---|---|---|---|
| Non-rigid template registration, 3D optical scans | <2 mm for 53.1% of landmarks, <4 mm for 84.4%; midface best, upper face worst | [34] | 📄 |
| Mobile-device 3D scanner, controlled light and angles | ~1 mm average | [35] | 📄 |
| 3D detection under large yaw and expression | 4.5–6.3 mm mean | [36] | 📄 |
| U-Net 3D landmarks, acromegaly patients | NME 2.8 mm | [37] | 📄 |

**Table 5: Frame sensitivity of extremal landmarks.** Tilting the frame by θ slides an extremal point ≈ R·θ along the surface (R = local radius of curvature in the tilt plane); exact for a circular arc, R values rough.

| Landmark | R (mm) | Slide per 5° (mm) | Per 10° (mm) | Status |
|---|---|---|---|---|
| prn | 6–10 | 0.5–0.9 | 1.0–1.7 | 🧠 |
| pg′, me′ | 15–30 | 1.3–2.6 | 2.6–5.2 | 🧠 |
| g′ | 30–80 | 2.6–7 | 5–14 | 🧠 |
| zy (yaw) | 40–80 | 3.5–7 | 7–14 | 🧠 |
| v | 80–100 | 7–9 | 14–17 | 🧠 |

## Applying this to photo→3D face sculpting in Blender

1. **Shoot to the definitions.** Frontal, both true profiles and both ¾ views at ≥1.5 m with an 85–135 mm (full-frame-equivalent) lens: a nose tip ~100 mm nearer the lens than the ear plane is magnified by (d+100)/d, about 20% at 0.5 m and 5% at 2 m 🧠. Neutral face, lips closed in repose (sto is defined for that state [10][11]), eyes open (en/ex vanish when closed [13]), ears and hairline uncovered, glasses off (lenses rescale the eyes; nose pads dent n′) 🧠. Profiles are mandatory for the depth of n′, prn, sn, pg′, me′. For v, flatten hair under a thin cap; loose hair adds 5–20+ mm 🧠.
2. **Fix the frame first.** Set the midsagittal plane from bilateral pairs (en, ex, ch, al, t); level FH on t and or′ (with consent, palpate the lowest infraorbital rim and mark it with a small sticker before shooting). From the engine frame (`face3d`: +x subject's left, +y up, +z forward, mm) map to Blender as (x, y, z) → (x, −z, y): the face looks down −Y (Front view) and the subject's left is +X, `.L` 🧠. Re-derive extremal points after any re-orientation (Table 5).
3. **Name and bind.** Empties `LM.prn`, `LM.en.L`, … carry custom properties `tissue`, `variant`, `views`, `sigma_mm`. A Shrinkwrap constraint (Nearest Surface Point) keeps skin empties on the sculpt; bone empties live on a skull mesh. Vertex or barycentric binding survives only while topology is fixed; Dyntopo and Remesh break it 🧠.
4. **Check ratios, then add scale.** A single photo has no scale. Compare photo and mesh on ratios (Table 2 midpoints): en–en/ex–ex ≈ 0.36, ex–en/en–en ≈ 0.95, al–al/en–en ≈ 1.0–1.1, ch–ch/al–al ≈ 1.5–1.6, sn–sto : sto–me′ ≈ 1 : 2, go–go/zy–zy ≈ 0.70, n–me′/zy–zy ≈ 0.85–0.90 🧠. Then fix scale from one caliper measurement on the subject (ex–ex or en–en), a ruler in the facial plane, or the iris prior (±4%, only with an unoccluded iris and a solved camera).
5. **Bone on bone, skin on skin.** n, g, or, po, zy, go, pog, me belong on the skull; their gap to n′, g′, or′, zy′, go′, pg′, me′ is soft-tissue thickness (see `anatomy/skull-osteology.md`). Thin midline sites (n, g, rhinion) read bone through skin; go and zy do not.
6. **What goes wrong.**
   - The detector jaw "corner" is not gonion: jaw points are spaced by rule [22] and ride the silhouette on a turned head [32].
   - dlib 8 and MediaPipe 152 sit near me′ in a frontal view, not pg′ or gn′; the `CHIN` name in markup_68.h [24] does not say which.
   - Brow points follow hair and dataset convention [22], not glabella or the brow ridge.
   - Slightly parted lips split sto; a smile moves ch and flattens the nasolabial region.
   - Checking a Farkas norm against a cephalometric definition (gn, ls, n′) yields "errors" that are only naming.
   - Tragion is not porion. Trichion and vertex depend on hair; never use them for scale.

## Algorithmic implications

- **Schema.** Per landmark: `abbr`, `aliases` (`labrale_superius`→`ls`; `pogonion`→`pog` or `pg′` by tissue), `tissue`, `side`, `bookstein_type`, `variant` (`go: outer|bisector|tangents`, `gn: ceph_mid|anthro_lowest`, `gn′: orient|curve`, `sto: single|sup|inf`, `ls: border|prominent`, `n′: deepest|over_n`), `kind ∈ {vertex, barycentric, extremal(dir, region), constructed(fn), contour(sliding|silhouette)}`, `visibility`, `sigma_t`, `sigma_n`, `source_ids`. Never compare across variants. `face3d/synthetic.py` uses tissue-free `pogonion`/`menton`, `labrale_superius` and `vertex_front` (not v); route them through aliases before attaching priors.
- **Frame, then extremes.** Fit the midsagittal plane from mirrored pairs (reflection Procrustes) and the FH proxy from t and or′. Compute extremal landmarks as argmax ⟨p, d⟩ over a region mask after every pose update (softmax-weighted, temperature ~1–2 mm, for differentiability) 🧠.
- **Correspondence types.** Point: dlib 36/39/42/45 (ex, en), 48/54 (ch), 30 (prn), 33 (sn), 51/57 (ls, li), 62/66 (sto). Curve: 27–30 (dorsum), lip contours, brows at low weight. Silhouette: 0–16, residual = distance from the detection to the projected occluding contour along the image normal, sliding free [22][32]. For MediaPipe, register its canonical mesh to your base mesh once, version-lock that correspondence to the model, treat face-oval vertices as silhouette when |yaw| > ~20°, and ignore z or give it σ ≥ 10 mm 🧠.
- **Suggested positional σ (engine defaults, tune on data)** 🧠:

| Class | Examples | σ across contour (mm) | σ along contour (mm) |
|---|---|---|---|
| Sharp junction | en, ex, ch, sn, sto (closed) | 1.0–1.5 | 1.0–1.5 |
| Curvature extreme | prn, pg′, me′ | 1–2 | 2–4, plus R·σθ |
| Flat extremal | g′, zy′, go′, v | 1.5–3 | 5–10 or free |
| 2D jaw / face oval | dlib 0–16, MediaPipe oval | 1.5–2.5 | free |
| Brows | dlib 17–26 | 3–5 | free |
| Bone from skin, midline | n, g, pog | 1–2 on thickness | — |
| Bone from skin, lateral | go, zy | 3–5 on thickness | — |

- **Anisotropy.** Align covariances to the contour tangent; gonion error runs along the mandibular border [38].
- **Shape priors.** Gaussian on log-ratios of Table 2 pairs, σ_log ≈ 0.05–0.08 (≈ the CV), inflated ×1.5–2 by default because Farkas norms disagree with 3D data [19] and populations differ 🧠. Population and sex are explicit parameters; never default silently to North American White.
- **Symmetry.** Midline landmarks x = 0 with σ 1–2 mm; mirrored bilateral residual σ 1.5–3 mm (see `anatomy/facial-asymmetry.md`); never force exact symmetry 🧠.
- **Constructed points are functions:** go from fitted ramus and body tangents (all three variants), ceph Gn from Pog/Me; flag variant disagreement beyond a tolerance.
- **Gating.** Drop en/ex when eye openness fails [13]; drop sto and li when lips part; depth-critical midline points need a profile, ¾ view or depth source.

## Disagreements, myths & open questions

- **Definition conflicts** (detail above): gonion [1][2][4][5], orbitale [3], subnasale [14][15][16], ls/li [15][16], stomion [10][11], gn′ [10][11][14] ↔️; n′ 🧠 ↔️.
- **Gnathion:** cephalometric midpoint of Pog–Me [1] vs anthropometric lowest point (= menton) 🧠 ↔️, the most damaging naming trap when using Farkas norms.
- **Myth: neoclassical canons** (equal thirds; eye width = intercanthal = nose width; mouth = 1.5 × nose). Farkas's 1985 revision found most hold only in a minority of young adults 🧠: checks, not constraints.
- **Myth: "MediaPipe z is depth in mm"**: it is relative 🧠. **Myth: "68-point jaw corner = gonion"**: unsupported, given spacing by rule [22].
- **Dating:** the harvest calls [19] a 2019 study, but its PubMed ID suggests about 2015–16; unconfirmed.
- **Unattributed harvest numbers**, unused until sourced: CNN 3D-scan error 0.83 ± 0.49 mm (best at en, ex, ch); deep-learning gonion 1.06 mm, orbitale 1.39 mm; PCA geometry+texture RMS ~1.7–1.8 mm (17 landmarks); a structured-light sub-mm claim.
- **Open:** the 478→68 table in [29] is unread; Downs and Steiner originals not retrieved; t→po and or′→or offsets unquantified; Table 2 needs checking against Farkas.
- **Earlier pass:** nothing was confirmed or refuted then. The 1-based 68-point ranges it quarantined (jaw 1–17, brows 18–27, nose 28–36, eyes 37–48, mouth 49–68) match the sourced 0-based blocks and are restored.

## Sources

[1] Columbia University craniology slides (landmark definitions) — https://columbia.edu/itc/hs/medical/humanAnatomy/yuan/craniologyISlides_files/slide0061.html — lecture slides — unknown
[2] Grand Valley State, Introduction to Human Osteology — https://pressbooks.gvsu.edu/introhumanosteology/?p=60 — textbook — unknown
[3] PMC12334920 Table 1 (landmark definitions) — https://pmc.ncbi.nlm.nih.gov/articles/PMC12334920/table/T1 — paper — unknown
[4] BMC Oral Health landmark table (s12903-024-04260-3) — https://bmcoralhealth.biomedcentral.com/articles/10.1186/s12903-024-04260-3/tables/1 — paper — 2024
[5] BMC Oral Health landmark table (s12903-022-02179-1) — https://bmcoralhealth.biomedcentral.com/articles/10.1186/s12903-022-02179-1/tables/1 — paper — 2022
[6] Artificial-Intelligence-Based Cephalometric Landmark Detection in Lateral Cephalograms — https://pmc.ncbi.nlm.nih.gov/articles/PMC13466904/ — paper — unknown
[7] The definitions of three-dimensional landmarks on the human face: an interdisciplinary view — https://pmc.ncbi.nlm.nih.gov/articles/PMC4832301/ — paper — unknown
[8] The Reliability of Three-Dimensional Landmark-Based Craniomaxillofacial and Airway Cephalometric Analysis — https://pmc.ncbi.nlm.nih.gov/articles/PMC10377994/ — paper — unknown
[9] Facial Landmarks Determination with Different Digital Scanners: An In Vivo Study — https://pmc.ncbi.nlm.nih.gov/articles/PMC12941515/ — paper — unknown
[10] Soft-Tissue Analysis of Different Sagittal Skeletal Patterns Using the Geometric Morphometric Method — https://pmc.ncbi.nlm.nih.gov/articles/PMC9949938/ — paper — unknown
[11] Accuracy of AI-assisted soft tissue landmark identification in serial lateral cephalograms of Class III two-jaw surgery patients — https://pmc.ncbi.nlm.nih.gov/articles/PMC12460026/ — paper — unknown
[12] A rapid identification method for soft tissue markers of dentofacial deformities based on heatmap regression — https://pmc.ncbi.nlm.nih.gov/articles/PMC10907697/ — paper — unknown
[13] PMC4246044 (3D facial-scan landmark article; title not captured) — https://pmc.ncbi.nlm.nih.gov/articles/PMC4246044 — paper — unknown
[14] Nobel Biocare: Definition of 3D cephalometric soft tissue landmarks — https://nobellicense.nobelbiocare.com/help/d3d046fb-52e8-4b33-9f51-d3fd98ca3ed4/2.0/EN/3D_cephalometric_soft_tissue_landmarks.htm — commercial docs — unknown
[15] Clinical Equivalence of a CNN-Based Automated Soft Tissue Landmark Detection System on 2D Facial Images — https://pmc.ncbi.nlm.nih.gov/articles/PMC13205844/ — paper — unknown
[16] Facial Anthropometry and Analysis in Egyptian Women — https://pmc.ncbi.nlm.nih.gov/articles/PMC9116947/ — paper — unknown
[17] PMC6571015 (cites Farkas as standard; title not captured) — https://pmc.ncbi.nlm.nih.gov/articles/PMC6571015 — paper — unknown
[18] CDC Stacks document 79136 (cites Farkas; title not captured) — https://stacks.cdc.gov/view/cdc/79136 — report — unknown
[19] Farkas norms vs 3D stereophotogrammetry (title not captured) — https://pubmed.ncbi.nlm.nih.gov/26703056/ — paper — unconfirmed
[20] 300 Faces In-the-Wild Challenge (300-W), ICCV 2013, iBUG — https://ibug.doc.ic.ac.uk/resources/300-W — official docs — 2013
[21] 300 Faces In-The-Wild Challenge (300-W), IMAVIS, iBUG — https://ibug.doc.ic.ac.uk/resources/300-W_IMAVIS/ — official docs — 2014
[22] iBUG facial point annotations — https://ibug.doc.ic.ac.uk/resources/facial-point-annotations/ — official docs — unknown
[23] NeoLoc-68: 68-point neonatal facial landmark localisation — https://arxiv.org/pdf/2606.20823 — preprint — 2026
[24] librealsense2 markup_68.h source — https://docs.ros.org/en/kinetic/api/librealsense2/html/markup__68_8h_source.html — code docs — unknown
[25] PyImageSearch: Detect eyes, nose, lips, and jaw with dlib — https://pyimagesearch.com/2017/04/10/detect-eyes-nose-lips-jaw-dlib-opencv-python/ — blog — 2017
[26] PyImageSearch: (Faster) facial landmark detector with dlib — https://pyimagesearch.com/2018/04/02/faster-facial-landmark-detector-with-dlib/ — blog — 2018
[27] yakhyo/mediapipe-face-mesh-onnx README — https://github.com/yakhyo/mediapipe-face-mesh-onnx/blob/main/README.md — repo — unknown
[28] cornpip/mediapipe_face_mesh — https://github.com/cornpip/mediapipe_face_mesh — repo — unknown
[29] PeizhiYan/Mediapipe_2_Dlib_Landmarks — https://github.com/PeizhiYan/Mediapipe_2_Dlib_Landmarks/ — repo — unknown
[30] Google AI Edge Face Landmarker documentation — https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker — official docs — unknown
[31] MediaPipe Face Mesh docs — https://github.com/google-ai-edge/mediapipe/blob/master/docs/solutions/face_mesh.md?plain=1 — official docs — unknown
[32] Infinite 3D Landmarks: Improving Continuous 2D Facial Landmark Detection — https://arxiv.org/pdf/2405.20117 — preprint — 2024
[33] Proto-Former: Unified Facial Landmark Detection by Prototype Transformer — https://arxiv.org/abs/2510.15338 — preprint — 2025
[34] Comparison Study of Extraction Accuracy of 3D Facial Anatomical Landmarks Based on Non-Rigid Registration of Face Template — https://pmc.ncbi.nlm.nih.gov/articles/PMC10047049/ — paper — unknown
[35] Accuracy of Facial Digitization Using a New Mobile Device-Compatible 3D Scanner for Malocclusion — https://pmc.ncbi.nlm.nih.gov/articles/PMC13117559/ — paper — unknown
[36] 3D facial landmark detection under large yaw and expression variations — https://pubmed.ncbi.nlm.nih.gov/23681986/ — paper — unknown
[37] U-Net 3D facial landmark study, acromegaly (title not captured) — https://ncbi.nlm.nih.gov/pmc/articles/PMC10963813 — paper — unknown
[38] Accuracy and reliability of automated landmark identification on CBCT using Invivo software — https://pmc.ncbi.nlm.nih.gov/articles/PMC12418967/ — paper — 2025 (per harvest)
[39] CBCT 3D skeletal landmark reliability study (3 judges, 31 landmarks) — https://pmc.ncbi.nlm.nih.gov/articles/PMC8111847 — paper — unknown
[40] Observer Reliability of Three-Dimensional Cephalometric Landmark Identification on Cone-Beam CT — https://pmc.ncbi.nlm.nih.gov/articles/PMC2642991 — paper — unknown
[41] VGCLUB/facefit-mpfb (FaceFit MPFB2 add-on prototype) — https://github.com/VGCLUB/facefit-mpfb — repo — unknown
[42] H0wZy/captureforge (GPL-3.0 Blender face rig extension) — https://github.com/H0wZy/captureforge — repo — unknown
[54] MediaPipe Iris: Real-time Iris Tracking & Depth Estimation (Google Research blog) — https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/ — official docs — 2020

Eleven further harvested sources not used for claims (including the earlier draft's [16]–[21]) are numbered [43]–[53] in `research/sources/craniometric-landmarks.json`.

**Further reading (by name, not yet linked)**
- Farkas LG, *Anthropometry of the Head and Face*, 2nd ed., 1994; Farkas LG, Hreczko TA, Kolar JC, Munro IR, "Vertical and horizontal proportions of the face in young adult North American Caucasians: revision of neoclassical canons", Plast Reconstr Surg, 1985; Farkas LG et al., international anthropometric study of facial morphology in ethnic groups, J Craniofac Surg, 2005.
- Kolar JC, Salter EM, *Craniofacial Anthropometry*, 1997; Martin R, Saller K, *Lehrbuch der Anthropologie*, 1957.
- Swennen GRJ, Schutyser F, Hausamen JE, *Three-Dimensional Cephalometry: A Color Atlas and Manual*, 2006.
- Downs WB, "Variations in facial relationships", Am J Orthod, 1948; Steiner CC, "Cephalometrics for you and me", Am J Orthod, 1953; Legan HL, Burstone CJ, soft-tissue cephalometric analysis for orthognathic surgery, J Oral Surg, 1980; Holdaway RA, soft-tissue cephalometric analysis, Am J Orthod, 1983.
- Baumrind S, Frantz RC, "The reliability of head film measurements. 1. Landmark identification", Am J Orthod, 1971.
- Bookstein FL, *Morphometric Tools for Landmark Data*, 1991; Gunz P, Mitteroecker P, "Semilandmarks: a method for quantifying curves and surfaces", Hystrix, 2013.
- Moorrees CFA, Kean MR, natural head position in cephalometrics, Am J Phys Anthropol, 1958.
- Kazemi V, Sullivan J, "One Millisecond Face Alignment with an Ensemble of Regression Trees", CVPR 2014 (dlib); Kartynnik Y et al., "Real-time Facial Surface Geometry from Monocular Video on Mobile GPUs", 2019 (MediaPipe Face Mesh); Ablavatski A et al., MediaPipe Iris paper, 2020.
- Zhu X et al., "Face Alignment Across Large Poses: A 3D Solution", CVPR 2016; Bulat A, Tzimiropoulos G, "How far are we from solving the 2D & 3D Face Alignment problem?", ICCV 2017; Wu W et al., "Look at Boundary" (WFLW), CVPR 2018.
- Dodgson NA, "Variation and extrema of human interpupillary distance", Proc SPIE, 2004.

## Verification log (2026-11-20)

4 queued claims, 4 web searches used.

1. **Farkas/Martin-Saller gn = lowest midline chin point; living-subject FH via tragion and soft-tissue orbitale** — unconfirmed (left 🧠). Results showed generic definitions (gnathion/menton as lowest symphysis point; FH via orbitale plus porion or tragion) but no source quoting Farkas's gn or tragion-or′ construction could be tied to a specific URL. Nearest: https://columbia.edu/itc/hs/medical/humanAnatomy/yuan/craniologyISlides_files/slide0061.html (already [1]).
2. **Farkas young-adult North American White means (Table 2)** — unconfirmed (left 🧠). No table values retrieved; candidate full texts: https://pmc.ncbi.nlm.nih.gov/articles/PMC6571015 and https://pubmed.ncbi.nlm.nih.gov/26703056/ (already [17], [19]). Weinberg-type comparison confirms only that 3D norms differ considerably from Farkas.
3. **MediaPipe index map (1, 2, 168, 33/133, 362/263, 61/291, 0/17, 13/14, 152, 234/454, 468/473) and z relative** — unconfirmed (left 🧠). Only the 468 + 10 iris layout was re-seen (Google docs), already ✅. No index table or z-scale statement retrieved.
4. **Iris diameter 11.7 ± 0.5 mm as MediaPipe Iris assumption** — confirmed 📄 (one source): https://research.google/blog/mediapipe-iris-real-time-iris-tracking-depth-estimation/ [54]. The blog also reports 4.3% mean relative depth error (SD 2.4%), consistent with the ~±4% prior; the ±4% figure as a scale prior remains an inference.
