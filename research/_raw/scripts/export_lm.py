import json, math, runpy, sys
import numpy as np

ns = runpy.run_path("/tmp/claude-0/-home-user-minedesign/b0bfc7ad-f996-5fdb-831e-f158e8b6fceb/scratchpad/build_lm.py")
IDS, IDX, NAMES, MID, BIL = ns["IDS"], ns["IDX"], ns["NAMES"], ns["MID"], ns["BIL"]
results, base, dist_grad, TARGETS, RES = ns["results"], ns["base"], ns["dist_grad"], ns["TARGETS"], ns["RES"]
OUT = sys.argv[1]


def r1(v):
    return round(float(v), 1)


def r2(v):
    return round(float(v), 2)


DEFS = {
    "v": ("highest point of the head in the midline with the head in FH (hair compressed)", "III", "hidden by hair; silhouette only"),
    "tr": ("midline point of the hairline on the forehead", "III", "hair-dependent; never a scale anchor"),
    "g": ("soft-tissue glabella g': most prominent midline point between the brows", "III", "profile silhouette"),
    "n": ("soft-tissue nasion n': deepest midline point of the frontonasal curve (= sellion within ~0-5 mm)", "III", "profile; frontal by shading only"),
    "prn": ("pronasale: most anterior midline point of the nasal tip", "II", "profile; frontal position only"),
    "sn": ("subnasale: junction of columella and upper lip in the midline", "I", "profile and 3/4"),
    "ls": ("labrale superius: midpoint of the upper vermilion border", "I/II", "all views"),
    "sto": ("stomion: midline point of the lip junction, lips closed relaxed", "I", "all views"),
    "li": ("labrale inferius: midpoint of the lower vermilion border", "I/II", "all views"),
    "sl": ("sublabiale (soft-tissue B'): deepest midline point of the labiomental fold", "III", "profile"),
    "pg": ("soft-tissue pogonion pg': most anterior midline chin point in FH", "III", "profile"),
    "gn": ("soft-tissue gnathion gn' (cephalometric): midway pg'-me' on the chin contour", "III", "profile; definitions vary"),
    "me": ("soft-tissue menton me': lowest midline chin point in FH (= Farkas 'gn')", "III", "profile; frontal silhouette"),
    "op": ("opisthocranion: midline point of the occiput farthest from glabella", "III", "rear/profile silhouette; hair"),
    "t": ("tragion: notch at the upper margin of the tragus", "I", "profile, 3/4"),
    "or": ("soft-tissue orbitale or': skin over the lowest point of the infraorbital rim", "III", "palpation; profile shading"),
    "p": ("pupil centre (= corneal apex for depth), far gaze", "I", "all views"),
    "en": ("endocanthion: inner corner of the palpebral fissure", "I", "frontal, 3/4"),
    "ex": ("exocanthion: outer corner of the palpebral fissure", "I", "frontal, 3/4, profile"),
    "ps": ("palpebrale superius: highest point of the upper lid margin", "II", "frontal"),
    "pi": ("palpebrale inferius: lowest point of the lower lid margin", "II", "frontal"),
    "al": ("alare: most lateral point of the alar contour", "III", "frontal"),
    "ac": ("alar curvature (crest) point: most posterolateral point of the alar base groove", "I/III", "3/4, basal, profile"),
    "ch": ("cheilion: lip commissure", "I", "all views"),
    "zy": ("soft-tissue zygion zy': most lateral point over the zygomatic arch", "III", "frontal silhouette"),
    "go": ("soft-tissue gonion go': most lateral-inferior point of the jaw angle", "III", "frontal/3/4 silhouette; adiposity"),
    "sa": ("superaurale: highest point of the free margin of the auricle", "III", "profile"),
    "sba": ("subaurale: lowest point of the earlobe", "III", "profile, frontal"),
    "eu": ("euryon: most lateral point of the head (parietal)", "III", "frontal/top silhouette; hair"),
}

tables = []

