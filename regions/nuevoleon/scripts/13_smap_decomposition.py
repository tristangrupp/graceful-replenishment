"""Remove the soil-moisture component from Nuevo Leon GRACE using SMAP L4.

The reservoir correction accounted for 67% of the GSFC trend and left a
residual of -0.54 mm/yr that could not be called groundwater, because soil
moisture had never been removed. This removes it.

    TWS = reservoir + soil moisture + residual

SMAP L4 root-zone soil moisture (SPL4SMGP, 0-100 cm, 9 km EASE-Grid 2.0) is
already on disk from an earlier drought study at
`H:\\water intelligence\\soilmoisture`, as monthly means 2016-01..2025-12.

Three things this does not fix, stated up front:

- SMAP L4 is a **model assimilation** product, not a direct observation. Its
  root-zone field is a land-surface model constrained by L-band brightness
  temperature, so removing it removes a model's opinion of soil moisture.
- The profile stops at **1 m**. Unsaturated storage between 1 m and the water
  table is in neither the SMAP term nor any reservoir, so it stays in the
  residual.
- SMAP begins 2015-04, so this runs on **2016-2025**, a 10-year window against
  the 24-year record the reservoir work used. The reservoir-only trends are
  therefore recomputed on the identical short window, because comparing a
  short-window residual against a full-record one would be meaningless.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import Transformer

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import trend as trend_mod  # noqa: E402

NL = Path(r"E:\Water\NuevoLeon")
SM = Path(r"H:\water intelligence\soilmoisture")
OUT_S, OUT_T = NL / "signals", NL / "trends"

# EASE-Grid 2.0 global 9 km, from the source study's smap_config.py
EASE2_EPSG = "EPSG:6933"
EASE2_NCOLS, EASE2_NROWS = 3856, 1624
EASE2_XMIN, EASE2_XMAX = -17367530.45, 17367530.45
EASE2_YMAX = 7314540.83
EASE2_RES = (EASE2_XMAX - EASE2_XMIN) / EASE2_NCOLS      # 9008.055 m

RZ_DEPTH_MM = 1000.0     # sm_rootzone is volumetric over 0-100 cm


def ease_latlon(row0, col0, ny, nx):
    """Cell-centre lat/lon for a window of the global EASE-2 9 km grid."""
    cols = col0 + np.arange(nx)
    rows = row0 + np.arange(ny)
    x = EASE2_XMIN + (cols + 0.5) * EASE2_RES
    y = EASE2_YMAX - (rows + 0.5) * EASE2_RES
    xx, yy = np.meshgrid(x, y)
    tf = Transformer.from_crs(EASE2_EPSG, "EPSG:4326", always_xy=True)
    lon, lat = tf.transform(xx, yy)
    return lat, lon


def load_smap():
    z = np.load(SM / "data" / "sm_monthly.npz")
    rzsm, ym = z["rzsm"], z["ym"]
    win = json.loads((SM / "data" / "window.json").read_text())
    lat, lon = ease_latlon(win["row0"], win["col0"], rzsm.shape[1], rzsm.shape[2])
    times = pd.to_datetime([f"{v // 100}-{v % 100:02d}-01" for v in ym])
    # Volumetric water content -> mm of water over the 0-100 cm profile.
    return rzsm * RZ_DEPTH_MM, lat, lon, times


def smap_to_mascons(sm_mm, lat, lon, meta):
    """Mean SMAP storage (mm) inside each mascon box. EASE-2 is equal-area, so
    an unweighted mean of the cells inside is already area-correct."""
    out, counts = {}, {}
    flat_lat, flat_lon = lat.ravel(), lon.ravel()
    flat = sm_mm.reshape(sm_mm.shape[0], -1)
    for _, r in meta.iterrows():
        lo = ((r["lon_180"] - r["lon_span"] / 2), (r["lon_180"] + r["lon_span"] / 2))
        inside = ((flat_lat >= r["lat_center"] - r["lat_span"] / 2)
                  & (flat_lat < r["lat_center"] + r["lat_span"] / 2)
                  & (flat_lon >= lo[0]) & (flat_lon < lo[1]))
        if inside.sum() == 0:
            continue
        out[int(r["mascon_id"])] = flat[:, inside].mean(axis=1)
        counts[int(r["mascon_id"])] = int(inside.sum())
    return pd.DataFrame(out), counts


def deseasonalise(df):
    return df - df.groupby(df.index.month).transform("mean")


def fit(series):
    s = pd.Series(series).dropna()
    if len(s) < 36:
        return np.nan, np.nan
    import xarray as xr
    da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                      coords={"time": s.index, "x": [0]})
    r = trend_mod.fit_trend(da)
    return float(r["trend"].values[0]), float(r["p_value"].values[0])


def weighted(df, w):
    cols = [c for c in df.columns if c in w.index]
    ww = w.loc[cols]
    ww = ww / ww.sum()
    return (df[cols] * ww).sum(axis=1, min_count=1)


def main():
    # `nl_area_frac` lives on the decomposition table rather than the metadata,
    # and it is what the reservoir-only headline weighted by. Reuse it so this
    # result is directly comparable rather than differently weighted.
    meta = pd.read_csv(NL / "signals" / "mascon_metadata.csv")
    dec = pd.read_csv(NL / "trends" / "mascon_decomposition.csv")
    meta = meta.merge(dec[["mascon_id", "nl_area_frac"]], on="mascon_id", how="left")
    meta["nl_area_frac"] = meta["nl_area_frac"].fillna(0.0)
    frac_col = "nl_area_frac"
    print(f"NL-weighted mascons: {(meta[frac_col] > 0).sum()} with any state area, "
          f"{(meta[frac_col] > 0.2).sum()} above 20%")

    sm_mm, lat, lon, sm_times = load_smap()
    print(f"SMAP {sm_mm.shape[0]} months {sm_times.min():%Y-%m}..{sm_times.max():%Y-%m}, "
          f"grid {sm_mm.shape[1]}x{sm_mm.shape[2]}, "
          f"lat {lat.min():.2f}..{lat.max():.2f} lon {lon.min():.2f}..{lon.max():.2f}")

    sm, counts = smap_to_mascons(sm_mm, lat, lon, meta)
    sm.index = sm_times
    print(f"SMAP mapped onto {sm.shape[1]} mascons "
          f"({min(counts.values())}-{max(counts.values())} EASE cells each)")

    tws = pd.read_parquet(NL / "signals" / "tws_mm.parquet")
    res = pd.read_parquet(NL / "signals" / "reservoir_anomaly_mm.parquet")
    csr = pd.read_parquet(NL / "signals" / "csr_tws_mm.parquet")
    for d in (tws, res, csr):
        d.index = pd.to_datetime(d.index)
        d.columns = [int(c) for c in d.columns]

    common = tws.index.intersection(sm.index).intersection(res.index)
    cols = sorted(set(tws.columns) & set(sm.columns) & set(res.columns))
    print(f"common months {len(common)}: {common.min():%Y-%m}..{common.max():%Y-%m}; "
          f"{len(cols)} mascons")

    tws_c, sm_c, res_c = tws.loc[common, cols], sm.loc[common, cols], res.loc[common, cols]
    csr_c = csr.loc[csr.index.intersection(common), cols] if len(csr.columns) else None

    # Anomalies relative to this window, then seasonal cycle removed.
    tws_a = deseasonalise(tws_c - tws_c.mean())
    sm_a = deseasonalise(sm_c - sm_c.mean())
    res_a = deseasonalise(res_c - res_c.mean())
    resid = tws_a - res_a - sm_a

    w = meta.set_index("mascon_id")[frac_col] * meta.set_index("mascon_id")["area_km2"]

    series = {
        "tws": weighted(tws_a, w),
        "reservoir": weighted(res_a, w),
        "soil_moisture": weighted(sm_a, w),
        "residual": weighted(resid, w),
        "tws_minus_reservoir_only": weighted(tws_a - res_a, w),
    }
    if csr_c is not None and len(csr_c) > 36:
        cc = csr_c.index
        csr_a = deseasonalise(csr_c - csr_c.mean())
        series["csr_tws"] = weighted(csr_a, w)
        series["csr_residual"] = weighted(
            csr_a - res_a.loc[cc] - sm_a.loc[cc], w)

    reg = pd.DataFrame(series)
    reg.to_csv(OUT_S / "smap_decomposition_series.csv")

    summary = {
        "window": [f"{common.min():%Y-%m}", f"{common.max():%Y-%m}"],
        "n_months": int(len(common)),
        "n_mascons": len(cols),
        "smap_product": "SPL4SMGP v008 sm_rootzone (0-100 cm), monthly means",
        "smap_ease_cells_per_mascon": {"min": min(counts.values()), "max": max(counts.values())},
        "note_short_window": ("Reservoir-only trends are recomputed on this same 2016-2025 "
                              "window, so they differ from the 2002-2026 headline."),
    }
    for k, s in series.items():
        t, p = fit(s)
        summary[f"trend_{k}_mm_yr"] = t
        summary[f"p_{k}"] = p
        summary[f"std_{k}_mm"] = float(s.std())

    tws_t = summary["trend_tws_mm_yr"]
    if tws_t:
        summary["reservoir_share_of_tws_trend"] = summary["trend_reservoir_mm_yr"] / tws_t
        summary["soilmoisture_share_of_tws_trend"] = summary["trend_soil_moisture_mm_yr"] / tws_t
        summary["residual_share_of_tws_trend"] = summary["trend_residual_mm_yr"] / tws_t

    # Per-mascon table, so the northern mascon 3149 can be checked specifically.
    rows = []
    for c in cols:
        tt, tp = fit(tws_a[c])
        rt, _ = fit(res_a[c])
        st, _ = fit(sm_a[c])
        dt, dp = fit(resid[c])
        m = meta[meta["mascon_id"] == c].iloc[0]
        rows.append({"mascon_id": c, "lat": m["lat_center"], "lon": m["lon_180"],
                     "nl_frac": m[frac_col],
                     "tws_trend": tt, "tws_p": tp, "reservoir_trend": rt,
                     "soilmoisture_trend": st, "residual_trend": dt, "residual_p": dp,
                     "sm_std_mm": float(sm_a[c].std())})
    per = pd.DataFrame(rows).sort_values("residual_trend")
    per.to_csv(OUT_T / "smap_per_mascon.csv", index=False)

    (OUT_T / "smap_decomposition_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nmost negative residuals after removing reservoirs AND soil moisture")
    print(per.head(6)[["mascon_id", "lat", "lon", "nl_frac", "tws_trend",
                       "reservoir_trend", "soilmoisture_trend", "residual_trend", "residual_p"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.3f}"))


if __name__ == "__main__":
    main()
