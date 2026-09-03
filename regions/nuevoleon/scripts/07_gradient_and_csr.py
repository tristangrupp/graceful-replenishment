"""Phase 4: the post-2020 divergence, and whether CSR reproduces it.

Panel C of `trends/decorrelation.png` showed mascons far from the region
centre dropping to about -150 mm after 2020 while the central reference held
near -60 mm. This asks four things of that:

  * where the boundary is -- is "distance from centre" actually the right
    variable, or is it a north/south (Texas / Mexico) split?
  * how large it is, in mm, with reservoirs removed
  * whether CSR RL06.3, an independent solution on a 0.25 deg grid, shows
    the same thing on the same mascon footprints
  * whether CHIRPS precipitation explains it, and how its timing sits
    against the 2022-07..2023-04 drought window established independently
    by the SMAP/SPI-12 study in H:\\water intelligence\\soilmoisture

CSR's time axis is spelled `Units` with a capital U, so xarray's CF decoder
skips it and every timestamp collapses to 1970. Opened with
decode_times=False and rebuilt from the attribute by hand.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import trend as T  # noqa: E402

ROOT = Path(r"E:\Water\NuevoLeon")
SIG, TR = ROOT / "signals", ROOT / "trends"
CSR = Path(r"E:\Water\Saudi\raw\csr_rl0603_mascons.nc")
LANDMASK = ROOT / "raw" / "chirps_landmask_native.nc"
BASELINE = ("2004-01-01", "2009-12-31")
POST = "2020-01-01"
DROUGHT = ("2022-07-01", "2023-04-30")     # SPI-12 event, soilmoisture study
PRE_DROUGHT = ("2015-01-01", "2019-12-31")


def csr_time(ds):
    t = ds["time"]
    unit = t.attrs.get("units") or t.attrs.get("Units", "")
    epoch = unit.split("since")[-1].strip().replace("Z", "") if "since" in unit else "2002-01-01"
    return pd.to_datetime(epoch) + pd.to_timedelta(t.values.astype("float64"), unit="D")


def land_fraction_grid(lat_edges, lon_edges_180):
    """Land fraction of each cell of a target grid, from CHIRPS' own ocean NaNs.

    Needed because the eastern mascon boxes straddle the Gulf of Mexico
    coastline. CSR is a global 0.25 deg field with real ocean values in it,
    so a plain box average over those footprints mixes ocean mass into the
    land signal and pulls the amplitude toward zero - which is exactly what
    an unmasked first pass produced (mascon 1821: GSFC -208 mm post-2020
    against CSR -10 mm, series r = 0.36, versus r = 0.85-0.94 inland).
    """
    d = xr.open_dataset(LANDMASK, decode_times=False)
    p = d["precipitation"].values[0]
    cy, cx = d["Y"].values, d["X"].values           # 0.05 deg, lon in -180..180
    land = np.isfinite(p).astype(float)
    d.close()
    out = np.zeros((len(lat_edges) - 1, len(lon_edges_180) - 1))
    for i in range(len(lat_edges) - 1):
        my = (cy >= lat_edges[i]) & (cy < lat_edges[i + 1])
        if not my.any():
            out[i] = np.nan
            continue
        for j in range(len(lon_edges_180) - 1):
            mx = (cx >= lon_edges_180[j]) & (cx < lon_edges_180[j + 1])
            out[i, j] = land[np.ix_(my, mx)].mean() if mx.any() else np.nan
    return out


def csr_on_footprints(mas):
    ds = xr.open_dataset(CSR, decode_times=False)
    da = (ds["lwe_thickness"] * 10.0).assign_coords(time=csr_time(ds))    # cm -> mm
    lat, lon = da["lat"].values, da["lon"].values                        # lon 0-360
    lon180 = ((lon + 180) % 360) - 180
    # land fraction of every 0.25 deg CSR cell in the window
    win_lat = (lat >= 21.0) & (lat < 30.0)
    win_lon = (lon180 >= -103.5) & (lon180 < -96.0)
    lat_e = np.append(lat[win_lat] - 0.125, lat[win_lat][-1] + 0.125)
    lon_e = np.append(lon180[win_lon] - 0.125, lon180[win_lon][-1] + 0.125)
    lf_win = land_fraction_grid(lat_e, np.sort(lon_e))
    lf = np.zeros((len(lat), len(lon)))
    order = np.argsort(lon180[win_lon])
    lf[np.ix_(np.where(win_lat)[0], np.where(win_lon)[0][order])] = lf_win
    w = np.cos(np.radians(lat))
    out, mas_land = {}, {}
    for _, r in mas.iterrows():
        lo, hi = r["lon_min"] % 360, r["lon_max"] % 360
        latm = (lat >= r["lat_min"]) & (lat < r["lat_max"])
        lonm = (lon >= lo) & (lon < hi) if lo < hi else ((lon >= lo) | (lon < hi))
        if not latm.any() or not lonm.any():
            continue
        li, lj = np.where(latm)[0], np.where(lonm)[0]
        blk = da.isel(lat=li, lon=lj)
        wt = w[latm][:, None] * lf[np.ix_(li, lj)]
        mas_land[int(r["mascon_id"])] = float(lf[np.ix_(li, lj)].mean())
        if wt.sum() == 0:
            continue
        ww = xr.DataArray(wt, dims=("lat", "lon"),
                          coords={"lat": blk["lat"], "lon": blk["lon"]})
        out[int(r["mascon_id"])] = blk.weighted(ww).mean(dim=("lat", "lon")).to_series()
    ds.close()
    pd.Series(mas_land, name="mascon_land_fraction").to_csv(
        ROOT / "inventory" / "mascon_land_fraction.csv")
    df = pd.DataFrame(out)
    df.index = pd.DatetimeIndex(df.index)
    df = df.groupby(df.index.to_period("M").to_timestamp()).mean()
    df.index.name = "time"
    # CSR ships its own baseline; re-reference to the GSFC one so the two are comparable
    base = df.loc[BASELINE[0]:BASELINE[1]].mean()
    return df - base


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def level(df, start, end=None):
    sl = df.loc[start:end] if end else df.loc[start:]
    return sl.mean()


def main():
    mas = pd.read_csv(SIG / "mascon_metadata.csv")
    tws = pd.read_parquet(SIG / "tws_mm.parquet")
    minus = pd.read_parquet(SIG / "tws_minus_reservoir_mm.parquet")
    tws.columns = [int(c) for c in tws.columns]
    minus.columns = [int(c) for c in minus.columns]
    dec = pd.read_csv(TR / "mascon_decomposition.csv")
    ids = list(tws.columns)

    csr = csr_on_footprints(mas)
    csr = csr.reindex(columns=ids)
    csr.to_parquet(SIG / "csr_tws_mm.parquet")

    # the reference used by the decorrelation figure: land mascon nearest the
    # mean of the land-mascon centres
    clat, clon = mas["lat_center"].mean(), mas["lon_180"].mean()
    ref = int(mas.loc[((mas["lat_center"] - clat).abs()
                       + (mas["lon_180"] - clon).abs()).idxmin(), "mascon_id"])
    rlat = float(mas.loc[mas.mascon_id == ref, "lat_center"].iloc[0])
    rlon = float(mas.loc[mas.mascon_id == ref, "lon_180"].iloc[0])

    g = dec.set_index("mascon_id").loc[ids].copy()
    lf = pd.read_csv(ROOT / "inventory" / "mascon_land_fraction.csv", index_col=0).iloc[:, 0]
    g["land_frac"] = lf.reindex(g.index).to_numpy()
    g["dist_km"] = haversine(rlat, rlon, g["lat_center"].to_numpy(), g["lon_180"].to_numpy())
    g["post2020_tws_mm"] = level(tws, POST).reindex(ids).to_numpy()
    g["post2020_minusres_mm"] = level(minus, POST).reindex(ids).to_numpy()
    g["post2020_csr_mm"] = level(csr, POST).reindex(ids).to_numpy()
    g["pre2020_tws_mm"] = level(tws, "2010-01-01", "2019-12-31").reindex(ids).to_numpy()
    g["drought_tws_mm"] = level(tws, *DROUGHT).reindex(ids).to_numpy()
    g["drought_minusres_mm"] = level(minus, *DROUGHT).reindex(ids).to_numpy()
    g["drought_csr_mm"] = level(csr, *DROUGHT).reindex(ids).to_numpy()
    g["predrought_tws_mm"] = level(tws, *PRE_DROUGHT).reindex(ids).to_numpy()
    g["drought_drawdown_mm"] = g["drought_tws_mm"] - g["predrought_tws_mm"]
    g["drought_drawdown_minusres_mm"] = (g["drought_minusres_mm"]
                                         - level(minus, *PRE_DROUGHT).reindex(ids).to_numpy())

    # CHIRPS cumulative anomaly at the same epochs
    cum = pd.read_parquet(SIG / "chirps_cumulative_anomaly_cm.parquet")
    cum.columns = [int(c) for c in cum.columns]
    g["post2020_cum_precip_cm"] = level(cum, POST).reindex(ids).to_numpy()
    g["drought_cum_precip_cm"] = level(cum, *DROUGHT).reindex(ids).to_numpy()

    g = g.reset_index()
    g.to_csv(TR / "post2020_gradient.csv", index=False)

    # --- which spatial variable actually organises the post-2020 level?
    def reg(y, x):
        m = np.isfinite(y) & np.isfinite(x)
        r = stats.linregress(x[m], y[m])
        return {"slope": float(r.slope), "r2": float(r.rvalue ** 2), "p": float(r.pvalue),
                "n": int(m.sum())}

    y = g["post2020_minusres_mm"].to_numpy()
    predictors = {
        "distance_from_centre_km": g["dist_km"].to_numpy(),
        "latitude": g["lat_center"].to_numpy(),
        "longitude": g["lon_180"].to_numpy(),
        "nuevo_leon_area_fraction": g["nl_area_frac"].to_numpy(),
        "cumulative_chirps_anomaly_cm": g["post2020_cum_precip_cm"].to_numpy(),
    }
    fits = {k: reg(y, v) for k, v in predictors.items()}
    fits_tws = {k: reg(g["post2020_tws_mm"].to_numpy(), v) for k, v in predictors.items()}
    fits_csr = {k: reg(g["post2020_csr_mm"].to_numpy(), v) for k, v in predictors.items()}

    # --- GSFC vs CSR agreement
    both = pd.concat([tws.stack().rename("gsfc"), csr.stack().rename("csr")], axis=1).dropna()
    per_r, per_tr = {}, {}
    for c in ids:
        a = pd.concat([tws[c], csr[c]], axis=1).dropna()
        per_r[c] = float(a.corr().iloc[0, 1]) if len(a) > 30 else np.nan
        s = csr[c].dropna()
        s.index = pd.DatetimeIndex(s.index, name="time")
        da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                          coords={"time": s.index, "x": [0]})
        per_tr[c] = float(T.fit_trend(da)["trend"].values[0])
    g["csr_r"] = pd.Series(per_r).reindex(g["mascon_id"]).to_numpy()
    g["csr_trend_mm_yr"] = pd.Series(per_tr).reindex(g["mascon_id"]).to_numpy()
    g.to_csv(TR / "post2020_gradient.csv", index=False)

    w = g["area_km2"].to_numpy()
    wnl = w * np.nan_to_num(g["nl_area_frac"].to_numpy())

    def _wm(df, weights, cols=None, min_cover=0.90):
        """Weighted mean over available mascons; a month with no data stays NaN.

        A plain nansum over w.sum() would score a month in which every mascon is
        missing as exactly 0 mm and feed 33 fictitious zeros into every trend fit.
        """
        cols = list(cols) if cols is not None else ids
        m = df[cols].to_numpy()
        ok = np.isfinite(m)
        ws = (ok * weights).sum(axis=1)
        val = np.nansum(np.where(ok, m, 0.0) * weights, axis=1) / np.where(ws > 0, ws, np.nan)
        return pd.Series(np.where(ws / weights.sum() >= min_cover, val, np.nan), index=df.index)

    def wmean_series(df):
        return _wm(df, w)

    def wmean_series_nl(df):
        return _wm(df, wnl)

    reg_ser = pd.DataFrame({
        "gsfc_tws": wmean_series(tws), "gsfc_minus_res": wmean_series(minus),
        "csr_tws": wmean_series(csr),
        "gsfc_tws_nl": wmean_series_nl(tws), "gsfc_minus_res_nl": wmean_series_nl(minus),
        "csr_tws_nl": wmean_series_nl(csr),
    })
    reg_ser.to_csv(SIG / "regional_series_with_csr.csv")

    def tfit(s):
        s = s.dropna()
        s.index = pd.DatetimeIndex(s.index, name="time")
        da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                          coords={"time": s.index, "x": [0]})
        r = T.fit_trend(da)
        return float(r["trend"].values[0]), float(r["p_value"].values[0])

    far = g[g["dist_km"] > 300]["mascon_id"]
    near = g[g["dist_km"] <= 150]["mascon_id"]
    tx = g[g["nl_area_frac"] < 0.01]["mascon_id"]
    nl = g[g["nl_area_frac"] > 0.2]["mascon_id"]

    def grp(df, members):
        m = [c for c in members if c in df.columns]
        aw = g.set_index("mascon_id").loc[m, "area_km2"].to_numpy()
        return _wm(df, aw, cols=m)

    summary = {
        "reference_mascon": ref, "reference_lat": rlat, "reference_lon": rlon,
        "post2020_window": f"{POST}..{tws.index.max():%Y-%m}",
        "drought_window_from_soilmoisture_study": list(DROUGHT),
        "post2020_level_vs": fits,
        "post2020_level_vs_tws_unadjusted": fits_tws,
        "post2020_level_vs_csr": fits_csr,
        "gsfc_csr_median_per_mascon_r": float(np.nanmedian(list(per_r.values()))),
        "gsfc_csr_trend_r": float(np.corrcoef(
            g["tws_trend_mm_yr"], g["csr_trend_mm_yr"])[0, 1]),
        "gsfc_csr_mean_trend_diff_mm_yr": float(
            (g["csr_trend_mm_yr"] - g["tws_trend_mm_yr"]).mean()),
        "n_sign_disagreement": int(((g["tws_trend_mm_yr"] < 0)
                                    != (g["csr_trend_mm_yr"] < 0)).sum()),
        "post2020_mean_mm": {
            "far_gt300km_gsfc": float(g[g.dist_km > 300]["post2020_tws_mm"].mean()),
            "near_le150km_gsfc": float(g[g.dist_km <= 150]["post2020_tws_mm"].mean()),
            "far_gt300km_csr": float(g[g.dist_km > 300]["post2020_csr_mm"].mean()),
            "near_le150km_csr": float(g[g.dist_km <= 150]["post2020_csr_mm"].mean()),
            "outside_nuevo_leon_gsfc": float(g[g.nl_area_frac < 0.01]["post2020_tws_mm"].mean()),
            "inside_nuevo_leon_gsfc": float(g[g.nl_area_frac > 0.2]["post2020_tws_mm"].mean()),
            "outside_nuevo_leon_csr": float(g[g.nl_area_frac < 0.01]["post2020_csr_mm"].mean()),
            "inside_nuevo_leon_csr": float(g[g.nl_area_frac > 0.2]["post2020_csr_mm"].mean()),
            "inside_nuevo_leon_gsfc_minus_reservoir":
                float(g[g.nl_area_frac > 0.2]["post2020_minusres_mm"].mean()),
        },
        "drought_drawdown_mm_vs_2015_2019": {
            "inside_nuevo_leon_tws": float(g[g.nl_area_frac > 0.2]["drought_drawdown_mm"].mean()),
            "inside_nuevo_leon_minus_reservoir":
                float(g[g.nl_area_frac > 0.2]["drought_drawdown_minusres_mm"].mean()),
            "outside_nuevo_leon_tws": float(g[g.nl_area_frac < 0.01]["drought_drawdown_mm"].mean()),
        },
        "regional_trends_mm_yr": {k: tfit(reg_ser[k]) for k in reg_ser.columns},
        "group_trends_mm_yr": {
            "far_gt300km_gsfc": tfit(grp(tws, far)), "near_le150km_gsfc": tfit(grp(tws, near)),
            "far_gt300km_csr": tfit(grp(csr, far)), "near_le150km_csr": tfit(grp(csr, near)),
            "outside_nl_gsfc": tfit(grp(tws, tx)), "inside_nl_gsfc": tfit(grp(tws, nl)),
            "outside_nl_csr": tfit(grp(csr, tx)), "inside_nl_csr": tfit(grp(csr, nl)),
            "inside_nl_gsfc_minus_res": tfit(grp(minus, nl)),
        },
        "n_csr_months": int(csr.notna().any(axis=1).sum()),
        "csr_first_month": str(csr.dropna(how="all").index.min().date()),
        "csr_last_month": str(csr.dropna(how="all").index.max().date()),
    }
    (TR / "gradient_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
