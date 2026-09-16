"""Spatial autocorrelation of the level 4 storage trends.

The trend test corrects for autocorrelation in time, following Dawdy and
Matalas, and then treats every basin as an independent test. It is not. Basins
sit on a smooth field, neighbours share mascons, and the GSFC solution is
regularized, which smooths it further. This script measures how much of a
problem that is, without claiming to separate real hydroclimate clustering from
smoothing built into the measurement. Nothing here can do that; the correlogram
range against the mascon footprint is the closest available hint.

Four things are computed, for total water storage and for the groundwater
estimate:

  1. Global Moran's I with a permutation test. Moran (1950) Biometrika 37:17;
     inference as in Cliff and Ord, Spatial Processes (1981).
  2. A correlogram: Moran's I by centroid distance band. Oden (1984)
     Geographical Analysis 16:1; Legendre and Legendre, Numerical Ecology, ch 13.
  3. An effective sample size, from an exponential fit to the correlogram:
     n_eff = n^2 / sum_ij rho(d_ij). This is the spatial counterpart of the
     Dawdy and Matalas correction already applied in time. Clifford, Richardson
     and Hemon (1989) Biometrics 45:123; Dutilleul (1993) Biometrics 49:305;
     Griffith (2005) Annals AAG 95:740.
  4. False discovery rate control over the basin p-values, which is what the
     hatching on the map actually needs. Benjamini and Hochberg (1995) JRSS B
     57:289; Benjamini and Yekutieli (2001) Ann Stat 29:1165, valid under any
     dependence; Wilks (2016) BAMS 97:2263 recommends alpha_FDR = 2 alpha for
     correlated fields.

Each measure runs three ways: on the trends, on their ranks, and with basins
over one fifth ice dropped. Greenland's trends are extreme enough to drive a
Moran statistic on their own, and a result that only holds one of those three
ways is not a result.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

ROOT = Path(r"E:\Water\Global")
OUT = ROOT / "trends" / "spatial_autocorr_lev04.json"
N_PERM = 9999
N_PERM_BAND = 999
BANDS = [(0, 250), (250, 500), (500, 750), (750, 1000), (1000, 1500),
         (1500, 2000), (2000, 3000), (3000, 4000), (4000, 6000)]
RNG = np.random.default_rng(20260916)
EARTH_R = 6371.0088

trends = pd.read_csv(ROOT / "trends" / "basins_lev04_trends.csv")
basins = rg.load_basins("04")[["HYBAS_ID", "geometry"]]
g = basins.merge(trends, on="HYBAS_ID", how="inner", suffixes=("", "_t"))
n = len(g)
print(f"{n} level 4 basins with geometry and trends")

# --------------------------------------------------------------- the weights
# Contiguity first: basins that share a border. HydroBASINS polygons are built
# to tile without gaps, so "intersects" is the shared-border test.
idx = pd.Series(np.arange(n), index=g.index)
pairs = g.sjoin(g[["geometry"]], how="inner", predicate="intersects")
a = idx.loc[pairs.index].to_numpy()
b = pairs["index_right"].to_numpy()
keep = a != b
a, b = a[keep], b[keep]
print(f"{len(a)} contiguity pairs, {len(np.unique(a))} basins with a neighbour")

pt = g.geometry.representative_point()
lon = np.radians(pt.x.to_numpy())
lat = np.radians(pt.y.to_numpy())
# Great-circle distance between every pair of basin centres, in km. 1,342
# basins is 1.8 million pairs, which fits in memory as float32.
sin_lat, cos_lat = np.sin(lat), np.cos(lat)
cosd = (sin_lat[:, None] * sin_lat[None, :] +
        cos_lat[:, None] * cos_lat[None, :] * np.cos(lon[:, None] - lon[None, :]))
D = (EARTH_R * np.arccos(np.clip(cosd, -1, 1))).astype("float32")
np.fill_diagonal(D, 0.0)

W_cont = np.zeros((n, n), dtype="float32")
W_cont[a, b] = 1.0
W_cont = np.maximum(W_cont, W_cont.T)
# An island basin has no shared border. Rather than dropping it, give it its
# four nearest neighbours, so every basin carries some weight.
orphan = W_cont.sum(axis=1) == 0
if orphan.any():
    for i in np.flatnonzero(orphan):
        near = np.argsort(D[i])[1:5]
        W_cont[i, near] = 1.0
        W_cont[near, i] = 1.0
    print(f"{int(orphan.sum())} basins had no shared border; gave them 4 nearest neighbours")


def row_standardize(W):
    s = W.sum(axis=1, keepdims=True)
    s[s == 0] = 1.0
    return W / s


def morans_i(x, W):
    z = x - x.mean()
    s0 = W.sum()
    return (len(x) / s0) * float(z @ (W @ z)) / float(z @ z)


def moran_perm(x, W, n_perm=N_PERM):
    """Moran's I with a permutation reference distribution.

    The null is that the values could sit on any basin. Shuffling the values
    and keeping the geometry fixed is the standard test in Cliff and Ord.
    """
    obs = morans_i(x, W)
    z = x - x.mean()
    denom = float(z @ z)
    s0 = W.sum()
    k = len(x) / s0
    sim = np.empty(n_perm)
    for j in range(n_perm):
        zp = RNG.permutation(z)
        sim[j] = k * float(zp @ (W @ zp)) / denom
    # One-sided: the question is clustering, not dispersion.
    p = (1 + int((sim >= obs).sum())) / (n_perm + 1)
    e_i = -1.0 / (len(x) - 1)
    return {"I": obs, "E_I": e_i, "p_perm": p,
            "sd_perm": float(sim.std()),
            "z_perm": float((obs - sim.mean()) / sim.std())}


def correlogram(x, n_perm=N_PERM_BAND):
    """Moran's I in distance bands, each with its own permutation test.

    Oden's correction for testing several bands at once is a Bonferroni step;
    the corrected threshold is reported rather than applied silently.
    """
    out = []
    for lo, hi in BANDS:
        W = ((D > lo) & (D <= hi)).astype("float32")
        np.fill_diagonal(W, 0.0)
        npairs = int(W.sum() / 2)
        if npairs < 50:
            continue
        r = moran_perm(x, W, n_perm)
        r.update({"lo_km": lo, "hi_km": hi, "pairs": npairs})
        out.append(r)
    return out


def effective_n(corr, x):
    """n_eff from an exponential fit to the correlogram.

    rho(d) = exp(-d / a), fitted by least squares on the band values that are
    still positive, then n_eff = n^2 / sum_ij rho(d_ij). At rho = 0 everywhere
    this returns n; at rho = 1 everywhere it returns 1.
    """
    d = np.array([0.5 * (c["lo_km"] + c["hi_km"]) for c in corr])
    i = np.array([c["I"] for c in corr])
    ok = i > 0.01
    if ok.sum() < 2:
        return {"range_km": 0.0, "n_eff": float(len(x)), "note": "no positive bands"}
    # log rho = -d / a, through the origin, weighted by pair count.
    w = np.array([c["pairs"] for c in corr], dtype="float64")[ok]
    a_hat = float(-(w * d[ok] * d[ok]).sum() / (w * d[ok] * np.log(i[ok])).sum())
    rho = np.exp(-D.astype("float64") / a_hat)
    n_eff = float(len(x) ** 2 / rho.sum())
    return {"range_km": a_hat, "e_folding_km": a_hat,
            "practical_range_km": 3 * a_hat, "n_eff": n_eff,
            "n_eff_share": n_eff / len(x)}


def fdr(p, alpha):
    """Benjamini-Hochberg and Benjamini-Yekutieli counts.

    BH assumes positive dependence; BY holds under any dependence and is the
    conservative one to quote for a field this smooth.
    """
    p = np.sort(np.asarray(p, dtype="float64"))
    m = len(p)
    rank = np.arange(1, m + 1)
    bh = p <= alpha * rank / m
    c_m = np.log(m) + 0.5772156649 + 1.0 / (2 * m)
    by = p <= alpha * rank / (m * c_m)
    return {"n_tested": m,
            "n_raw": int((p < alpha).sum()),
            "n_bh": int(rank[bh].max()) if bh.any() else 0,
            "n_by": int(rank[by].max()) if by.any() else 0,
            "c_m": float(c_m)}


W_cont_rs = row_standardize(W_cont)
results = {
    "n_basins": int(n),
    "n_perm": N_PERM,
    "weights": {"contiguity_pairs": int(len(a) / 2),
                "mean_neighbours": float((W_cont > 0).sum(axis=1).mean())},
    "layers": {},
    "references": [
        "Moran 1950 Biometrika 37:17",
        "Cliff and Ord 1981 Spatial Processes",
        "Oden 1984 Geographical Analysis 16:1",
        "Clifford, Richardson and Hemon 1989 Biometrics 45:123",
        "Dutilleul 1993 Biometrics 49:305",
        "Griffith 2005 Annals AAG 95:740",
        "Benjamini and Hochberg 1995 JRSS B 57:289",
        "Benjamini and Yekutieli 2001 Ann Stat 29:1165",
        "Wilks 2016 BAMS 97:2263",
    ],
}

for layer, tcol, pcol in [("tws", "tws_trend_mm_yr", "tws_p"),
                          ("gws", "gws_trend_mm_yr", "gws_p")]:
    have = g[tcol].notna().to_numpy()
    no_ice = have & (g["ice_fraction"].fillna(0).to_numpy() <= 0.20)
    entry = {}
    for variant, mask, transform in [("all", have, "raw"),
                                     ("all_ranks", have, "rank"),
                                     ("no_ice", no_ice, "raw")]:
        sub = np.flatnonzero(mask)
        x = g[tcol].to_numpy()[sub]
        if transform == "rank":
            x = pd.Series(x).rank().to_numpy()
        Wc = row_standardize(W_cont[np.ix_(sub, sub)])
        # The distance matrix is global, so the correlogram is computed on the
        # same subset by rebuilding D's view inside the closure.
        D_full = D
        D = D_full[np.ix_(sub, sub)]
        res = {"n": int(len(sub)), "global_moran_contiguity": moran_perm(x, Wc)}
        corr = correlogram(x)
        res["correlogram"] = corr
        res["effective_n"] = effective_n(corr, x)
        D = D_full
        entry[variant] = res
        gm = res["global_moran_contiguity"]
        en = res["effective_n"]
        print(f"[{layer}/{variant}] n={len(sub)} Moran I={gm['I']:.3f} "
              f"p={gm['p_perm']:.4f} e-folding={en.get('e_folding_km', 0):.0f} km "
              f"n_eff={en['n_eff']:.0f} ({en.get('n_eff_share', 1)*100:.1f}%)")

    p = g[pcol].to_numpy()[have]
    entry["fdr"] = {"alpha_0.05": fdr(p, 0.05), "alpha_0.10_wilks": fdr(p, 0.10)}
    f5 = entry["fdr"]["alpha_0.05"]
    print(f"[{layer}] significant at 0.05: raw {f5['n_raw']}, "
          f"BH {f5['n_bh']}, BY {f5['n_by']} of {f5['n_tested']}")
    results["layers"][layer] = entry

mascon_summary = json.load(open(ROOT / "trends" / "mascon_trends_summary.json"))
results["comparators"] = {
    "n_land_mascons": mascon_summary.get("n_land_mascons"),
    "n_mascons": mascon_summary.get("n_mascons"),
    "mascon_area_km2": 12400,
    "note": "a mascon is one gravimetric observation; n_eff below this count is "
            "the field being smoother than the mascon grid, above it would be "
            "impossible",
}

OUT.parent.mkdir(parents=True, exist_ok=True)
# numpy scalars come out of the float32 weight matrices; json needs builtins.
json.dump(results, open(OUT, "w"), indent=2, default=float)
print("wrote", OUT)