# ---- frame definition
tables.append({
    "name": "head_frame_definition",
    "units": "-",
    "columns": ["item", "definition"],
    "rows": [
        ["origin", "midpoint of tragion_L and tragion_R"],
        ["x_axis", "unit vector tragion_R -> tragion_L (+x = subject's left = viewer's right)"],
        ["FH_plane", "plane through tragion_L, tragion_R and the midpoint of orbitale_L/orbitale_R (living-subject Frankfort horizontal)"],
        ["y_axis", "normal to FH plane, pointing up (toward vertex)"],
        ["z_axis", "x cross y: forward, out of the face toward a frontal camera (right-handed)"],
        ["units", "millimetres"],
        ["blender_mapping", "Blender X = x/1000, Blender Y = -z/1000, Blender Z = y/1000 (metres, Z-up, face looking -Y)"],
        ["flame_mapping", "FLAME: metres, +X subject's left, +Y up, face toward +Z: same axes as this frame, but origin and FH tilt must be re-solved"],
        ["engine_match", "matches face3d/synthetic.py conventions (+x subject's left, +y up, +z toward frontal camera, mm)"],
        ["renormalise", "after sampling or fitting, recompute the frame from the four frame landmarks and re-express all points"],
    ],
    "population": "-",
    "source_urls": [],
    "status": "knowledge",
    "notes": "Using tragion rather than bony porion makes the frame observable from photos; offset of t-or' line from bony po-or is a few degrees at most (unquantified here).",
})

# ---- landmark definitions
tables.append({
    "name": "landmark_definitions",
    "units": "-",
    "columns": ["id", "name", "bilateral", "definition", "bookstein_type", "observability"],
    "rows": [[k, NAMES[k], k in BIL, *DEFS[k]] for k in MID + BIL],
    "population": "-",
    "source_urls": [
        "https://columbia.edu/itc/hs/medical/humanAnatomy/yuan/craniologyISlides_files/slide0061.html",
        "https://nobellicense.nobelbiocare.com/help/d3d046fb-52e8-4b33-9f51-d3fd98ca3ed4/2.0/EN/3D_cephalometric_soft_tissue_landmarks.htm",
    ],
    "status": "knowledge",
    "notes": "FH and prn definitions are sourced; gn' vs me' naming is contested (Farkas 'gn' = lowest chin point = me' here). Bilateral ids carry suffix _L (+x) / _R (-x).",
})

# ---- mean coordinates with per-coordinate SD
for sex, label in (("M", "male"), ("F", "female")):
    R = results[sex]
    X, S = R["X"], R["S"]
    sd = np.sqrt(np.diag(S)).reshape(-1, 3)
    rows = []
    for i, k in enumerate(IDS):
        rows.append([k, NAMES[base(k)] + (k[-2:] if k.endswith(("_L", "_R")) else ""),
                     r1(X[i, 0]), r1(X[i, 1]), r1(X[i, 2]), r1(sd[i, 0]), r1(sd[i, 1]), r1(sd[i, 2])])
    tables.append({
        "name": f"mean_landmarks_{label}_european_young_adult",
        "units": "mm, FH head frame (origin mid-tragion; +x subject's left, +y up, +z forward)",
        "columns": ["id", "name", "x", "y", "z", "sd_x", "sd_y", "sd_z"],
        "rows": rows,
        "population": f"{label}, European-ancestry young adult (~18-35 y); synthesised to reproduce Farkas-NAW / ANSUR-type chords",
        "source_urls": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC3485457/table/Tab2", "https://arxiv.org/pdf/2304.07175"],
        "status": "knowledge",
        "notes": "Expert synthesis, NOT a published coordinate set. Only n-me mean and a few SDs are sourced. Profile depths (z) are the least certain values (+/-8 mm on the t->face offset). SDs are the square roots of the diagonal of the factor covariance below; SD 0 on tragion y/z is by frame construction. Replace with FLAME-2023-Open / 3DFN / CAESAR-derived values when computed.",
    })

# ---- distance check
for sex, label in (("M", "male"), ("F", "female")):
    pass
rows = []
for a, b, mM, sM, mF, sF, st in TARGETS:
    vals = []
    for sex in ("M", "F"):
        R = results[sex]
        L, g = dist_grad(R["X"], a, b)
        gv = g.reshape(-1)
        vals += [r1(L), r2(math.sqrt(gv @ R["S"] @ gv))]
    rows.append([f"{a}-{b}", vals[0], mM, vals[1], sM, vals[2], mF, vals[3], sF, st])
tables.append({
    "name": "model_vs_norm_chords",
    "units": "mm (3D chord)",
    "columns": ["measure", "model_M", "norm_M", "model_sd_M", "norm_sd_M", "model_F", "norm_F", "model_sd_F", "norm_sd_F", "norm_status"],
    "rows": rows,
    "population": "European-ancestry young adults",
    "source_urls": ["https://pmc.ncbi.nlm.nih.gov/articles/PMC3485457/table/Tab2", "https://arxiv.org/pdf/2304.07175"],
    "status": "knowledge",
    "notes": "Self-consistency check of the synthesised configuration and covariance against the norms it was calibrated to. n-me means and ex-ex / n-me SDs sourced; the rest recalled.",
})

