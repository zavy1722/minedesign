# Hard- and soft-tissue anthropometric landmarks

> Craniofacial landmarks come in two layers: hard-tissue (bony) points such as nasion, glabella, orbitale, porion, zygion, gonion, pogonion and menton, which are invisible in photographs, and soft-tissue points such as subnasale, pronasale, labiale superius, stomion, soft-tissue pogonion/gnathion, the eye canthi, cheilion, alare and tragion, which a photo→3D tool can actually observe. Most definitions are *extremal* ("most anterior", "lowest", "most lateral"), so they are only meaningful after a canonical head frame is fixed; the classic frame is the Frankfort horizontal through porion and orbitale. Several standard points (gonion, soft-tissue gnathion, stomion, alare) have competing constructions across protocols, so a tool must pin one definition per landmark and record which one it used. The iBUG 68-point detector scheme is an annotation convention, not an anatomical one: its jaw and brow points are placed by spacing rules, so only some of its points correspond to named anatomical landmarks. **Verification caveat:** in this session the shared web-search budget was already used up and direct page fetches were blocked, so no claim below could be independently re-checked. Every fact is therefore single-source (⚠️) or contested (↔️), and no mm norms or MediaPipe 478 mapping could be sourced.

## Key facts

Badge legend: ⚠️ means "taken from harvested search snippets, not independently re-verified here". Where two papers are cited, both came from the same harvest and the attribution was inferred from snippets, not from reading the full text.

**Hard tissue (bony)**
- **Nasion (n)**: junction of the nasal and frontal bones at the root of the nose, where the frontonasal suture meets the midline [1] ⚠️
- **Glabella (g)**: the most prominent point between the eyebrows, above the nasal root [1] ⚠️
- **Orbitale (or)**: the lowest point of the bony orbital rim. With porion it defines the **Frankfort horizontal (FH)** [1] ⚠️
- **Porion (po)**: the highest point on the roof of the external auditory meatus (ear canal) [2] ⚠️
- **Zygion (zy)**: the most lateral point on the zygomatic arch [1] ⚠️
- **Pogonion (pog)**: the most anterior midline point of the bony chin. **Menton (me)**: the lowest midline point of the chin on the mandibular symphysis [1] ⚠️
- **Gonion (go)**: the outermost posterior point of the mandibular angle. Its *construction* differs: one protocol uses the bisector of the angle between the ramus and body lines [2], another the intersection of tangents to the ramus and the corpus [3] ↔️

**Soft tissue (skin surface)**
- **Subnasale (sn)**: the point where the columella meets the upper lip in the midsagittal plane [9][4] ⚠️
- **Pronasale (prn)**: the most protruded (most anterior) midpoint of the nasal tip [9][4] ⚠️
- **Labiale superius (ls)**: the midpoint of the upper-lip vermilion line [7][8] ⚠️
- **Stomion (sto)**: the midline point of the labial fissure with the lips closed naturally. Some protocols split it into superior and inferior stomion (superior = the lowest point of the upper lip in the midsagittal plane) [7][8] ↔️
- **Soft-tissue pogonion (pg′/Pog′)**: the most anterior midpoint of the soft-tissue chin in the midsagittal plane [7][8] ⚠️
- **Soft-tissue gnathion (gn′/Gn′)** has two definitions. The *orientation-based* one is the midpoint between the most anterior and most inferior points of the soft-tissue chin. The *curve-based* one is the lowest point of the mental soft tissue in the midsagittal plane. The curve-based point lies slightly lower [7][8] ↔️
- **Endocanthion (en)**: the most medial point of the palpebral fissure at the inner commissure. It is best seen with the subject gazing upward [5][6] ⚠️
- **Exocanthion (ex)**: the most lateral point of the palpebral fissure at the outer canthus [5][6] ⚠️
- en and ex **cannot be located when the eyes are closed**, which happens often in laser scans [10] ⚠️
- **Cheilion (ch)**: the outer corner of the mouth, where the outer edges of the upper and lower vermilion meet [5] ⚠️
- **Alare (al)**: the most lateral point of the nasal ala. A separate *skeletal* alare exists in 3D studies, so the tissue level must always be stated [5][4] ⚠️
- **Tragion (t)**: the superior notch of the auricular tragus [5] ⚠️
- The same landmark name (e.g. gnathion, stomion) can be constructed differently in different protocols, so check the protocol before comparing measurements across studies [7][8] ⚠️

