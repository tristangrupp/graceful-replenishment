"""Nuevo Leon decomposition with GLDAS soil moisture over the full record.

Script 13 removed soil moisture with SMAP L4, which only starts in 2015 and
so could only run on 2016-2025 -- ten years against the twenty-four the
reservoir work used. GLDAS covers 2002-04 to 2026-03, the whole GRACE record,
and comes as three independent land-surface models rather than one.

    TWS = reservoir + [soil moisture + snow + canopy] + groundwater

Reservoir storage is surface water and appears in no GLDAS variable here, so
it must still be subtracted separately; GLDAS alone would leave Cuchillo,
Cerro Prieto and El Cuchillo's drawdown inside the "groundwater" term.

Two things this answers that script 13 could not:

- whether the residual drought excursion -- pre-drought +15.8 mm, trough
  -57.4 mm at 2023-12, 63% recovered by 2025 -- survives a soil-moisture
  correction fitted over the full record rather than the drought decade only
- whether SMAP and GLDAS agree about soil moisture on the window they share,
  which is the first independent check on that term this project has had

Weighting matches script 13 exactly (`nl_area_frac` x `area_km2`) so the
numbers are directly comparable rather than differently aggregated.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import attribution as A  # noqa: E402
from dark_water.depletion_watchlist.depletion import trend as trend_mod  # noqa: E402

NL = Path(r"E:\Water\NuevoLeon")
SIG, TR, PROC = NL / "signals", NL / "trends", NL / "processed"
MODELS = ("noah", "vic", "clsm")
CM_TO_MM = 10.0


def deseasonalise(df):
    return df - df.groupby(df.index.month).transform("mean")


def fit(series):
    s = pd.Series(series).dropna()
    if len(s) < 36:
        return np.nan, np.nan
    da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                      coords={"time": s.index, "x": [0]})
    r = trend_mod.fit_trend(da)
    return float(r["trend"].values[0]), float(r["p_value"].values[0])


def weighted(df, w):
    """Weighted mean, renormalised each month over the mascons that reported.

    Script 13 divided by the full weight sum regardless of how many mascons
    had data, which silently treats a missing mascon as a zero anomaly and
    pulls the aggregate toward zero. Harmless when every mascon reports, and
    it does within the windows used here, but the failure is invisible when it
    does happen, so the normalisation is done against the available weight.
    """
    cols = [c for c in df.columns if c in w.index]
    ww = w.loc[cols]
    num = (df[cols] * ww).sum(axis=1, min_count=1)
    den = (df[cols].notna() * ww).sum(axis=1)
    return num / den.where(den > 0)


meta = pd.read_csv(SIG / "mascon_metadata.csv")
dec = pd.read_csv(TR / "mascon_decomposition.csv")
meta = meta.merge(dec[["mascon_id", "nl_area_frac"]], on="mascon_id", how="left")
meta["nl_area_frac"] = meta["nl_area_frac"].fillna(0.0)
w = meta.set_index("mascon_id")["nl_area_frac"] * meta.set_index("mascon_id")["area_km2"]
print(f"{len(meta)} mascons, {(meta.nl_area_frac > 0).sum()} touching Nuevo Leon")


def to_mascons(da: xr.DataArray) -> pd.DataFrame:
    """cos(lat)-weighted mean of a lat/lon field over each mascon's box."""
    lat, lon = da["lat"].values, da["lon"].values
    vals = da.transpose("time", "lat", "lon").values
    out, fallback = {}, 0
    for _, r in meta.iterrows():
        my = (lat >= r.lat_min) & (lat < r.lat_max)
        mx = (lon >= r.lon_min) & (lon < r.lon_max)
        if my.sum() and mx.sum():
            blk = vals[:, my, :][:, :, mx]
            ww = np.broadcast_to(np.cos(np.deg2rad(lat[my]))[None, :, None], blk.shape).copy()
            ww[~np.isfinite(blk)] = 0.0
            tot = ww.sum(axis=(1, 2))
            with np.errstate(invalid="ignore"):
                out[int(r.mascon_id)] = np.nansum(blk * ww, axis=(1, 2)) / np.where(tot > 0, tot, np.nan)
        else:
            fallback += 1
            out[int(r.mascon_id)] = vals[:, np.abs(lat - r.lat_center).argmin(),
                                         np.abs(lon - r.lon_180).argmin()]
    if fallback:
        print(f"    {fallback} mascons smaller than a grid cell -> nearest-cell fallback")
    return pd.DataFrame(out, index=pd.to_datetime(da["time"].values))