# ---- tragion distances and depths
pairs = [("t_L", "n"), ("t_L", "g"), ("t_L", "sn"), ("t_L", "prn"), ("t_L", "ls"), ("t_L", "pg"), ("t_L", "gn"),
         ("t_L", "me"), ("t_L", "en_L"), ("t_L", "ex_L"), ("t_L", "al_L"), ("t_L", "ch_L"), ("t_L", "zy_L"), ("t_L", "go_L")]
rows = []
for a, b in pairs:
    row = [f"{a.replace('_L','')}-{b.replace('_L','')}"]
    for sex in ("M", "F"):
        R = results[sex]
        L, g = dist_grad(R["X"], a, b)
        gv = g.reshape(-1)
        dz = R["X"][IDX[b], 2] - R["X"][IDX[a], 2]
        row += [r1(L), r1(math.sqrt(gv @ R["S"] @ gv)), r1(dz)]
    rows.append(row)
tables.append({
    "name": "tragion_distances",
    "units": "mm",
    "columns": ["measure", "chord_M", "sd_M", "fh_depth_M", "chord_F", "sd_F", "fh_depth_F"],
    "rows": rows,
    "population": "European-ancestry young adults",
    "source_urls": [],
    "status": "contested",
    "notes": "chord = 3D tragion-to-landmark distance (Farkas-style t-n, t-sn, t-gn 'face depths'); fh_depth = forward distance in the FH frame (what perspective arithmetic needs). Derived from the synthesised configuration; plausible error +/-8 mm on depths. The library's earlier working value of 100 mm for prn-to-tragion depth is low for adult European males under this model (see note).",
})

rows = []
for k, lab in [("al_L", "alare"), ("ac_L", "alar crest (alar base)"), ("sn", "subnasale"), ("ls", "labrale superius"),
               ("n", "soft nasion"), ("g", "soft glabella"), ("p_L", "corneal apex / pupil"), ("en_L", "endocanthion"),
               ("or_L", "soft orbitale"), ("ch_L", "cheilion"), ("ex_L", "exocanthion"), ("pg", "soft pogonion"),
               ("me", "soft menton"), ("zy_L", "soft zygion"), ("go_L", "soft gonion"), ("t_L", "tragion"),
               ("sa_L", "superaurale"), ("op", "opisthocranion")]:
    row = [lab]
    for sex in ("M", "F"):
        R = results[sex]
        X, S = R["X"], R["S"]
        g = np.zeros_like(X); g[IDX["prn"], 2] = 1; g[IDX[k], 2] -= 1
        gv = g.reshape(-1)
        row += [r1(X[IDX["prn"], 2] - X[IDX[k], 2]), r1(math.sqrt(gv @ S @ gv))]
    rows.append(row)
rows.append(["cheek silhouette, frontal view, alar level (not a landmark)", 79.0, 9.0, 73.0, 8.5])
tables.append({
    "name": "profile_depths_behind_pronasale",
    "units": "mm along FH z (pronasale z minus landmark z)",
    "columns": ["landmark", "depth_M", "sd_M", "depth_F", "sd_F"],
    "rows": rows,
    "population": "European-ancestry young adults",
    "source_urls": [],
    "status": "contested",
    "notes": "Perspective depth levers. Library notes previously used alar base ~20, eye corners 35-45, cheek contour 60-80, tragion 90-120 (100 nominal); this model gives larger values for alar base, cheek and tragion. East Asian faces: subtract ~3-6 mm from radix/nasal-tip rows (lower projection).",
})

# ---- factor model
for sex, label in (("M", "male"), ("F", "female")):
    R = results[sex]
    rows = [[k, round(float(s), 4) if k == "size" else r2(s)] for k, s in zip(R["names"], R["sig"])]
    tables.append({
        "name": f"factor_sigmas_{label}",
        "units": "mm per unit loading (size: fractional CV)",
        "columns": ["factor", "sigma"],
        "rows": rows,
        "population": f"{label}, European-ancestry young adult",
        "source_urls": [],
        "status": "knowledge",
        "notes": "Factor SDs fitted (NNLS + ridge, floor 0.5x prior guess) so implied chord SDs reproduce recalled Farkas/ANSUR SDs. Covariance = L L^T + diag(residual^2) with L[:,k] = sigma_k * loading_k. Loadings are in table factor_loadings; 'size' loading = mean coordinates (isometric scaling about the mid-tragion origin).",
    })
