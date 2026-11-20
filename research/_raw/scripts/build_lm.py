"""Build the metric 3D landmark prior (expert-synthesised) and calibrate a factor covariance.

Frame: Frankfort-horizontal head frame, mm. Origin = midpoint of tragia.
+x = subject's left, +y = up (normal to FH), +z = forward (anterior).
"""
import json, math
import numpy as np

MID = ["v", "tr", "g", "n", "prn", "sn", "ls", "sto", "li", "sl", "pg", "gn", "me", "op"]
BIL = ["t", "or", "p", "en", "ex", "ps", "pi", "al", "ac", "ch", "zy", "go", "sa", "sba", "eu"]

NAMES = {
    "v": "vertex", "tr": "trichion", "g": "glabella", "n": "nasion", "prn": "pronasale",
    "sn": "subnasale", "ls": "labrale_superius", "sto": "stomion", "li": "labrale_inferius",
    "sl": "sublabiale", "pg": "pogonion", "gn": "gnathion", "me": "menton", "op": "opisthocranion",
    "t": "tragion", "or": "orbitale", "p": "pupil", "en": "endocanthion", "ex": "exocanthion",
    "ps": "palpebrale_superius", "pi": "palpebrale_inferius", "al": "alare", "ac": "alar_curvature",
    "ch": "cheilion", "zy": "zygion", "go": "gonion", "sa": "superaurale", "sba": "subaurale",
    "eu": "euryon",
}

# Mean configurations (bilateral given for the subject's LEFT, +x). mm.
MALE = {
    "v": (0, 130, 0), "tr": (0, 80, 86), "g": (0, 33, 99), "n": (0, 21, 94),
    "prn": (0, -21.5, 119), "sn": (0, -32.5, 102), "ls": (0, -46, 105), "sto": (0, -54.5, 101.5),
    "li": (0, -64.5, 103), "sl": (0, -75, 94), "pg": (0, -88, 95), "gn": (0, -96, 90),
    "me": (0, -100, 82), "op": (0, 40, -98),
    "t": (72.5, 0, 0), "or": (33, 0, 78), "p": (32, 14, 82), "en": (16.5, 13, 77),
    "ex": (45, 16, 67), "ps": (31, 18.5, 80.5), "pi": (32, 9, 79.5), "al": (17.5, -27.5, 96),
    "ac": (15, -30.5, 90), "ch": (26.5, -53.5, 86), "zy": (70.5, -3, 27), "go": (54, -64, 17),
    "sa": (80, 29, -12), "sba": (76, -34, -3), "eu": (76, 68, -20),
}
FEMALE = {
    "v": (0, 126, 0), "tr": (0, 76, 81), "g": (0, 30, 91), "n": (0, 19, 88),
    "prn": (0, -20, 111), "sn": (0, -31, 95), "ls": (0, -43.5, 98), "sto": (0, -51, 95),
    "li": (0, -60.5, 96), "sl": (0, -69.5, 89), "pg": (0, -80.5, 89), "gn": (0, -87.5, 84),
    "me": (0, -92, 77), "op": (0, 38, -96),
    "t": (68.5, 0, 0), "or": (31.5, 0, 73), "p": (31, 13, 77), "en": (16, 12, 72),
    "ex": (43.5, 15, 62.5), "ps": (30, 17.5, 75.5), "pi": (31, 8, 74.5), "al": (15.7, -26, 89.5),
    "ac": (13.5, -29, 84), "ch": (25, -50, 81), "zy": (66, -3, 25), "go": (50, -58, 16),
    "sa": (75.5, 27, -11), "sba": (72, -32, -3), "eu": (72.5, 63, -18),
}

IDS = MID + [b + s for b in BIL for s in ("_L", "_R")]
IDX = {k: i for i, k in enumerate(IDS)}


def config(d):
    X = np.zeros((len(IDS), 3))
    for k in MID:
        X[IDX[k]] = d[k]
    for b in BIL:
        x, y, z = d[b]
        X[IDX[b + "_L"]] = (x, y, z)
        X[IDX[b + "_R"]] = (-x, y, z)
    return X


def sgn(i):
    k = IDS[i]
    return 1.0 if k.endswith("_L") else (-1.0 if k.endswith("_R") else 0.0)


def base(k):
    return k[:-2] if k.endswith(("_L", "_R")) else k


