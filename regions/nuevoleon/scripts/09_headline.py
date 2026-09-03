"""The Nuevo Leon headline, in both solutions, with and without reservoirs.

Weights every mascon by (its area) x (its area fraction inside the Nuevo Leon
state polygon), so the number describes the state rather than the processing
box - the box is dominated by Texas and Coahuila mascons whose behaviour is
different and, in the Texas case, not reproduced by CSR.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd
import sys
import xarray as xr

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import precipitation as P  # noqa: E402
from dark_water.depletion_watchlist.depletion import trend as T  # noqa: E402

ROOT = Path(r"E:\Water\NuevoLeon")
SIG, TR = ROOT / "signals", ROOT / "trends"
DROUGHT = ("2022-07-01", "2023-04-30")
PRE = ("2015-01-01", "2019-12-31")


def tfit(s):
    s = s.dropna()
    s.index = pd.DatetimeIndex(s.index, name="time")
    da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                      coords={"time": s.index, "x": [0]})
    r = T.fit_trend(da)
    return float(r["trend"].values[0]), float(r["p_value"].values[0])


def main():
    g = pd.read_csv(TR / "post2020_gradient.csv")
    ids = list(g["mascon_id"])
    tws = pd.read_parquet(SIG / "tws_mm.parquet"); tws.columns = [int(c) for c in tws.columns]
    csr = pd.read_parquet(SIG / "csr_tws_mm.parquet"); csr.columns = [int(c) for c in csr.columns]
    res = pd.read_parquet(SIG / "reservoir_anomaly_mm.parquet")
    res.columns = [int(c) for c in res.columns]
    res = res.reindex(columns=ids)
    has_dam = res.notna().any()
    res.loc[:, ~has_dam] = 0.0
    res_g = res.reindex(index=tws.index)
    res_c = res.reindex(index=csr.index)
    cum = pd.read_parquet(SIG / "chirps_cumulative_anomaly_cm.parquet")
    cum.columns = [int(c) for c in cum.columns]

    w = g["area_km2"].to_numpy() * np.nan_to_num(g["nl_area_frac"].to_numpy())

    def wm(df, min_cover=0.90):
        m = df[ids].to_numpy()
        ok = np.isfinite(m)
        ws = (ok * w).sum(axis=1)
        val = np.nansum(np.where(ok, m, 0.0) * w, axis=1) / np.where(ws > 0, ws, np.nan)
        return pd.Series(np.where(ws / w.sum() >= min_cover, val, np.nan), index=df.index)

    ser = pd.DataFrame({
        "gsfc_tws": wm(tws), "gsfc_minus_res": wm(tws - res_g),
        "reservoir": wm(res_g.where((tws - res_g).notna())),
        "chirps_cum_cm": wm(cum.reindex(tws.index)),
    })
    ser_csr = pd.DataFrame({"csr_tws": wm(csr), "csr_minus_res": wm(csr - res_c)})
    ser = ser.join(ser_csr, how="outer")
    # the unadjusted series restricted to the months the adjusted one has, so the
    # two trends are never fitted over different records
    ser["gsfc_tws_paired"] = ser["gsfc_tws"].where(ser["gsfc_minus_res"].notna())
    ser["csr_tws_paired"] = ser["csr_tws"].where(ser["csr_minus_res"].notna())
    ser.to_csv(SIG / "nuevo_leon_series.csv")

    out = {"weighting": "mascon area x fraction inside Nuevo Leon state polygon",
           "effective_area_km2": float(w.sum()),
           "n_mascons_contributing": int((w > 0).sum()),
           "n_mascons_frac_gt_0p2": int((g["nl_area_frac"] > 0.2).sum()),
           "n_months_gsfc": int(ser["gsfc_tws"].notna().sum()),
           "n_months_gsfc_paired": int(ser["gsfc_tws_paired"].notna().sum()),
           "reservoir_record_last_month": str(ser["gsfc_minus_res"].last_valid_index().date())}
    for k in ["gsfc_tws", "gsfc_tws_paired", "gsfc_minus_res", "reservoir",
              "csr_tws", "csr_tws_paired", "csr_minus_res"]:
        t, p = tfit(ser[k])
        out[f"trend_{k}_mm_yr"] = t
        out[f"p_{k}"] = p
    out["reservoir_share_of_gsfc_trend"] = (
        1 - out["trend_gsfc_minus_res_mm_yr"] / out["trend_gsfc_tws_paired_mm_yr"])
    out["reservoir_share_of_csr_trend"] = (
        1 - out["trend_csr_minus_res_mm_yr"] / out["trend_csr_tws_paired_mm_yr"])

    # precipitation control on the Nuevo Leon aggregate
    for k in ["gsfc_tws", "gsfc_tws_paired", "gsfc_minus_res", "csr_tws",
              "csr_tws_paired", "csr_minus_res"]:
        s = ser[[k, "chirps_cum_cm"]].dropna()
        y = xr.DataArray(s[k].to_numpy()[:, None], dims=("time", "m"),
                         coords={"time": pd.DatetimeIndex(s.index, name="time"), "m": [0]})
        c = xr.DataArray(s["chirps_cum_cm"].to_numpy()[:, None], dims=("time", "m"),
                         coords={"time": pd.DatetimeIndex(s.index, name="time"), "m": [0]})
        a = P.adjusted_trend(y, c, dim="time")
        out[f"precipadj_trend_{k}_mm_yr"] = float(a["trend"].values[0])
        out[f"precipadj_p_{k}"] = float(a["p_value"].values[0])
        out[f"frac_unexplained_by_precip_{k}"] = float(a["fraction_unexplained"].values[0])

    # drought-window response, against the 2015-2019 reference level
    for k in ["gsfc_tws", "gsfc_minus_res", "reservoir", "csr_tws", "csr_minus_res"]:
        d = ser[k].loc[DROUGHT[0]:DROUGHT[1]].mean()
        pre = ser[k].loc[PRE[0]:PRE[1]].mean()
        out[f"drought_drawdown_{k}_mm"] = float(d - pre)
    out["drought_window"] = list(DROUGHT)
    out["drought_reference_window"] = list(PRE)
    out["gsfc_minimum_month"] = str(ser["gsfc_tws"].idxmin().date())
    out["gsfc_minimum_mm"] = float(ser["gsfc_tws"].min())
    out["gsfc_minus_res_minimum_month"] = str(ser["gsfc_minus_res"].idxmin().date())
    out["gsfc_minus_res_minimum_mm"] = float(ser["gsfc_minus_res"].min())
    out["csr_minimum_month"] = str(ser["csr_tws"].idxmin().date())
    out["csr_minimum_mm"] = float(ser["csr_tws"].min())

    # GSFC's own regional uncertainty formula, as used in the Saudi run
    lk = g["leakage_2sigma_cm"].to_numpy() * 10
    ltr = g["leakage_trend_cm_yr"].to_numpy() * 10
    nz = g["grace_noise_2sigma_mm"].to_numpy()
    ww = w / w.sum()
    out["nl_weighted_leakage_trend_mm_yr"] = float(np.nansum(np.abs(ltr) * ww))
    out["nl_weighted_leakage_2sigma_mm"] = float(np.nansum(lk * ww))
    out["nl_weighted_noise_2sigma_mm"] = float(np.nansum(nz * ww))

    (TR / "nuevo_leon_headline.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