R = results["M"]
rows = []
for k in R["names"]:
    if k == "size":
        rows.append([k, "*", "x", "y", "z", "loading = mean coordinate (isometric)"])
        continue
    Fk = R["F"][k]
    for i, lid in enumerate(IDS):
        if np.any(np.abs(Fk[i]) > 1e-9):
            rows.append([k, lid, r2(Fk[i, 0]), r2(Fk[i, 1]), r2(Fk[i, 2]), ""])
tables.append({
    "name": "factor_loadings",
    "units": "mm displacement per mm of factor sigma (unitless direction weights); lower_face_height and face_depth weights scale with position (shown for the male mean; recompute from female mean with the same rules)",
    "columns": ["factor", "landmark", "dx", "dy", "dz", "note"],
    "rows": rows,
    "population": "both sexes (rules identical; numeric weights shown for male mean)",
    "source_urls": [],
    "status": "knowledge",
    "notes": "Expert-structured integration factors (size, vertical face, facial depth, mandibular projection, widths, nose, orbit spacing, lips, mouth width, cephalic index, brow, upper-face height, ear length/protrusion, soft tissue, eye opening, vault). Rules: lower_face_height dy = -(y_n - y)/100 for lower-face points (chin dz = -0.15*that; gonion dy at half weight); face_depth dz = clip(z/100, 0, 1.25) for every non-ear/non-vault point.",
})
ASYM = ns["ASYM"]
rows = [[k, *RES[k], *([None, None, None] if k in MID else [min(a_, t_) for a_, t_ in zip(ASYM[k], RES[k])])] for k in MID + BIL]
tables.append({
    "name": "residual_sd",
    "units": "mm. total = residual SD per coordinate; asym = part independent per side (rest is shared mirror-symmetrically by L and R)",
    "columns": ["landmark", "sd_total_x", "sd_total_y", "sd_total_z", "sd_asym_x", "sd_asym_y", "sd_asym_z"],
    "rows": rows,
    "population": "both sexes",
    "source_urls": [],
    "status": "knowledge",
    "notes": "Includes landmark-definition noise for poorly defined points (v, tr, op, eu, zy, go, me). Tragion residual is zero because the frame is built on it. Residual covariance: diagonal total^2; between L and R of the same landmark, (total^2 - asym^2) with the x term negated (mirror symmetry). Midline x residual = lateral deviation of the midline.",
})

# ---- correlations among chords
sel = [("en_L", "en_R"), ("ex_L", "ex_R"), ("al_L", "al_R"), ("ch_L", "ch_R"), ("zy_L", "zy_R"), ("go_L", "go_R"),
       ("eu_L", "eu_R"), ("g", "op"), ("n", "sn"), ("sn", "me"), ("n", "me"), ("sn", "prn"), ("t_L", "prn"), ("sa_L", "sba_L")]
R = results["M"]
G = []
for a, b in sel:
    L, g = dist_grad(R["X"], a, b)
    G.append(g.reshape(-1))
G = np.array(G)
C = G @ R["S"] @ G.T
d = np.sqrt(np.diag(C))
Cr = C / np.outer(d, d)
labels = [f"{a.replace('_L','').replace('_R','')}-{b.replace('_L','').replace('_R','')}" for a, b in sel]
rows = [[labels[i]] + [r2(Cr[i, j]) for j in range(len(sel))] for i in range(len(sel))]
tables.append({
    "name": "implied_chord_correlations_male",
    "units": "Pearson r (linearised)",
    "columns": ["measure"] + labels,
    "rows": rows,
    "population": "male, European-ancestry young adult (female similar)",
    "source_urls": [],
    "status": "knowledge",
    "notes": "Implied by the factor covariance; expected empirical ranges: widths among widths r~0.3-0.6, heights among heights 0.4-0.8 (nested chords higher), width-height 0.1-0.35, en-en weakly coupled (~0.1-0.3). Replace with a FLAME/3DFN-derived covariance when available.",
})

json.dump({"tables": tables, "ids": IDS}, open(OUT, "w"))
print("ok", len(tables))
print("corr labels", labels)
for r in rows:
    print(r)
