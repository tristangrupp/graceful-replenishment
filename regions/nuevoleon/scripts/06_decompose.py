"""Phase 3: decompose per-mascon TWS into reservoir, precipitation and residual.

For every land mascon in the window:

  1. monthly TWS anomaly (mm, GSFC baseline 2004-01..2009-12)
  2. minus the mascon's reservoir-storage anomaly on the same baseline
  3. trend of each, fitted with `fit_trend` (trend + annual + semi-annual
     harmonics, lag-1 autocorrelation-corrected p-value)
  4. the same trend refitted with cumulative CHIRPS precipitation anomaly
     as a covariate (`precipitation.adjusted_trend`)

The output is deliberately named `residual`, not groundwater: soil moisture
is still in it, and unmonitored small dams and stock ponds are too.

Also computes each mascon's area fraction inside the Nuevo Leon state
polygon, so results can be reported for the state rather than for a box.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box as shp_box

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import precipitation as P  # noqa: E402
from dark_water.depletion_watchlist.depletion import trend as T  # noqa: E402

ROOT = Path(r"E:\Water\NuevoLeon")
SIG, INV, TR = ROOT / "signals", ROOT / "inventory", ROOT / "trends"
NL_POLY = Path(r"H:\water intelligence\soilmoisture\data\nuevo_leon.geojson")
CHIRPS = ROOT / "raw" / "chirps_v2p0_monthly_nuevoleon_0p5deg.nc"
BASELINE = ("2004-01", "2009-12")


def mascon_frames():
    mas = pd.read_csv(SIG / "mascon_metadata.csv")
    long = pd.read_parquet(SIG / "mascon_monthly_long.parquet")
    tws = long.pivot(index="month", columns="mascon_id", values="lwe_cm") * 10.0   # mm
    tws.index = pd.DatetimeIndex(tws.index)
    tws.index.name = "time"
    tws.columns.name = None
    return mas, long, tws


def nl_fraction(mas):
    """Fraction of each mascon box inside the Nuevo Leon state polygon."""
    if not NL_POLY.exists():
        return pd.Series(np.nan, index=mas["mascon_id"])
    nl = gpd.read_file(NL_POLY).to_crs(4326).union_all()
    frac = []
    for _, r in mas.iterrows():
        b = shp_box(r["lon_min"], r["lat_min"], r["lon_max"], r["lat_max"])
        frac.append(b.intersection(nl).area / b.area)
    return pd.Series(frac, index=mas["mascon_id"])


def chirps_on_mascons(mas):
    """Monthly CHIRPS depth (cm) averaged over each mascon box, complete axis."""
    ch = xr.open_dataset(CHIRPS, decode_times=False)
    per = pd.PeriodIndex([pd.Period("1960-01", "M") + int(np.floor(x))
                          for x in ch["T"].values], freq="M")
    pr = ch["precipitation"].values / 10.0                     # mm/month -> cm/month
    cy, cx = ch["Y"].values, ch["X"].values
    out = np.full((len(mas), len(per)), np.nan)
    ncell = np.zeros(len(mas), int)
    for i, r in mas.reset_index(drop=True).iterrows():
        my = (cy >= r["lat_min"]) & (cy < r["lat_max"])
        mx = (cx >= r["lon_min"]) & (cx < r["lon_max"])
        if my.sum() and mx.sum():
            blk = pr[:, my, :][:, :, mx]
            ncell[i] = int(np.isfinite(blk[0]).sum())
            with np.errstate(invalid="ignore"):
                out[i] = np.nanmean(blk, axis=(1, 2))
    ch.close()
    return per, out, ncell


def fit(series_df, ids):
    """fit_trend over a months x mascon frame; NaN months dropped per mascon."""
    tr, pv = {}, {}
    for c in ids:
        s = series_df[c].dropna()
        s.index = pd.DatetimeIndex(s.index, name="time")
        da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                          coords={"time": s.index, "x": [0]})
        r = T.fit_trend(da)
        tr[c] = float(r["trend"].values[0])
        pv[c] = float(r["p_value"].values[0])
    return pd.Series(tr), pd.Series(pv)


def main():
    TR.mkdir(parents=True, exist_ok=True)
    mas, long, tws = mascon_frames()
    ids = list(tws.columns)

    res = pd.read_parquet(SIG / "reservoir_anomaly_mm.parquet")
    res.columns = [int(c) for c in res.columns]
    res = res.reindex(index=tws.index).reindex(columns=ids)
    # Mascons with no monitored dam have a genuinely zero reservoir term; mascons
    # with dams have NaN in months where the dam record is absent, and those months
    # must drop out of the paired comparison rather than be zero-filled.
    has_dam = res.notna().any()
    res.loc[:, ~has_dam] = 0.0
    minus = tws - res                        # NaN propagates per mascon, per month
    # The unadjusted trend is refitted on exactly the months the adjusted one has,
    # so the two are never compared over different records.
    tws_full = tws.copy()
    tws_paired = tws.where(minus.notna())
    res = res.fillna(0.0)
    tws_full.to_parquet(SIG / "tws_mm_full_record.parquet")
    minus.notna().to_parquet(SIG / "reservoir_defined_mask.parquet")
    tws.to_parquet(SIG / "tws_mm.parquet")
    minus.to_parquet(SIG / "tws_minus_reservoir_mm.parquet")

    # --- CHIRPS covariate on the complete monthly axis, then sampled at GRACE months
    per, prm, ncell = chirps_on_mascons(mas)
    span = (per >= pd.Period("2002-04", "M")) & (per <= pd.Period("2026-06", "M"))
    per_s, prm_s = per[span], prm[:, span]
    precip_da = xr.DataArray(prm_s.T, dims=("time", "mascon"),
                             coords={"time": per_s.to_timestamp(), "mascon": mas["mascon_id"]})
    cum = P.cumulative_anomaly(precip_da, dim="time")
    cum_df = pd.DataFrame(cum.values, index=per_s.to_timestamp(), columns=mas["mascon_id"])
    cum_df.to_parquet(SIG / "chirps_cumulative_anomaly_cm.parquet")
    pd.DataFrame(prm_s.T, index=per_s.to_timestamp(),
                 columns=mas["mascon_id"]).to_parquet(SIG / "chirps_monthly_cm.parquet")

    def adj(series_df):
        """Precipitation-adjusted trend, one mascon at a time.

        `adjusted_trend` drops any column with a NaN anywhere, so mascons whose
        reservoir record is short would silently vanish if the whole frame were
        passed at once. Each mascon is fitted on its own complete months instead.
        """
        rows = {}
        for c in ids:
            s = series_df[c].dropna()
            s.index = pd.DatetimeIndex(s.index, name="time")
            if len(s) < 60:
                rows[c] = (np.nan, np.nan, np.nan)
                continue
            y = xr.DataArray(s.to_numpy()[:, None], dims=("time", "m"),
                             coords={"time": s.index, "m": [0]})
            k = xr.DataArray(cum_df.reindex(s.index)[c].to_numpy()[:, None],
                             dims=("time", "m"), coords={"time": s.index, "m": [0]})
            a = P.adjusted_trend(y, k, dim="time")
            rows[c] = (float(a["trend"].values[0]), float(a["p_value"].values[0]),
                       float(a["fraction_unexplained"].values[0]))
        return pd.DataFrame(rows, index=["trend", "p", "frac_unexplained"]).T

    tr_tws, p_tws = fit(tws, ids)
    tr_pair, p_pair = fit(tws_paired, ids)
    tr_min, p_min = fit(minus, ids)
    a_tws = adj(tws)
    a_min = adj(minus)

    out = pd.DataFrame({"mascon_id": ids})
    out = out.merge(mas[["mascon_id", "lat_center", "lon_180", "area_km2",
                         "leakage_2sigma_cm", "leakage_trend_cm_yr"]], on="mascon_id")
    out["nl_area_frac"] = nl_fraction(mas).reindex(out["mascon_id"]).to_numpy()
    out["chirps_cells"] = ncell
    out["chirps_mm_yr"] = np.nanmean(prm_s, axis=1) * 12 * 10
    out["tws_trend_mm_yr"] = tr_tws.reindex(out["mascon_id"]).to_numpy()
    out["tws_p"] = p_tws.reindex(out["mascon_id"]).to_numpy()
    out["res_trend_mm_yr"] = [
        float(np.polyfit(np.arange(len(res)) / 12.0, res[c], 1)[0]) if res[c].abs().sum() else 0.0
        for c in out["mascon_id"]]
    out["tws_trend_paired_mm_yr"] = tr_pair.reindex(out["mascon_id"]).to_numpy()
    out["n_months_reservoir_defined"] = minus.notna().sum().reindex(out["mascon_id"]).to_numpy()
    out["minus_res_trend_mm_yr"] = tr_min.reindex(out["mascon_id"]).to_numpy()
    out["minus_res_p"] = p_min.reindex(out["mascon_id"]).to_numpy()
    out["reservoir_share_of_tws_trend"] = (
        (out["tws_trend_paired_mm_yr"] - out["minus_res_trend_mm_yr"])
        / out["tws_trend_paired_mm_yr"])
    for nm, a in (("tws", a_tws), ("minus_res", a_min)):
        out[f"{nm}_precipadj_trend_mm_yr"] = a["trend"].reindex(out["mascon_id"]).to_numpy()
        out[f"{nm}_precipadj_p"] = a["p"].reindex(out["mascon_id"]).to_numpy()
        out[f"{nm}_frac_unexplained_by_precip"] = (
            a["frac_unexplained"].reindex(out["mascon_id"]).to_numpy())
    out["grace_noise_2sigma_mm"] = (long[long.observed].groupby("mascon_id")["noise_2sigma_cm"]
                                    .median() * 10).reindex(out["mascon_id"]).to_numpy()
    out.to_csv(TR / "mascon_decomposition.csv", index=False)

    # --- area-weighted regional aggregates, and a Nuevo-Leon-weighted one
    w = out["area_km2"].to_numpy()
    wnl = w * np.nan_to_num(out["nl_area_frac"].to_numpy())

    def wser(df, weights, min_cover=0.90):
        """Weighted mean over the mascons available that month.

        Weights are renormalised on the available set, and a month is dropped
        entirely if less than `min_cover` of the total weight is present - so a
        month in which only the reservoir-free mascons report is not passed off
        as a regional mean.
        """
        m = df[out["mascon_id"]].to_numpy()
        ok = np.isfinite(m)
        wsum = (ok * weights).sum(axis=1)
        val = np.nansum(np.where(ok, m, 0.0) * weights, axis=1) / np.where(wsum > 0, wsum, np.nan)
        return pd.Series(np.where(wsum / weights.sum() >= min_cover, val, np.nan), index=df.index)

    reg = pd.DataFrame({
        "tws_mm": wser(tws, w), "tws_minus_res_mm": wser(minus, w),
        "reservoir_mm": wser(res, w),
        "tws_mm_nlweighted": wser(tws, wnl),
        "tws_minus_res_mm_nlweighted": wser(minus, wnl),
        "reservoir_mm_nlweighted": wser(res, wnl),
    })
    reg["tws_mm_paired"] = reg["tws_mm"].where(reg["tws_minus_res_mm"].notna())
    reg["tws_mm_nlweighted_paired"] = (reg["tws_mm_nlweighted"]
                                       .where(reg["tws_minus_res_mm_nlweighted"].notna()))
    reg.to_csv(SIG / "regional_series.csv")

    def one(s):
        s = s.dropna()
        s.index = pd.DatetimeIndex(s.index, name="time")
        da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                          coords={"time": s.index, "x": [0]})
        r = T.fit_trend(da)
        return float(r["trend"].values[0]), float(r["p_value"].values[0])

    summary = {"region_area_km2": float(w.sum()),
               "nl_weighted_area_km2": float(wnl.sum()),
               "n_mascons": len(out),
               "n_mascons_touching_nuevo_leon": int((out["nl_area_frac"] > 0.01).sum())}
    for k in reg.columns:
        t, p = one(reg[k])
        summary[f"trend_{k}_mm_yr"] = t
        summary[f"p_{k}"] = p
    summary["reservoir_share_of_regional_trend"] = (
        1 - summary["trend_tws_minus_res_mm_mm_yr"] / summary["trend_tws_mm_paired_mm_yr"])
    summary["reservoir_share_of_regional_trend_nlweighted"] = (
        1 - summary["trend_tws_minus_res_mm_nlweighted_mm_yr"]
        / summary["trend_tws_mm_nlweighted_paired_mm_yr"])
    summary["n_months_reservoir_defined_regional"] = int(reg["tws_minus_res_mm"].notna().sum())
    summary["reservoir_record_last_month"] = str(
        reg["tws_minus_res_mm_nlweighted"].last_valid_index().date())
    (TR / "decomposition_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print()
    cols = ["mascon_id", "lat_center", "lon_180", "nl_area_frac", "tws_trend_mm_yr",
            "res_trend_mm_yr", "minus_res_trend_mm_yr", "minus_res_p",
            "minus_res_frac_unexplained_by_precip"]
    print(out.sort_values("tws_trend_mm_yr")[cols].to_string(index=False))


if __name__ == "__main__":
    main()