**Detector schemes**
- The 300-W challenge faces were annotated with the **68-point** frontal-face markup also used in Multi-PIE. 300-W popularised the 68-point scheme [11][12] ⚠️ (both pages are from the same lab, so this is one origin)
- A 68-point iBUG layout can be derived from WFLW annotations by keeping every other jawline point and removing the extra lower-eyebrow points [14] ⚠️
- The librealsense2 header `markup_68.h` gives named indices for the 68 points (e.g. `JAW_FROM`, `CHIN`, `LEFT_EYEBROW_L`, `NOSE_TIP`) [15] ⚠️
- Jawline and eyebrow point placement varies between datasets. Some projects space the jawline points evenly along the chin and place brow points at the arc centre, bottom or top [13] ⚠️

## Numbers & reference tables

The harvested sources contain **no population norms (mm, angles, sample sizes)**. The only sourced number is the 68-point count. The tables below are categorical registries that a program can use directly.

**Table 1 — Landmark registry (sourced definitions)**

| Abbr. | Name | Tissue | Midline / bilateral | Definition type | Seen in a frontal photo?* | Src | Status |
|---|---|---|---|---|---|---|---|
| n | Nasion | hard | midline | suture junction | no (soft proxy n′) | [1] | ⚠️ |
| g | Glabella | hard | midline | extremal, anterior | no (soft proxy g′) | [1] | ⚠️ |
| or | Orbitale | hard | bilateral | extremal, inferior | no | [1] | ⚠️ |
| po | Porion | hard | bilateral | extremal, superior | no | [2] | ⚠️ |
| zy | Zygion | hard | bilateral | extremal, lateral | partly (cheek contour) | [1] | ⚠️ |
| go | Gonion | hard | bilateral | constructed | partly (jaw contour) | [2][3] | ↔️ |
| pog | Pogonion | hard | midline | extremal, anterior | no | [1] | ⚠️ |
| me | Menton | hard | midline | extremal, inferior | no | [1] | ⚠️ |
| sn | Subnasale | soft | midline | junction | yes (needs profile for depth) | [9][4] | ⚠️ |
| prn | Pronasale | soft | midline | extremal, anterior | yes (needs profile for depth) | [9][4] | ⚠️ |
| ls | Labiale superius | soft | midline | contour midpoint | yes | [7][8] | ⚠️ |
| sto | Stomion | soft | midline | fissure midpoint | yes (lips closed only) | [7][8] | ↔️ |
| pg′ | Soft-tissue pogonion | soft | midline | extremal, anterior | profile only | [7][8] | ⚠️ |
| gn′ | Soft-tissue gnathion | soft | midline | constructed / curve | profile only | [7][8] | ↔️ |
| en | Endocanthion | soft | bilateral | extremal, medial | yes (eyes open) | [5][6] | ⚠️ |
| ex | Exocanthion | soft | bilateral | extremal, lateral | yes (eyes open) | [5][6] | ⚠️ |
| ch | Cheilion | soft | bilateral | junction | yes | [5] | ⚠️ |
| al | Alare (soft) | soft | bilateral | extremal, lateral | yes | [5][4] | ⚠️ |
| t | Tragion | soft | bilateral | notch | profile / ¾ only | [5] | ⚠️ |

*The visibility column is the author's inference from each definition, not a sourced claim.

**Table 2 — Landmarks in the brief with NO source captured this session (working definitions only; do not hard-code)**

| Abbr. | Name | Conventional working definition (unsourced) | What to verify |
|---|---|---|---|
| n′ | Soft-tissue nasion | the deepest point of the soft-tissue concavity at the nasal root, *or* the skin point overlying n (both conventions are in use) | which one [4] adopts |
| li | Labiale inferius | the midpoint of the lower-lip vermilion line (mirror of ls) | the exact wording |
| tr | Trichion | the midline point of the frontal hairline | how variable hairlines are handled |
| v | Vertex | the highest point of the head in the midsagittal plane, with the head in FH | the head-orientation requirement |
| g′, me′ | Soft-tissue glabella / menton | soft-tissue counterparts of g / me | the definitions |