# ---------- factor loadings (per +1 SD, before sigma) ----------
def factors(X):
    n = len(IDS)
    F = {}

    def new():
        return np.zeros((n, 3))

    # 1 isometric size about the tragion-midpoint origin (sigma = CV)
    F["size"] = X.copy()
    # 2 lower-face height (long vs short face), per 100 mm below nasion
    L = new(); yn = X[IDX["n"], 1]
    face = {"prn", "sn", "ls", "sto", "li", "sl", "pg", "gn", "me", "al", "ac", "ch"}
    for i, k in enumerate(IDS):
        b = base(k)
        if b in face:
            dyf = (yn - X[i, 1]) / 100.0
            L[i, 1] = -dyf
            if b in {"pg", "gn", "me", "sl"}:
                L[i, 2] = -0.15 * dyf
        if b == "go":
            L[i, 1] = -0.5 * (yn - X[i, 1]) / 100.0
    F["lower_face_height"] = L
    # 3 facial depth relative to the ears (whole face forward/back)
    L = new()
    for i, k in enumerate(IDS):
        b = base(k)
        if b in {"t", "sa", "sba", "eu", "op", "v"}:
            continue
        L[i, 2] = float(np.clip(X[i, 2] / 100.0, 0, 1.25))
    F["face_depth"] = L
    # 4 mandibular projection
    L = new()
    w = {"pg": 1.0, "gn": 1.0, "me": 1.0, "sl": 0.9, "li": 0.6, "sto": 0.3, "ch": 0.2}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 2] = w[base(k)]
    F["mandible_projection"] = L
    # 5 bizygomatic / bigonial / bitragal width
    L = new()
    w = {"zy": 1.0, "go": 0.8, "t": 1.0, "eu": 0.6, "sa": 1.0, "sba": 1.0, "ex": 0.35, "p": 0.2, "or": 0.3, "ch": 0.15}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 0] = sgn(i) * w[base(k)]
    F["face_width"] = L
    # 6 nasal projection / size
    L = new()
    L[IDX["prn"]] = (0, -0.25, 1.0)
    L[IDX["sn"], 2] = 0.15
    L[IDX["n"], 2] = 0.3
    for s in ("_L", "_R"):
        L[IDX["al" + s]] = (sgn(IDX["al" + s]) * 0.3, 0, 0.4)
        L[IDX["ac" + s], 0] = sgn(IDX["ac" + s]) * 0.25
    F["nose_projection"] = L
    # 7 nasal width
    L = new()
    for s in ("_L", "_R"):
        L[IDX["al" + s], 0] = sgn(IDX["al" + s]) * 1.0
        L[IDX["ac" + s], 0] = sgn(IDX["ac" + s]) * 0.9
    F["nose_width"] = L
    # 8 interorbital spacing
    L = new()
    w = {"en": 1.0, "p": 0.9, "ps": 0.8, "pi": 0.8, "ex": 0.6, "or": 0.6}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 0] = sgn(i) * w[base(k)]
    F["interorbital"] = L
    # 9 lip fullness / protrusion
    L = new()
    L[IDX["ls"]] = (0, 0.0, 1.0)
    L[IDX["li"]] = (0, 0.0, 1.0)
    L[IDX["sto"], 2] = 0.7
    for s in ("_L", "_R"):
        L[IDX["ch" + s], 2] = 0.3
    F["lips"] = L
    # 10 mouth width
    L = new()
    for s in ("_L", "_R"):
        L[IDX["ch" + s], 0] = sgn(IDX["ch" + s])
    F["mouth_width"] = L
    # 11 cephalic index (broad-short vs narrow-long vault)
    L = new()
    for s in ("_L", "_R"):
        L[IDX["eu" + s], 0] = sgn(IDX["eu" + s])
    L[IDX["op"], 2] = 1.5
    L[IDX["v"], 1] = 0.3
    F["cephalic_index"] = L
    # 12 brow / glabella projection
    L = new()
    L[IDX["g"], 2] = 1.0
    L[IDX["n"], 2] = 0.4
    L[IDX["tr"], 2] = 0.4
    F["brow_projection"] = L
    # 13 upper-face height (nasion/eyes above FH)
    L = new()
    w = {"n": 1.0, "g": 1.0, "tr": 1.0, "en": 0.5, "ex": 0.5, "p": 0.5, "ps": 0.5, "pi": 0.5}
    for i, k in enumerate(IDS):
        if base(k) in w:
            L[i, 1] = w[base(k)]
    F["upper_face_height"] = L
    # 14 ear length
    L = new()
    for s in ("_L", "_R"):
        L[IDX["sa" + s], 1] = 1.0
        L[IDX["sba" + s], 1] = -1.0
    F["ear_length"] = L
    # 15 ear protrusion
    L = new()
    for s in ("_L", "_R"):
        L[IDX["sa" + s], 0] = sgn(IDX["sa" + s])
        L[IDX["sba" + s], 0] = sgn(IDX["sba" + s]) * 0.6
    F["ear_protrusion"] = L
    # 16 soft-tissue / adiposity
    L = new()
    for s in ("_L", "_R"):
        L[IDX["go" + s], 0] = sgn(IDX["go" + s]) * 1.0
        L[IDX["zy" + s], 0] = sgn(IDX["zy" + s]) * 0.5
        L[IDX["ch" + s], 0] = sgn(IDX["ch" + s]) * 0.2
    L[IDX["me"], 1] = -0.5
    L[IDX["gn"], 1] = -0.3
    F["soft_tissue"] = L
    # 17 eye opening
    L = new()
    for s in ("_L", "_R"):
        L[IDX["ps" + s], 1] = 1.0
        L[IDX["pi" + s], 1] = -0.4
    F["eye_opening"] = L
    # 18 vault height
    L = new()
    L[IDX["v"], 1] = 1.0
    L[IDX["tr"], 1] = 0.5
    for s in ("_L", "_R"):
        L[IDX["eu" + s], 1] = 0.5
    F["vault_height"] = L
    return F