# ------------------------------------------------------- GLDAS surface storage
storage = {}
for m in MODELS:
    g = xr.open_dataset(PROC / f"gldas_{m}_monthly.nc")
    s = to_mascons(A._NON_GW_STORAGE[m](g)) * CM_TO_MM  # cm -> mm
    storage[m] = s
    print(f"[{m}] {dict(g.sizes)} -> {s.shape[1]} mascons, mean {s.mean().mean():.0f} mm")

common_cols = sorted(set.intersection(*[set(s.columns) for s in storage.values()]))
gldas_mean = sum(storage[m][common_cols] for m in MODELS) / len(MODELS)

# ------------------------------------------------------------------- GRACE etc
tws = pd.read_parquet(SIG / "tws_mm.parquet")
res = pd.read_parquet(SIG / "reservoir_anomaly_mm.parquet")
for d in (tws, res):
    d.index = pd.to_datetime(d.index)
    d.columns = [int(c) for c in d.columns]

# Every mascon with any Nuevo Leon area, not only the ones carrying a monitored
# dam. A mascon with no dam has a reservoir anomaly of zero, which is a value,
# not a gap -- dropping those two would change the footprint and make the total
# incomparable with the report's -1.63 mm/yr state-weighted trend.
dammed = sorted(set(res.columns) & set(w[w > 0].index))
cols = sorted(set(tws.columns) & set(gldas_mean.columns) & set(w[w > 0].index))
for c in cols:
    if c not in res.columns:
        res[c] = 0.0
print(f"{len(cols)} mascons with state area, {len(dammed)} of them carrying a monitored dam")

common = tws.index.intersection(gldas_mean.index).intersection(res.index)
common = tws.loc[common, cols].dropna(how="all").index

# CONAGUA's dams stop reporting after 2025-04 for all but one of these
# mascons, and individual dams drop out for a month here and there earlier.
# Carrying the decomposition past the cut-off would compare a GRACE total
# against a reservoir term that no longer exists. Demanding all thirteen every
# month is too strict -- it would discard two decades over scattered single-dam
# gaps -- so the test is on weight: a month is kept when the mascons that
# reported carry at least 90% of the total weight, which the renormalised
# `weighted` then divides by correctly.
COVERAGE = 0.90
wc = w.loc[dammed]
share = (res.loc[common, dammed].notna() * wc).sum(axis=1) / wc.sum()
dropped = common[share < COVERAGE]
common = common[share >= COVERAGE]
print(f"full record: {len(common)} months {common.min():%Y-%m}..{common.max():%Y-%m}, {len(cols)} mascons")
if len(dropped):
    print(f"    dropped {len(dropped)} months with an incomplete reservoir record "
          f"({dropped.min():%Y-%m}..{dropped.max():%Y-%m})")


def decompose(idx, sm_source, label):
    """TWS = reservoir + soil-type storage + groundwater, on the given months."""
    t = tws.loc[idx, cols]
    r = res.loc[idx, cols]
    s = sm_source.loc[idx, cols]
    t_a = deseasonalise(t - t.mean())
    r_a = deseasonalise(r - r.mean())
    s_a = deseasonalise(s - s.mean())
    gw = t_a - r_a - s_a
    out = pd.DataFrame({
        "tws": weighted(t_a, w),
        "reservoir": weighted(r_a, w),
        "soil_moisture": weighted(s_a, w),
        "groundwater": weighted(gw, w),
        "tws_minus_reservoir_only": weighted(t_a - r_a, w),
    })
    stats = {}
    for k in out.columns:
        tr, p = fit(out[k])
        stats[f"trend_{k}_mm_yr"] = tr
        stats[f"p_{k}"] = p
        stats[f"std_{k}_mm"] = float(out[k].std())
    tt = stats["trend_tws_mm_yr"]
    for k in ("reservoir", "soil_moisture", "groundwater"):
        stats[f"{k}_share_of_tws_trend"] = stats[f"trend_{k}_mm_yr"] / tt
    print(f"\n--- {label} ({len(out)} months) ---")
    for k in out.columns:
        print(f"  {k:26s} {stats[f'trend_{k}_mm_yr']:+7.2f} mm/yr  p={stats[f'p_{k}']:.4f}")
    return out, stats