**Table 3 — Detector schemes**

| Scheme | Points | Anatomical correspondence | Source | Status |
|---|---|---|---|---|
| iBUG 300-W / Multi-PIE | 68 | partial: eye and mouth corners and the nose tip are near-anatomical; jaw and brows are by convention | [11][12][13][15] | ⚠️ |
| WFLW → iBUG-68 | convertible to 68 | the conversion drops alternate jaw points and extra lower-brow points | [14] | ⚠️ |
| MediaPipe Face Mesh | 478 (figure from the project brief, not verified) | not sourced here | — | unverified |

**Table 4 — Definition conflicts that change coordinates**

| Landmark | Variant A | Variant B | Effect |
|---|---|---|---|
| go | bisector of the ramus/body angle [2] | intersection of the ramus and corpus tangents [3] | different points on or near the angle |
| gn′ | midpoint of the anterior-most and inferior-most chin points [7][8] | lowest point of the mental soft tissue [7][8] | B lies slightly lower (not quantified) |
| sto | the labial fissure midpoint | superior (and inferior) stomion [7][8] | separate points when the lips are apart |
| al | soft-tissue alar point [5] | skeletal alare [4] | a different tissue layer |

## Applying this to photo→3D face sculpting in Blender

1. **Capture to the definitions.** Use eyes-open photos with a neutral-to-slightly-upward gaze (en is best seen when gazing up [5][6]; en/ex are lost with closed eyes [10]). Keep the lips *closed naturally* (sto is defined only for this state [7][8]) and the ears uncovered (t is the tragal notch [5]). Add a true profile shot: prn, sn, pg′, gn′ and n′ are midsagittal "most anterior/lowest" points, and their depth cannot be recovered from a frontal view alone.
2. **Fix the head frame before placing anything.** Every extremal definition (or = lowest, po = highest, prn = most anterior, zy = most lateral) depends on orientation. The anatomical standard is FH through po and or [1]. In photos neither is visible, so use tragion as the posterior proxy and the soft tissue under the lower orbital rim as the anterior proxy. Make the mesh's midsagittal plane x = 0 and the FH plane parallel to Blender's XY plane. The po→t and or→soft-tissue offsets are **not quantified in any source gathered here**, so treat the proxy frame as approximate.
3. **Use named empties with the standard abbreviations** (`prn`, `sn`, `ls`, `sto`, `pg_soft`, `gn_soft`, `en.L/.R`, `ex.L/.R`, `ch.L/.R`, `al.L/.R`, `t.L/.R`) parented to the head. Blender's `.L/.R` suffixes allow mirrored editing, but measure each side separately rather than forcing symmetry.
4. **Compare ratios, not raw mm.** A single photo has no absolute scale. Check proportions between photo and mesh: ch–ch vs en–en vs ex–ex, al–al vs en–en, the sn–sto–gn′ vertical thirds, and the prn projection relative to sn in profile. Absolute scale needs a measured reference on the subject. No reference size is sourced here.
5. **Bone points belong on the skull, skin points on the skin.** If you sculpt over a skull base mesh, place n, g, or, po, zy, go, pog and me on the bone and their soft-tissue counterparts on the skin. The gap between them is soft-tissue thickness, which is a separate topic and not covered here.
6. **What goes wrong:**
   - The 68-point jawline is *not* go. Jaw points are spaced evenly along the contour [13], so the "angle" point of a detector sits wherever the spacing puts it.
   - The 68-point "CHIN" [15] is ambiguous between pg′, gn′ and me′.
   - Brow points sit at the arc centre, bottom or top depending on the dataset [13], so they say little about glabella or brow-ridge projection.
   - Slightly parted lips silently move sto.
   - Mixing a gonion construction from one protocol with norms from another produces false "errors" [2][3].

## Algorithmic implications