# residual SD per landmark base, (x, y, z), mm
RES = {
    "v": (2.0, 1.5, 12.0), "tr": (1.0, 8.0, 3.0), "g": (0.8, 4.0, 1.0), "n": (0.6, 2.0, 1.2),
    "prn": (0.8, 1.5, 1.2), "sn": (0.6, 1.2, 1.2), "ls": (0.6, 1.0, 0.8), "sto": (0.6, 1.0, 0.8),
    "li": (0.6, 1.0, 0.9), "sl": (0.6, 2.0, 1.5), "pg": (0.8, 2.0, 1.5), "gn": (0.8, 1.5, 1.5),
    "me": (1.0, 2.0, 3.0), "op": (1.5, 10.0, 1.5),
    "t": (0.0, 0.0, 0.0), "or": (1.0, 1.0, 1.5), "p": (0.5, 0.8, 1.0), "en": (0.6, 0.8, 1.2),
    "ex": (0.8, 1.0, 1.5), "ps": (0.6, 0.6, 1.0), "pi": (0.6, 0.6, 1.0), "al": (0.6, 1.2, 1.5),
    "ac": (0.6, 1.2, 1.5), "ch": (0.8, 1.2, 1.5), "zy": (1.0, 4.0, 5.0), "go": (1.5, 3.0, 4.0),
    "sa": (1.0, 1.5, 3.0), "sba": (1.0, 1.5, 3.0), "eu": (1.0, 12.0, 12.0),
}

# asymmetric (independent per side) share of the bilateral residual SD, mm per axis
ASYM = {b: (0.6, 0.6, 0.8) for b in BIL}
ASYM.update({"zy": (1.2, 1.2, 1.5), "go": (1.2, 1.5, 1.5), "sa": (1.2, 1.2, 1.5), "sba": (1.2, 1.2, 1.5),
             "eu": (1.2, 2.0, 2.0), "or": (0.8, 0.8, 1.0), "t": (0.0, 0.0, 0.0)})


def residual_cov():
    n = len(IDS)
    D = np.zeros((3 * n, 3 * n))
    for i, k in enumerate(IDS):
        b = base(k)
        tot = np.array(RES[b], float)
        if b in MID:
            D[3 * i:3 * i + 3, 3 * i:3 * i + 3] = np.diag(tot ** 2)
            continue
        asy = np.minimum(np.array(ASYM[b], float), tot)
        sym2 = tot ** 2 - asy ** 2
        D[3 * i:3 * i + 3, 3 * i:3 * i + 3] = np.diag(tot ** 2)
        if k.endswith("_L"):
            j = IDX[b + "_R"]
            # symmetric component: mirrored x (anti-correlated), equal y and z
            c = np.diag(sym2 * np.array([-1.0, 1.0, 1.0]))
            D[3 * i:3 * i + 3, 3 * j:3 * j + 3] = c
            D[3 * j:3 * j + 3, 3 * i:3 * i + 3] = c
    return D


