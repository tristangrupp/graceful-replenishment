"""Red experiment, tests 2 and 3, and the flag table.

Reads the basin-mean series written by 11_red_series.py and asks, for every
HydroBASINS level 6 basin, whether either downscaled product has anything
a coarse GRACE solution does not already say.

The tests are all one-sided. A basin that trips a flag has been shown to add
nothing usable. A basin that trips nothing has only survived; it has not been
shown to be right. There is no green half here and the outputs never claim one.

Every threshold sits in CONFIG below and every one of them is a judgment call,
so the script also emits a sensitivity table: the same counts recomputed across
a plausible range of each threshold. A count that moves a lot across that range
is not a finding.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

sys.path.insert(0, r"E:\Water\_shared")
sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
import red_grid as rg  # noqa: E402
from dark_water.depletion_watchlist.depletion import trend as T  # noqa: E402

RED = rg.RED

CONFIG = {
    # test 1, geometry
    "min_cells": 2,              # fewer product cells than this is not a field
    "max_frac_dominant": 0.95,   # basin inside one coarse footprint
    # test 2
    "min_var_ratio": 0.05,       # departure smaller than this is resampling
    "max_pred_r2": 0.80,         # departure this explainable is a weather field
    # test 3
    "min_r_GL": 0.50,
    "max_trend_diff_ratio": 1.0,
    "max_rank_shift": 20.0,      # percentile points
    # admission
    "min_months": 60,
    "min_coverage": 0.50,
}

SENSITIVITY = {
    "min_cells": [1, 2, 3, 4],
    "max_frac_dominant": [0.80, 0.90, 0.95, 0.99],
    "min_var_ratio": [0.02, 0.05, 0.10, 0.20],
    "max_pred_r2": [0.70, 0.80, 0.90, 0.95],
    "min_r_GL": [0.30, 0.50, 0.70, 0.90],
    "max_trend_diff_ratio": [0.5, 1.0, 2.0, 5.0],
    "max_rank_shift": [10.0, 20.0, 30.0, 50.0],
}

geom = pd.read_parquet(RED / "level6_geometry.parquet")
n = len(geom)
hyb = geom["HYBAS_ID"].to_numpy()


def load(name):
    p = RED / f"series_{name}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df.columns = [int(c) for c in df.columns]
    return df


seda, liku = load("seda"), load("liku")
jpl, jpl61, gsfc = load("jpl"), load("jpl61"), load("gsfc")
precip, sm, snow = load("precip"), load("sm"), load("snowcanopy")
have_L = liku is not None
if not have_L:
    print("Li and Kusche series absent: tests 3 and 3b will be left empty")

# ------------------------------------------------------------- common window
idx = seda.index
for d in [jpl] + ([liku] if have_L else []):
    idx = idx.intersection(d.index)
pred_idx = idx.intersection(precip.index).intersection(sm.index).intersection(snow.index)
print(f"common window {idx[0]:%Y-%m}..{idx[-1]:%Y-%m}, {len(idx)} months; "
      f"{len(pred_idx)} of them with predictors")
COMMON = [f"{idx[0]:%Y-%m}", f"{idx[-1]:%Y-%m}"]


def centered(df):
    """Re-center on the common months.

    The products state different baseline periods, and a difference of two
    baselines survives a subtraction as a constant offset with no physical
    meaning. Re-centering both on the months actually compared removes it.
    """
    x = df.loc[idx].to_numpy(dtype="float64")
    return x - np.nanmean(x, axis=0, keepdims=True)


# Each product is differenced against the release it was built from. GRACE-SeDA
# v1 names JPL RL06.1Mv03 CRI; Li and Kusche names no release, so it gets the
# current one, RL06.3Mv04, with the alternative reported beside it. One release
# for both would push a release change into one product's residual and score it
# as information the downscaling added.
D_G = centered(seda)
C = centered(jpl)                    # RL06.3Mv04, the parent of Li and Kusche
C61 = centered(jpl61)                # RL06.1Mv03, the parent of GRACE-SeDA
C2 = centered(gsfc)                  # a second processing center
D_L = centered(liku) if have_L else None

complete = (np.isfinite(D_G).all(axis=0) & np.isfinite(C).all(axis=0)
            & np.isfinite(C61).all(axis=0))
if have_L:
    complete &= np.isfinite(D_L).all(axis=0)
cover_ok = (geom["cover_G"].to_numpy() >= CONFIG["min_coverage"])
usable = complete & cover_ok & (len(idx) >= CONFIG["min_months"])
print(f"{int(usable.sum())} of {n} basins have a complete series in every product")

# --------------------------------------------------------------- test 2a
def ratio(num, den):
    v = np.var(den, axis=0)
    return np.divide(np.var(num, axis=0), v, out=np.full(n, np.nan), where=v > 0)


R_G = D_G - C61
R_L = (D_L - C) if have_L else None
var_ratio_G = ratio(R_G, C61)
var_ratio_L = ratio(R_L, C) if have_L else np.full(n, np.nan)
# The same quantity against the other release, so the choice above can be seen
# rather than taken on trust.
var_ratio_G_alt = ratio(D_G - C, C)
var_ratio_L_alt = ratio(D_L - C61, C61) if have_L else np.full(n, np.nan)
# Two floors under any departure. The first is one center changing release; the
# second is two centers processing the same months. A departure below either is
# not distinguishable from a processing choice.
var_ratio_release = ratio(C - C61, C61)
var_ratio_solution = ratio(C2 - C, C)

# --------------------------------------------------------------- test 2b
def deseason(x, index):
    """Remove each calendar month's own mean, the repo's deseasonalisation."""
    m = index.month.to_numpy()
    out = x.copy()
    for k in range(1, 13):
        s = m == k
        if s.any():
            out[s] -= np.nanmean(x[s], axis=0, keepdims=True)
    return out


pi = idx.get_indexer(pred_idx)
P = deseason(precip.loc[pred_idx].to_numpy(dtype="float64"), pred_idx)
SM = deseason(sm.loc[pred_idx].to_numpy(dtype="float64"), pred_idx)
SN = deseason(snow.loc[pred_idx].to_numpy(dtype="float64"), pred_idx)

# Storage integrates flux, so the accumulated anomaly is the term a storage
# series can answer to; single months are kept as short lags beside it.
PC = np.nancumsum(np.nan_to_num(P), axis=0)
PC -= PC.mean(axis=0, keepdims=True)


def lag(x, k):
    out = np.full_like(x, np.nan)
    if k:
        out[k:] = x[:-k]
    else:
        out = x.copy()
    return out


def predictor_fit(resid):
    """Adjusted R-squared of the departure on the hydrometeorological fields.

    Returns the ordinary adjusted R-squared, which is what the 0.8 threshold in
    the spec means, and a second one whose denominator uses the effective
    sample size from residual lag-1 autocorrelation, following Dawdy and
    Matalas. Monthly storage is strongly autocorrelated, so the second number
    is the honest one to quote beside any claim about degrees of freedom.
    """
    y = deseason(resid[pi], pred_idx)
    cols = [np.ones(len(pred_idx))] + [lag(P, k) for k in (0, 1, 2, 3)] + [PC, SM, SN]
    r2 = np.full(n, np.nan)
    r2_eff = np.full(n, np.nan)
    k_par = len(cols) - 1
    for b in np.where(usable)[0]:
        X = np.column_stack([c[:, b] if c.ndim == 2 else c for c in cols])
        yy = y[:, b]
        ok = np.isfinite(yy) & np.isfinite(X).all(axis=1)
        nn = int(ok.sum())
        if nn < k_par + 10:
            continue
        Xo, yo = X[ok], yy[ok]
        beta, *_ = np.linalg.lstsq(Xo, yo, rcond=None)
        res = yo - Xo @ beta
        sst = float(((yo - yo.mean()) ** 2).sum())
        if sst <= 0:
            continue
        raw = 1.0 - float((res ** 2).sum()) / sst
        r2[b] = 1.0 - (1.0 - raw) * (nn - 1) / max(nn - k_par - 1, 1)
        r1 = float(np.corrcoef(res[1:], res[:-1])[0, 1]) if nn > 3 else 0.0
        r1 = min(max(r1, -0.99), 0.99)
        n_eff = nn * (1 - r1) / (1 + r1)
        if n_eff > k_par + 2:
            r2_eff[b] = 1.0 - (1.0 - raw) * (n_eff - 1) / (n_eff - k_par - 1)
    return r2, r2_eff


print("regressing the departure on precipitation, soil moisture and snow")
pred_r2_G, pred_r2_eff_G = predictor_fit(R_G)
pred_r2_L, pred_r2_eff_L = (predictor_fit(R_L) if have_L
                            else (np.full(n, np.nan), np.full(n, np.nan)))

# ---------------------------------------------------------------- test 3
def trends(x):
    out = np.full(n, np.nan)
    p = np.full(n, np.nan)
    cols = np.where(usable & np.isfinite(x).all(axis=0))[0]
    if not len(cols):
        return out, p
    da = xr.DataArray(x[:, cols], dims=("time", "b"),
                      coords={"time": idx, "b": cols})
    r = T.fit_trend(da, dim="time")
    out[cols] = r["trend"].values
    p[cols] = r["p_value"].values
    return out, p


trend_G, p_G = trends(D_G)
trend_C, p_C = trends(C)
trend_C2, _ = trends(C2)
trend_C61, p_C61 = trends(C61)
trend_L, p_L = (trends(D_L) if have_L else (np.full(n, np.nan), np.full(n, np.nan)))


def corr_cols(a, b):
    out = np.full(n, np.nan)
    for i in np.where(usable)[0]:
        out[i] = np.corrcoef(a[:, i], b[:, i])[0, 1]
    return out


r_GL = corr_cols(D_G, D_L) if have_L else np.full(n, np.nan)
r_GC = corr_cols(D_G, C)
r_LC = corr_cols(D_L, C) if have_L else np.full(n, np.nan)

trend_diff = np.abs(trend_G - trend_L)
scale = np.nanmean(np.abs(np.vstack([trend_G, trend_L])), axis=0)
trend_diff_ratio = np.divide(trend_diff, scale, out=np.full(n, np.nan), where=scale > 0)


# --------------------------------------------------------------- test 3b
def pct_rank(x):
    out = np.full(n, np.nan)
    m = np.isfinite(x) & usable
    v = x[m]
    # rank 0 = most depleting, so that the percentile reads as a priority list
    r = stats.rankdata(v, method="average")
    out[m] = 100.0 * (r - 1) / max(len(v) - 1, 1)
    return out


rank_G, rank_L, rank_C = pct_rank(trend_G), pct_rank(trend_L), pct_rank(trend_C)
rank_C2 = pct_rank(trend_C2)
rank_shift = np.abs(rank_G - rank_L)

both = np.isfinite(trend_G) & np.isfinite(trend_L) & np.isfinite(trend_C)
spearman = {}
if both.sum() > 10:
    spearman = {
        "G_vs_L": float(stats.spearmanr(trend_G[both], trend_L[both]).statistic),
        "G_vs_coarse": float(stats.spearmanr(trend_G[both], trend_C[both]).statistic),
        "L_vs_coarse": float(stats.spearmanr(trend_L[both], trend_C[both]).statistic),
        "n": int(both.sum()),
    }
else:
    gc = np.isfinite(trend_G) & np.isfinite(trend_C)
    spearman = {"G_vs_coarse": float(stats.spearmanr(trend_G[gc], trend_C[gc]).statistic),
                "n": int(gc.sum())}

# The two coarse solutions are compared on their own mask: GSFC leaves a few
# coastal basins without a terrestrial mascon, and those should not silently
# take the whole comparison out with them.
cc = np.isfinite(trend_C) & np.isfinite(trend_C2)
spearman["coarse_JPL_vs_GSFC"] = float(stats.spearmanr(trend_C[cc], trend_C2[cc]).statistic)
spearman["n_coarse_pair"] = int(cc.sum())
# The same centre, one release apart, which is the tighter of the two floors.
rr = np.isfinite(trend_C) & np.isfinite(trend_C61)
spearman["coarse_RL0603_vs_RL0601"] = float(
    stats.spearmanr(trend_C[rr], trend_C61[rr]).statistic)

# ------------------------------------------------------------------- flags
def flags(cfg):
    n_cells = np.nanmin(np.vstack([
        geom["n_cells_G"].to_numpy(dtype="float64"),
        geom["n_cells_L"].to_numpy(dtype="float64") if have_L
        else np.full(n, np.inf)]), axis=0)
    f = {}
    f["RED_GEOMETRY"] = ((n_cells < cfg["min_cells"])
                         | (geom["frac_dominant_mascon"].to_numpy() > cfg["max_frac_dominant"]))
    vr = np.nanmin(np.vstack([var_ratio_G, var_ratio_L]), axis=0) if have_L else var_ratio_G
    f["RED_NO_INDEPENDENT_DEPARTURE"] = vr < cfg["min_var_ratio"]
    pr = np.nanmax(np.vstack([pred_r2_G, pred_r2_L]), axis=0) if have_L else pred_r2_G
    f["RED_PREDICTOR_DERIVED"] = pr > cfg["max_pred_r2"]
    f["RED_DISAGREEMENT"] = ((r_GL < cfg["min_r_GL"])
                             | (trend_diff_ratio > cfg["max_trend_diff_ratio"]))
    f["RED_RANK_UNSTABLE"] = rank_shift > cfg["max_rank_shift"]
    for k in list(f):
        f[k] = np.where(np.isnan(f[k].astype("float64")), False, f[k]).astype(bool)
    f["RED_ANY"] = np.logical_or.reduce(list(f.values()))
    # The three per-product tests split cleanly by product; the two comparison
    # tests do not, because they are about the pair.
    for tag, nc, vr_, pr_ in (("G", geom["n_cells_G"].to_numpy(dtype="float64"),
                               var_ratio_G, pred_r2_G),
                              ("L", geom["n_cells_L"].to_numpy(dtype="float64"),
                               var_ratio_L, pred_r2_L)):
        f[f"RED_GEOMETRY_{tag}"] = np.nan_to_num(
            (nc < cfg["min_cells"])
            | (geom["frac_dominant_mascon"].to_numpy() > cfg["max_frac_dominant"]),
            nan=False).astype(bool)
        f[f"RED_NO_INDEPENDENT_DEPARTURE_{tag}"] = (np.nan_to_num(vr_, nan=np.inf)
                                        < cfg["min_var_ratio"])
        f[f"RED_PREDICTOR_DERIVED_{tag}"] = (np.nan_to_num(pr_, nan=-np.inf)
                                             > cfg["max_pred_r2"])
        # Each product's own verdict, on its own three tests. The two
        # comparison tests are left out of it deliberately: a reader who wants
        # to judge one product without reference to the other needs a count
        # that does not quietly fold the other one in.
        f[f"RED_ANY_OWN_{tag}"] = (f[f"RED_GEOMETRY_{tag}"]
                                   | f[f"RED_NO_INDEPENDENT_DEPARTURE_{tag}"]
                                   | f[f"RED_PREDICTOR_DERIVED_{tag}"])
    return f


F = flags(CONFIG)

out = geom.copy()
out["n_months"] = len(idx)
out["common_period"] = f"{COMMON[0]}..{COMMON[1]}"
out["usable"] = usable
out["var_ratio_G"] = var_ratio_G
out["var_ratio_L"] = var_ratio_L
out["var_ratio_G_alt_release"] = var_ratio_G_alt
out["var_ratio_L_alt_release"] = var_ratio_L_alt
out["var_ratio_release"] = var_ratio_release
out["var_ratio_solution"] = var_ratio_solution
out["pred_r2_G"] = pred_r2_G
out["pred_r2_L"] = pred_r2_L
out["pred_r2_eff_G"] = pred_r2_eff_G
out["pred_r2_eff_L"] = pred_r2_eff_L
out["r_GL"] = r_GL
out["r_GC"] = r_GC
out["r_LC"] = r_LC
out["trend_G"] = trend_G
out["trend_L"] = trend_L
out["trend_coarse"] = trend_C
out["trend_coarse_gsfc"] = trend_C2
out["trend_coarse_rl0601"] = trend_C61
out["p_coarse_rl0601"] = p_C61
out["p_G"] = p_G
out["p_L"] = p_L
out["p_coarse"] = p_C
out["trend_diff"] = trend_diff
out["trend_diff_ratio"] = trend_diff_ratio
out["rank_G"] = rank_G
out["rank_L"] = rank_L
out["rank_coarse"] = rank_C
out["rank_coarse_gsfc"] = rank_C2
out["rank_shift"] = rank_shift
for k, v in F.items():
    out[k] = v
out.to_parquet(RED / "level6_red_flags.parquet")

area = out["SUB_AREA"].to_numpy()


def counts(f):
    tot = area[usable].sum()
    return {k: {"n": int((v & usable).sum()),
                "area_share_of_tested": float(area[v & usable].sum() / tot) if tot else None}
            for k, v in f.items()}


sens = {}
for key, values in SENSITIVITY.items():
    rows = []
    for val in values:
        cfg = dict(CONFIG, **{key: val})
        ff = flags(cfg)
        rows.append({"value": val,
                     "n_RED_ANY": int((ff["RED_ANY"] & usable).sum()),
                     "n_flag": int((ff[{
                         "min_cells": "RED_GEOMETRY", "max_frac_dominant": "RED_GEOMETRY",
                         "min_var_ratio": "RED_NO_INDEPENDENT_DEPARTURE",
                         "max_pred_r2": "RED_PREDICTOR_DERIVED",
                         "min_r_GL": "RED_DISAGREEMENT",
                         "max_trend_diff_ratio": "RED_DISAGREEMENT",
                         "max_rank_shift": "RED_RANK_UNSTABLE"}[key]] & usable).sum())})
    sens[key] = rows

# Moving one threshold at a time understates how much of the result is a choice
# of cut, so the two corners are computed as well: every threshold at the most
# generous end of its range at once, and every one at the strictest.
corners = {}
for name, pick in (("most_generous", lambda v: v[0] if v[0] > v[-1] else v[-1]),
                   ("strictest", lambda v: v[-1] if v[0] > v[-1] else v[0])):
    cfg = dict(CONFIG)
    for key, values in SENSITIVITY.items():
        # A larger value is looser for the max_ thresholds and tighter for the
        # min_ ones, so which end counts as generous depends on the direction.
        vals = sorted(values)
        cfg[key] = (vals[-1] if key.startswith("max_") else vals[0])             if name == "most_generous" else             (vals[0] if key.startswith("max_") else vals[-1])
    ff = flags(cfg)
    m = ff["RED_ANY"] & usable
    corners[name] = {"config": {k: cfg[k] for k in SENSITIVITY},
                     "n_RED_ANY": int(m.sum()),
                     "share_of_tested": float(m.sum() / usable.sum()),
                     "area_share_of_tested": float(area[m].sum() / area[usable].sum())}

med_area_red = float(np.median(area[F["RED_ANY"] & usable])) if (F["RED_ANY"] & usable).any() else None
not_red = usable & ~F["RED_ANY"]

edges = np.percentile(area[usable], np.arange(0, 101, 10))
area_deciles = []
for k in range(10):
    lo_, hi_ = edges[k], edges[k + 1]
    m = usable & (area >= lo_) & ((area <= hi_) if k == 9 else (area < hi_))
    area_deciles.append({
        "decile": k + 1,
        "area_km2_range": [float(lo_), float(hi_)],
        "n": int(m.sum()),
        "red_share": float((F["RED_ANY"] & m).sum() / max(int(m.sum()), 1)),
    })
summary = {
    "common_period": COMMON,
    "n_months": int(len(idx)),
    "n_months_with_predictors": int(len(pred_idx)),
    "have_li_kusche": bool(have_L),
    "n_basins": int(n),
    "n_tested": int(usable.sum()),
    "tested_area_km2": float(area[usable].sum()),
    "flags": counts(F),
    "area": {
        "median_km2_red": med_area_red,
        "median_km2_not_red": float(np.median(area[not_red])) if not_red.any() else None,
        "n_not_red": int(not_red.sum()),
        "area_share_not_red": float(area[not_red].sum() / area[usable].sum()),
        # Red flags are expected to follow basin size, and they do. The share
        # flagged in each area decile is the plainest way to show it.
        "red_share_by_area_decile": area_deciles,
    },
    "spearman": spearman,
    "medians": {
        "var_ratio_G": float(np.nanmedian(var_ratio_G[usable])),
        "var_ratio_L": float(np.nanmedian(var_ratio_L[usable])) if have_L else None,
        "var_ratio_G_alt_release": float(np.nanmedian(var_ratio_G_alt[usable])),
        "var_ratio_L_alt_release": (float(np.nanmedian(var_ratio_L_alt[usable]))
                                    if have_L else None),
        "var_ratio_release": float(np.nanmedian(var_ratio_release[usable])),
        "var_ratio_solution": float(np.nanmedian(var_ratio_solution[usable])),
        "pred_r2_G": float(np.nanmedian(pred_r2_G[usable])),
        "pred_r2_eff_G": float(np.nanmedian(pred_r2_eff_G[usable])),
        "pred_r2_L": float(np.nanmedian(pred_r2_L[usable])) if have_L else None,
        "r_GL": float(np.nanmedian(r_GL[usable])) if have_L else None,
        "r_GC": float(np.nanmedian(r_GC[usable])),
        "r_LC": float(np.nanmedian(r_LC[usable])) if have_L else None,
        "rank_shift": float(np.nanmedian(rank_shift[usable])) if have_L else None,
    },
    "config": CONFIG,
    "sensitivity": sens,
    "sensitivity_corners": corners,
}
json.dump(summary, open(RED / "level6_red_summary.json", "w"), indent=2)
print(json.dumps({k: v for k, v in summary.items() if k != "sensitivity"}, indent=2))