- **Landmark schema.** Store per landmark: `abbr`, `tissue ∈ {hard, soft}`, `symmetry ∈ {midline, L, R}`, `def_type ∈ {extremal(dir), junction, contour_midpoint, constructed, notch}`, `variant` (e.g. `go:bisector|tangent_intersection`, `gn_soft:orientation|curve`, `sto:fissure|superior|inferior`), `frame_required`, `visibility_conditions` (eyes_open, lips_closed, ear_visible, profile_view), `source_ids`. Never compare two landmarks whose `variant` differs.
- **Frame first, extremes second.** Fit the midsagittal plane (from bilateral pairs: en, ex, ch, al, t) and the FH proxy (t + infraorbital soft point), then compute extremal landmarks as `argmax(dot(v, dir))` over a region mask. Midline landmarks should be restricted to a narrow band around the midsagittal plane. If the frame is re-estimated, recompute the extremal landmarks rather than keeping cached vertices.
- **Constructed landmarks as functions.** Implement go as a function of fitted ramus and body lines (both variants, with one configurable default), and gn′ as a function of pg′, me′ and the chin curve. Report both variants when they disagree beyond a tolerance.
- **Detector-to-anatomy correspondence types.** Treat 68-point eye corners, mouth corners and the nose tip as *point* correspondences (to en/ex, ch, prn). Treat the jaw contour points (evenly spaced by convention [13]) and brows as *semi-landmarks*: use a point-to-curve or sliding loss, not point-to-point. Give brows a low weight for any bony prior.
- **Visibility gating.** Drop en/ex constraints when an eye-openness test fails [10], and drop sto when the lips are apart. Midline depth landmarks (prn, sn, pg′, gn′) should be inactive unless a profile or ¾ view or a depth source exists.
- **No hard-coded norms.** The harvested sources gave no population means or SDs. Leave anthropometric priors as pluggable tables (population, sex, age, n) and default to *ratio* constraints until sourced norms are added.
- **Uncertainty.** Carry a per-landmark positional variance. 3D reliability studies exist [5][6], but their error values were not captured. Until they are, weight extremal points on broad, gently curved regions (e.g. pg′) lower than sharp junctions (ch, en, sn).
- **MediaPipe 478.** Build an explicit `mediapipe_index → anatomical_abbr` table empirically (place the anatomical definitions on the canonical mesh and pick the nearest vertex), version it with the model, and validate it on scans. No sourced mapping exists in this note.

## Disagreements, myths & refuted claims

- **Gonion**: bisector construction [2] vs tangent intersection [3]. ↔️
- **Soft-tissue gnathion**: orientation-based vs curve-based. The curve-based point is lower, by an amount not quantified in the harvest [7][8]. ↔️
- **Stomion**: a single labial-fissure midpoint vs separate superior and inferior stomion [7][8]. ↔️
- **Alare**: soft-tissue vs skeletal usage of the same name [5][4]. Always qualify it.
- **Pitfall (inference, not a sourced claim): "the detector jaw corner = gonion."** Because jaw points are placed by spacing [13], this equivalence is not supported.
- **Removed from the main text:** the harvester's 1-based 68-point index ranges (jaw 1–17, brows 18–27, nose 28–36, eyes 37–48, mouth 49–68). The harvester said they came from general knowledge, and they could not be checked here, so they are listed only in Open questions.
- **Refuted:** none. No independent check could run, so nothing could be confirmed or refuted.

## Open questions