# initial guesses for factor SDs (mm, size = CV)
SIG0 = {
    "size": 0.03, "lower_face_height": 3.5, "face_depth": 4.0, "mandible_projection": 3.5,
    "face_width": 2.0, "nose_projection": 2.0, "nose_width": 0.8, "interorbital": 1.0,
    "lips": 1.8, "mouth_width": 1.2, "cephalic_index": 3.0, "brow_projection": 2.0,
    "upper_face_height": 2.5, "ear_length": 1.5, "ear_protrusion": 2.5, "soft_tissue": 2.5,
    "eye_opening": 0.8, "vault_height": 4.0,
}

# calibration targets: (a, b, mean_M, sd_M, mean_F, sd_F, status)
TARGETS = [
    ("en_L", "en_R", 33.3, 2.7, 31.8, 2.3, "knowledge (Farkas NAW; Kosovo-Albanian sample within 1 mm)"),
    ("ex_L", "ex_R", 90.0, 3.6, 87.0, 4.0, "mean knowledge; SD sourced (arXiv 2304.07175 copy of Farkas SDs)"),
    ("en_L", "ex_L", 31.0, 1.4, 30.0, 1.4, "knowledge"),
    ("p_L", "p_R", 64.5, 3.5, 62.0, 3.3, "knowledge (ANSUR 1988 via Dodgson 2004)"),
    ("al_L", "al_R", 34.9, 2.1, 31.4, 2.0, "knowledge (Farkas NAW)"),
    ("ch_L", "ch_R", 53.0, 3.3, 50.0, 3.0, "knowledge"),
    ("zy_L", "zy_R", 141.0, 5.0, 132.0, 4.6, "knowledge (soft-tissue/ANSUR-type bizygomatic)"),
    ("go_L", "go_R", 108.0, 6.5, 100.0, 6.0, "knowledge (soft-tissue jaw-angle width, not caliper on bone)"),
    ("t_L", "t_R", 145.0, 5.5, 137.0, 5.0, "knowledge (bitragion breadth)"),
    ("eu_L", "eu_R", 152.0, 5.3, 145.0, 5.0, "knowledge (Farkas/ANSUR range)"),
    ("g", "op", 197.0, 6.6, 187.0, 6.3, "knowledge"),
    ("n", "sn", 54.0, 3.3, 50.5, 3.1, "knowledge"),
    ("sn", "prn", 20.0, 2.0, 19.0, 1.9, "knowledge"),
    ("n", "prn", 49.0, 3.5, 45.0, 3.2, "knowledge"),
    ("sn", "sto", 22.0, 2.2, 20.0, 2.0, "knowledge"),
    ("sn", "me", 70.0, 4.8, 64.0, 4.2, "knowledge"),
    ("n", "me", 121.3, 6.8, 111.8, 5.2, "means sourced (PMC3485457 table); SDs sourced (arXiv 2304.07175)"),
    ("sa_L", "sba_L", 63.5, 3.6, 59.5, 3.4, "knowledge (Farkas/ANSUR range)"),
    ("ps_L", "pi_L", 9.5, 1.0, 9.5, 1.0, "knowledge"),
    ("ls", "sto", 8.5, 1.5, 7.5, 1.4, "knowledge"),
    ("sto", "li", 10.0, 1.5, 9.5, 1.4, "knowledge"),
]
# SD-only targets on derived quantities (no mean claim): t-n chord, prn depth
SD_ONLY = [("t_L", "n", 5.0, 4.7), ("t_L", "prn", 6.0, 5.6), ("t_L", "me", 6.5, 6.0)]
# SD of coordinate differences (axis, a, b, sd_M, sd_F): lip and chin protrusion, nasal projection
FUNC = [(2, "ls", "sn", 1.8, 1.7), (2, "li", "pg", 2.2, 2.0), (2, "prn", "sn", 1.8, 1.7), (2, "pg", "n", 3.5, 3.2)]


