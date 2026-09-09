"""Green experiment, step 2: score every product against the wells, and ablate.

Two questions, in order.

Does a downscaled product track a well better than the coarse solution it was
built from? That is a paired comparison of correlations at the same well, and it
is answered per well.

Does GRACE add anything at a well that precipitation, soil moisture and snow do
not already give? That is the ablation, and it is the one the red experiment
could not reach. Three nested models are fitted and scored out of sample:

    A   precipitation, soil moisture, snow
    B   A plus the coarse GRACE groundwater term
    C   A plus the downscaled GRACE groundwater term

If B beats A, gravimetry adds information at the well. If C beats B, the
downscaling adds information beyond what the coarse solution already held. If C
does not beat B, the finer grid is not buying anything a well can see.

Splits are leave one mascon out, never random. Wells inside one 3 degree mascon
see the same gravimetric observation, so a random split would train and test on
the same measurement and report skill that is really memorisation.

Nothing is converted from head to storage. Correlations and out of sample R
squared on standardised series are unchanged by any positive scale factor, so
the specific yield of each aquifer, which nobody knows per well, never enters.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

GREEN = rg.ROOT / "green"
JPL = rg.RAW / "jpl_mascon" / "jpl_mascon_rl0603v04_cri.nc"
MIN_PAIRS = 10

# Each product is scored against the release it was built from, as in the red
# experiment. GRACE-SeDA v1 names RL06.1Mv03; Li and Kusche names none.
PARENT = {"seda": "jpl61", "liku": "jpl"}


def load(name):
    p = GREEN / f"well_{name}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    df.columns = [str(c) for c in df.columns]
    return df


sites = pd.read_parquet(GREEN / "well_sites.parquet")
sites["StnID"] = sites["StnID"].astype(str)
sites = sites.set_index("StnID")
level = load("level_anomaly_m")
gws = {k: load(f"gws_{k}") for k in ("seda", "liku", "jpl", "jpl61")}
pred = {k: load(f"pred_{k}") for k in ("precip_accum", "sm", "snow", "precip")}
cols = level.columns
print(f"{len(cols):,} wells, {len(level)} years {level.index.min()}..{level.index.max()}")

# The 3 degree mascon each well sits in, which is the block the splits use.
jpl = xr.open_dataset(JPL)
jlat, jlon = jpl["lat"].values, jpl["lon"].values
iy = np.clip(np.floor((sites.Lat.values + 90.0) / 0.5).astype(int), 0, len(jlat) - 1)
ix = np.clip(np.floor(np.mod(sites.Lon.values, 360.0) / 0.5).astype(int), 0, len(jlon) - 1)
mascon = pd.Series(np.asarray(jpl["mascon_ID"].values)[iy, ix].astype(int),
                   index=sites.index)
print(f"wells fall in {mascon.nunique():,} distinct mascons")

mean_precip = pd.read_parquet(GREEN / "well_mean_precip.parquet")
mean_precip["StnID"] = mean_precip["StnID"].astype(str)
mean_precip = mean_precip.set_index("StnID")["mean_precip_mm_yr"]


def paired_r(a, b):
    """Correlation per column over the years both series have."""
    out = np.full(a.shape[1], np.nan)
    A, B = a.to_numpy(), b.to_numpy()
    for j in range(A.shape[1]):
        m = np.isfinite(A[:, j]) & np.isfinite(B[:, j])
        if m.sum() < MIN_PAIRS:
            continue
        x, y = A[m, j], B[m, j]
        if x.std() == 0 or y.std() == 0:
            continue
        out[j] = np.corrcoef(x, y)[0, 1]
    return pd.Series(out, index=a.columns)


print("correlating each product against the wells")
r = {}
for k in ("seda", "liku", "jpl", "jpl61"):
    g = gws[k].reindex(columns=cols)
    r[k] = paired_r(level, g)
    print(f"  {k}: {int(r[k].notna().sum()):,} wells scored, "
          f"median r {r[k].median():.3f}")

table = pd.DataFrame({"lat": sites.Lat, "lon": sites.Lon, "n_years": sites.n_years,
                      "mascon": mascon, "mean_precip_mm_yr": mean_precip})
for k in r:
    table[f"r_{k}"] = r[k]
for p, parent in PARENT.items():
    table[f"dr_{p}"] = table[f"r_{p}"] - table[f"r_{parent}"]


def clustered_sign_test(delta, block):
    """Share of wells improved, and a p-value that counts mascons, not wells.

    Wells in one mascon share a gravimetric observation, so treating them as
    independent would turn a handful of facts into tens of thousands of them.
    The test is run on the per-mascon mean of the difference instead.
    """
    ok = np.isfinite(delta)
    d, b = delta[ok], block[ok]
    per_mascon = pd.Series(d).groupby(pd.Series(b).values).mean()
    pos = int((per_mascon > 0).sum())
    n = int(per_mascon.notna().sum())
    p = stats.binomtest(pos, n, 0.5).pvalue if n else np.nan
    return {"n_wells": int(ok.sum()), "share_wells_improved": float((d > 0).mean()),
            "n_mascons": n, "mascons_improved": pos,
            "share_mascons_improved": float(pos / n) if n else None,
            "median_delta_r": float(np.median(d)), "p_value_by_mascon": float(p)}


sign = {p: clustered_sign_test(table[f"dr_{p}"].to_numpy(), table["mascon"].to_numpy())
        for p in PARENT}

# ----------------------------------------------------------------- the ablation
EXTRAS = ["jpl", "jpl61", "seda", "liku"]


def _z(frame):
    v = frame.to_numpy(dtype="float64")
    with np.errstate(invalid="ignore"):
        mu = np.nanmean(v, axis=0)
        sd = np.nanstd(v, axis=0)
    return (v - np.where(np.isfinite(mu), mu, 0.0)) / np.where(sd > 0, sd, np.nan)


def build_panel():
    """One standardised panel, on the rows every model can be scored on.

    Every model has to see the same rows or the comparison is not an ablation.
    A well whose cell is missing from one product would otherwise let that
    product's model be judged on an easier sample than the rest.
    """
    Z = {"level": _z(level)}
    for k in ("precip_accum", "sm", "snow"):
        Z[k] = _z(pred[k].reindex(columns=cols))
    for k in EXTRAS:
        Z[k] = _z(gws[k].reindex(columns=cols))
    good = np.isfinite(Z["level"])
    for k in list(Z)[1:]:
        good &= np.isfinite(Z[k])
    wi, yi = np.where(good.T)          # well index, year index
    return Z, wi, yi, mascon.reindex(cols).to_numpy()[wi]


PANEL_Z, PANEL_W, PANEL_Y, PANEL_B = build_panel()
print(f"common panel: {len(PANEL_W):,} well-years, "
      f"{len(np.unique(PANEL_W)):,} wells, {len(np.unique(PANEL_B))} mascons")


def build_long(extra_key=None):
    names = ["precip_accum", "sm", "snow"] + ([extra_key] if extra_key else [])
    X = np.stack([PANEL_Z[k][PANEL_Y, PANEL_W] for k in names], axis=-1)
    y = PANEL_Z["level"][PANEL_Y, PANEL_W]
    return y, X, PANEL_W, PANEL_B, names


def leave_one_mascon_out(y, X, block):
    """Out of sample predictions, holding out one mascon at a time.

    Refitting from scratch per block would be hundreds of fits over a million
    rows. The normal equations are additive over rows, so each block's own
    contribution is subtracted from the total instead, which is the same answer.
    """
    X1 = np.column_stack([np.ones(len(y)), X])
    XtX = X1.T @ X1
    Xty = X1.T @ y
    pred_out = np.full(len(y), np.nan)
    for m in np.unique(block):
        s = block == m
        Xb, yb = X1[s], y[s]
        A = XtX - Xb.T @ Xb
        b = Xty - Xb.T @ yb
        try:
            beta = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            continue
        pred_out[s] = Xb @ beta
    ok = np.isfinite(pred_out)
    ss_res = float(((y[ok] - pred_out[ok]) ** 2).sum())
    ss_tot = float(((y[ok] - y[ok].mean()) ** 2).sum())
    return pred_out, (1.0 - ss_res / ss_tot if ss_tot > 0 else np.nan), int(ok.sum())


def per_well_r(y, pred_out, well_idx):
    out = {}
    df = pd.DataFrame({"y": y, "p": pred_out, "w": well_idx}).dropna()
    for w, g in df.groupby("w"):
        if len(g) >= MIN_PAIRS and g.y.std() > 0 and g.p.std() > 0:
            out[w] = float(np.corrcoef(g.y, g.p)[0, 1])
    return pd.Series(out)


def per_block_r2(y, pred_out, block):
    """Out of sample R squared inside each held-out mascon.

    The pooled number hides how few independent things it rests on. 782,000
    well-years sit in 151 mascons, and a mascon is one gravimetric observation,
    so any comparison between two models has to be judged across mascons rather
    than across wells.
    """
    out = {}
    ok = np.isfinite(pred_out)
    for m in np.unique(block):
        s = (block == m) & ok
        if s.sum() < 30:
            continue
        yy, pp = y[s], pred_out[s]
        sst = float(((yy - yy.mean()) ** 2).sum())
        if sst <= 0:
            continue
        out[int(m)] = 1.0 - float(((yy - pp) ** 2).sum()) / sst
    return pd.Series(out)


print("ablation, leave one mascon out")
ablation = {}
block_r2 = {}
for label, key in (("A_predictors_only", None), ("B_plus_coarse_RL0603", "jpl"),
                   ("B_plus_coarse_RL0601", "jpl61"), ("C_plus_seda", "seda"),
                   ("C_plus_liku", "liku")):
    y, X, wi, blk, names = build_long(key)
    p_out, r2, n = leave_one_mascon_out(y, X, blk)
    rw = per_well_r(y, p_out, wi)
    block_r2[label] = per_block_r2(y, p_out, blk)
    ablation[label] = {"terms": names, "n_rows": n,
                       "n_mascons": int(len(np.unique(blk))),
                       "oos_r2": float(r2), "median_well_r": float(rw.median()),
                       "median_mascon_r2": float(block_r2[label].median()),
                       "n_wells": int(len(rw))}
    print(f"  {label:24s} rows {n:>9,}  out of sample R2 {r2:+.4f}  "
          f"median well r {rw.median():+.3f}")

# The same ablation split by how wet the well is. The green half is only cleanly
# interpretable where precipitation flux does not dominate the water balance, so
# the split is reported rather than averaged away.
DRY = 500.0
by_wet = {}
for tag, sel in (("dry_under_500mm", mean_precip.reindex(cols) < DRY),
                 ("wet_over_500mm", mean_precip.reindex(cols) >= DRY)):
    keep = np.where(sel.reindex(cols).fillna(False).to_numpy())[0]
    if len(keep) < 50:
        continue
    sub = {}
    for label, key in (("A_predictors_only", None), ("B_plus_coarse_RL0603", "jpl"),
                       ("C_plus_seda", "seda"), ("C_plus_liku", "liku")):
        y, X, wi, blk, _ = build_long(key)
        m = np.isin(wi, keep)
        if m.sum() < 500 or len(np.unique(blk[m])) < 5:
            continue
        _, r2, n = leave_one_mascon_out(y[m], X[m], blk[m])
        sub[label] = {"oos_r2": float(r2), "n_rows": int(n)}
    by_wet[tag] = {"n_wells": int(len(keep)),
                   "n_wells_in_panel": int(np.isin(np.unique(PANEL_W), keep).sum()),
                   "models": sub}
    print(f"  {tag}: " + ", ".join(f"{k} {v['oos_r2']:+.4f}" for k, v in sub.items()))

# Paired across mascons, which is the only unit that can carry a p-value here.
paired = {}
base = "B_plus_coarse_RL0603"
for label in ("A_predictors_only", "C_plus_seda", "C_plus_liku"):
    a, b = block_r2[label].align(block_r2[base], join="inner")
    d = (a - b).dropna()
    if not len(d):
        continue
    w = stats.wilcoxon(d) if len(d) > 10 else None
    paired[f"{label}_minus_{base}"] = {
        "n_mascons": int(len(d)),
        "median_delta_r2": float(d.median()),
        "mascons_better": int((d > 0).sum()),
        "share_better": float((d > 0).mean()),
        "wilcoxon_p": float(w.pvalue) if w is not None else None,
        "sign_test_p": float(stats.binomtest(int((d > 0).sum()), len(d), 0.5).pvalue),
    }
    print(f"  {label} minus coarse: median dR2 {d.median():+.4f}, "
          f"{int((d>0).sum())}/{len(d)} mascons better, p {paired[list(paired)[-1]]['sign_test_p']:.3f}")

pd.DataFrame(block_r2).to_parquet(GREEN / "mascon_oos_r2.parquet")
table.to_parquet(GREEN / "well_scores.parquet")
summary = {
    "window": [int(level.index.min()), int(level.index.max())],
    "n_wells": int(len(cols)),
    "n_mascons": int(mascon.nunique()),
    "min_paired_years": MIN_PAIRS,
    "median_r": {k: float(v.median()) for k, v in r.items()},
    "n_scored": {k: int(v.notna().sum()) for k, v in r.items()},
    "parent_release": PARENT,
    "paired_against_parent": sign,
    "ablation": ablation,
    "ablation_by_wetness": by_wet,
    "ablation_paired_by_mascon": paired,
}
json.dump(summary, open(GREEN / "green_summary.json", "w"), indent=2)
print(json.dumps({k: v for k, v in summary.items()
                  if k in ("median_r", "paired_against_parent")}, indent=2))