- **Verification debt.** Every ⚠️ item needs one independent confirmation, ideally from Farkas-style anthropometry definitions or the full text of [4].
- **68-point indices.** Confirm the index ranges listed above against `markup_68.h` [15] or the 300-W figure [11], including whether the indexing is 0- or 1-based.
- **MediaPipe Face Mesh (the brief's 478 points, including how the iris points are split out).** Find an official topology and any published landmark↔vertex mapping.
- **Unsourced definitions:** n′, li, tr, v, g′, me′ (Table 2).
- **Metric data:** population mm norms (e.g. en–en, ex–ex, al–al, ch–ch, n–sn, sn–me′) with sample size and ancestry; inter-observer and scanner error per landmark (likely in [5][6][8]); the size of the gn′ variant offset.
- **Proxy offsets:** po vs t, and or vs the infraorbital skin point, for building FH from photos.
- **Harvested but unread:** [16]–[21]. These include frontal-photo cephalometric landmark detection [17], 3D facial asymmetry [20] and 3D normotypes for priors [21]. Publication years for most PMC items were not captured.

## Sources

[1] Columbia University craniology lecture slides (landmark definitions) — https://columbia.edu/itc/hs/medical/humanAnatomy/yuan/craniologyISlides_files/slide0061.html — lecture slides — unknown
[2] BMC Oral Health, landmark abbreviation/definition table (s12903-024-04260-3) — https://bmcoralhealth.biomedcentral.com/articles/10.1186/s12903-024-04260-3/tables/1 — paper — 2024
[3] BMC Oral Health, landmark sign/name/definition table (s12903-022-02179-1) — https://bmcoralhealth.biomedcentral.com/articles/10.1186/s12903-022-02179-1/tables/1 — paper — 2022
[4] The definitions of three-dimensional landmarks on the human face: an interdisciplinary view — https://pmc.ncbi.nlm.nih.gov/articles/PMC4832301/ — paper — unknown
[5] The Reliability of Three-Dimensional Landmark-Based Craniomaxillofacial and Airway Cephalometric Analysis — https://pmc.ncbi.nlm.nih.gov/articles/PMC10377994/ — paper — unknown
[6] Facial Landmarks Determination with Different Digital Scanners: An In Vivo Study — https://pmc.ncbi.nlm.nih.gov/articles/PMC12941515/ — paper — unknown
[7] Soft-Tissue Analysis of Different Sagittal Skeletal Patterns Using the Geometric Morphometric Method — https://pmc.ncbi.nlm.nih.gov/articles/PMC9949938/ — paper — unknown
[8] Accuracy of AI-assisted soft tissue landmark identification in serial lateral cephalograms of Class III two-jaw surgery patients — https://pmc.ncbi.nlm.nih.gov/articles/PMC12460026/ — paper — unknown
[9] A rapid identification method for soft tissue markers of dentofacial deformities based on heatmap regression — https://pmc.ncbi.nlm.nih.gov/articles/PMC10907697/ — paper — unknown
[10] PMC4246044 (3D facial-scan landmark article; title not captured by the harvester) — https://pmc.ncbi.nlm.nih.gov/articles/PMC4246044 — paper — unknown
[11] 300 Faces In-the-Wild Challenge (300-W), ICCV 2013, iBUG — https://ibug.doc.ic.ac.uk/resources/300-W — official docs — 2013
[12] 300 Faces In-The-Wild Challenge (300-W), IMAVIS 2014, iBUG — https://ibug.doc.ic.ac.uk/resources/300-W_IMAVIS/ — official docs — 2014
[13] iBUG facial point annotations — https://ibug.doc.ic.ac.uk/resources/facial-point-annotations/ — official docs — unknown
[14] NeoLoc-68: 68-point neonatal facial landmark localisation (WFLW→iBUG-68 conversion) — https://arxiv.org/pdf/2606.20823 — paper (preprint) — 2026
[15] librealsense2 markup_68.h source (named 68-point iBUG layout) — https://docs.ros.org/en/kinetic/api/librealsense2/html/markup__68_8h_source.html — repo/code docs — unknown
[16] Zafeiriou et al., The Menpo Facial Landmark Localisation Challenge, CVPRW 2017 — https://openaccess.thecvf.com/content_cvpr_2017_workshops/w33/papers/Zafeiriou_The_Menpo_Facial_CVPR_2017_paper.pdf — paper — 2017 (harvested, not used for claims)
[17] Automatic cephalometric landmarks detection on frontal faces: supervised learning approach — https://arxiv.org/pdf/1904.10816 — paper (preprint) — 2019 (harvested, not used for claims)
[18] PMC12334920 Table 1 (landmark table) — https://pmc.ncbi.nlm.nih.gov/articles/PMC12334920/table/T1 — paper — unknown (harvested, not used)
[19] The Facial Morphology in Down Syndrome: A 3D Comparison of Patients with and without Obstructive Sleep Apnea — https://pmc.ncbi.nlm.nih.gov/articles/PMC5650534/ — paper — unknown (harvested, not used)
[20] Facial asymmetry in young healthy subjects evaluated by statistical shape analysis — https://pmc.ncbi.nlm.nih.gov/articles/PMC2666135/ — paper — unknown (harvested, not used)
[21] 3D Facial Normotypes for Maxillofacial Surgical Planning — https://pmc.ncbi.nlm.nih.gov/articles/PMC13666107 — paper — unknown (harvested, not used)