def dist_grad(X, a, b):
    if isinstance(a, tuple):
        ax, a = a
        g = np.zeros_like(X); g[IDX[a], ax] = 1.0; g[IDX[b], ax] = -1.0
        return float(X[IDX[a], ax] - X[IDX[b], ax]), g
    ia, ib = IDX[a], IDX[b]
    d = X[ia] - X[ib]
    L = np.linalg.norm(d)
    g = np.zeros_like(X)
    g[ia] = d / L
    g[ib] = -d / L
    return L, g


def nnls(A, b, tol=1e-12, maxit=500):
    m, n = A.shape
    P = np.zeros(n, bool); x = np.zeros(n)
    w = A.T @ (b - A @ x)
    it = 0
    while (~P).any() and w[~P].max() > tol and it < maxit:
        it += 1
        j = np.argmax(np.where(~P, w, -np.inf)); P[j] = True
        while True:
            z = np.zeros(n)
            z[P] = np.linalg.lstsq(A[:, P], b, rcond=None)[0]
            if (z[P] > 0).all():
                x = z; break
            mask = P & (z <= 0)
            alpha = np.min(x[mask] / (x[mask] - z[mask]))
            x = x + alpha * (z - x)
            P = P & (x > tol)
        w = A.T @ (b - A @ x)
    return x


def calibrate(X, sex):
    F = factors(X)
    names = list(F)
    rows, tv = [], []
    resvar = residual_cov()
    allt = [(a, b, (sM if sex == "M" else sF)) for a, b, mM, sM, mF, sF, _ in TARGETS]
    allt += [(a, b, (sM if sex == "M" else sF)) for a, b, sM, sF in SD_ONLY]
    allt += [((ax, a), b, (sM if sex == "M" else sF)) for ax, a, b, sM, sF in FUNC]
    for a, b, sd in allt:
        L, g = dist_grad(X, a, b)
        rows.append([float(np.sum(g * F[k])) ** 2 for k in names])
        gv = g.reshape(-1)
        tv.append(sd ** 2 - float(gv @ resvar @ gv))
    A = np.array(rows); t = np.array(tv)
    s0 = np.array([SIG0[k] ** 2 for k in names])
    # weighted (relative) least squares + ridge toward initial guess, Lawson-Hanson NNLS
    W = 1.0 / np.array([(sd ** 2) for _, _, sd in allt])
    lam = 0.15
    scale = s0.copy(); scale[scale == 0] = 1
    Aa = np.vstack([A * W[:, None], np.sqrt(lam) * np.diag(1 / scale)])
    ta = np.concatenate([t * W, np.sqrt(lam) * s0 / scale])
    x = nnls(Aa, ta)
    floor = 0.25 * s0  # keep every factor alive: sigma >= 0.5 * initial guess
    floor[0] = 0.0
    x = np.maximum(x, floor)
    sig = np.sqrt(x)
    return names, sig, F, resvar, allt


def covariance(F, names, sig, resvar):
    n = len(IDS)
    Lmat = np.stack([F[k].reshape(-1) * s for k, s in zip(names, sig)], axis=1)  # (3n, K)
    S = Lmat @ Lmat.T + resvar
    return S, Lmat


def report(X, S, allt):
    out = []
    for a, b, sd in allt:
        L, g = dist_grad(X, a, b)
        gv = g.reshape(-1)
        out.append((a, b, L, math.sqrt(gv @ S @ gv), sd))
    return out


results = {}
for sex, d in (("M", MALE), ("F", FEMALE)):
    X = config(d)
    names, sig, F, resvar, allt = calibrate(X, sex)
    S, Lmat = covariance(F, names, sig, resvar)
    results[sex] = dict(X=X, names=names, sig=sig, F=F, resvar=resvar, S=S, L=Lmat, allt=allt)
    print("=====", sex)
    for k, s in zip(names, sig):
        print(f"  {k:22s} sigma={s:.4f}")
    for a, b, L, sdm, sdt in report(X, S, allt):
        print(f"  {str(a):10s}-{b:6s} model={L:7.1f}  sd_model={sdm:5.2f}  sd_target={sdt:5.2f}")

np.save("/tmp/claude-0/-home-user-minedesign/b0bfc7ad-f996-5fdb-831e-f158e8b6fceb/scratchpad/results.npy", results, allow_pickle=True)