full, full_stats = decompose(common, gldas_mean, "GLDAS ensemble, full record 2002-2026")

# per-model, to show the spread of the answer rather than one model's opinion
per_model, per_model_gw = {}, {}
for m in MODELS:
    o, st = decompose(common, storage[m], f"GLDAS {m.upper()}, full record")
    per_model[m] = {k: st[k] for k in st if k.startswith("trend_")}
    per_model_gw[m] = o["groundwater"]
pd.DataFrame(per_model_gw).to_csv(SIG / "gldas_groundwater_by_model.csv")

# ------------------------------------------------ SMAP window, matched exactly
smap = pd.read_csv(SIG / "smap_decomposition_series.csv", index_col=0, parse_dates=True)
win = common.intersection(smap.index)
gl_win, gl_win_stats = decompose(win, gldas_mean, "GLDAS ensemble, SMAP window 2016-2025")
sm_soil = smap.loc[win, "soil_moisture"]
gl_soil = gl_win["soil_moisture"]
soil_r = float(np.corrcoef(sm_soil.values, gl_soil.values)[0, 1])
sm_tr, sm_p = fit(sm_soil)
print(f"\nsoil moisture on the shared window: SMAP {sm_tr:+.2f} mm/yr (p={sm_p:.3f}) vs "
      f"GLDAS {gl_win_stats['trend_soil_moisture_mm_yr']:+.2f} (p={gl_win_stats['p_soil_moisture']:.3f}), r={soil_r:.3f}")

# --------------------------------------- is the residual still a drought spike?
gwm = full["groundwater"]
pre = float(gwm.loc[:"2019-12"].mean())
# The trough of the drought excursion, not of the whole record -- the series
# also dips in 2003, and taking a global minimum would measure recovery from
# the wrong event.
drought = gwm.loc["2020-01":]
trough_month = drought.idxmin()
trough = float(drought.min())
# "Post" is whatever record exists after the trough, which the reservoir cut-off
# makes short. Counted, because a recovery percentage from a handful of months
# is a weaker statement than one from a settled post-drought level.
post_window = gwm.loc[trough_month + pd.offsets.MonthBegin(1):]
post = float(post_window.mean())
n_post = int(post_window.notna().sum())
recovered = (post - trough) / (pre - trough) * 100 if pre != trough else np.nan
lk = float((meta.set_index("mascon_id").loc[cols, "leakage_trend_cm_yr"].abs()
            * w.loc[cols] / w.loc[cols].sum()).sum() * CM_TO_MM)
print(f"\ngroundwater excursion: pre-2020 mean {pre:+.1f} mm, trough {trough:+.1f} mm at "
      f"{trough_month:%Y-%m}, post-trough mean {post:+.1f} mm over {n_post} months "
      f"-> {recovered:.0f}% recovered")
print(f"leakage trend floor (NL-weighted) {lk:.2f} mm/yr")

full.to_csv(SIG / "gldas_decomposition_series.csv")
summary = {
    "window_full": [f"{common.min():%Y-%m}", f"{common.max():%Y-%m}"],
    "n_months_full": len(common),
    "n_mascons": len(cols),
    "models": list(MODELS),
    "full_record": full_stats,
    "per_model_trends": per_model,
    "smap_window": {
        "months": len(win),
        "gldas": gl_win_stats,
        "smap_soil_trend_mm_yr": sm_tr,
        "smap_soil_p": sm_p,
        "soil_series_correlation_smap_vs_gldas": soil_r,
    },
    "groundwater_excursion": {
        "pre_2020_mean_mm": pre,
        "trough_mm": trough,
        "trough_month": f"{trough_month:%Y-%m}",
        "post_trough_mean_mm": post,
        "n_months_after_trough": n_post,
        "post_trough_window": [f"{post_window.index.min():%Y-%m}", f"{post_window.index.max():%Y-%m}"]
        if n_post else None,
        "pct_of_drop_recovered": recovered,
        "leakage_trend_floor_mm_yr": lk,
    },
}
json.dump(summary, open(TR / "gldas_decomposition_summary.json", "w"), indent=2)
print("\nwrote", SIG / "gldas_decomposition_series.csv")
print("wrote", TR / "gldas_decomposition_summary.json")
