"""Phase 3m - monthly consumptive use per mascon.

DWR publishes evapotranspiration of applied water ANNUALLY, by water year.
GRACE needs months. The annual total is spread over the twelve months of its
water year with a weight built from two measured fields:

    D_m  = max(0, ETo_m - P_m)        atmospheric demand not met by rain
    w_m  = D_m / sum over the water year
    CU_m = ETAW_WY * w_m

ETo is Spatial CIMIS (2 km daily, summed to months); P is PRISM 4 km monthly;
both reduced over the same mascon footprint. THE ANNUAL TOTAL IS DWR'S AND IS
NOT ALTERED - only its distribution within the year is derived.

Two variants are produced so sensitivity to that choice is visible:
  cu_mm      year-specific weights (above)
  cu_clim_mm the same construction with 12 climatological weights, fixed
             across all years
If the two give the same deseasonalised amplitude, the disaggregation is not
driving the answer.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")


def main():
    ann = pd.read_parquet(OUT / "cu_annual_mascon.parquet")
    eto = pd.read_parquet(OUT / "cimis_eto_mascon.parquet")
    ppt = pd.read_parquet(OUT / "prism_ppt_mascon.parquet")

    eto["time"] = pd.to_datetime(eto["ym"], format="%Y%m")
    ppt["time"] = pd.to_datetime(ppt["ym"], format="%Y%m")
    print(f"ETo {eto['time'].min():%Y-%m}..{eto['time'].max():%Y-%m} "
          f"({eto['time'].nunique()} months)   "
          f"PPT {ppt['time'].min():%Y-%m}..{ppt['time'].max():%Y-%m} "
          f"({ppt['time'].nunique()} months)")

    e = eto.pivot_table(index="time", columns="mascon", values="eto_mm")
    p = ppt.pivot_table(index="time", columns="mascon", values="ppt_mm")

    idx = pd.date_range("2001-10-01", "2026-06-01", freq="MS")
    e, p = e.reindex(idx), p.reindex(idx)
    cols = sorted(set(e.columns) & set(p.columns))
    e, p = e[cols], p[cols]

    # Fill absent ETo months with that mascon's climatological month value.
    eclim = e.groupby(e.index.month).transform("mean")
    n_eto_filled = int(e.isna().sum().sum())
    e = e.fillna(eclim)
    pclim = p.groupby(p.index.month).transform("mean")
    n_ppt_filled = int(p.isna().sum().sum())
    p_w = p.fillna(pclim)          # only for the weight; the P covariate keeps its gaps

    demand = (e - p_w).clip(lower=0.0)
    demand_clim = demand.groupby(demand.index.month).transform("mean")

    wy = np.array([t.year + (t.month >= 10) for t in demand.index])

    def weights(d):
        tot = d.groupby(wy).transform("sum")
        return d.divide(tot.where(tot > 0))

    w, w_clim = weights(demand), weights(demand_clim)

    def spread(field, weight):
        wide = ann.pivot_table(index="WY", columns="mascon", values=field)
        a = wide.reindex(wy).set_axis(demand.index).reindex(columns=weight.columns)
        return a * weight

    cu, cu_clim = spread("etaw_mm", w), spread("etaw_mm", w_clim)
    aw, dp = spread("aw_mm", w), spread("dp_mm", w)

    frames = {"cu_mm": cu, "cu_clim_mm": cu_clim, "aw_mm": aw, "dp_mm": dp,
              "eto_mm": e, "ppt_mm": p}
    long = []
    for name, df in frames.items():
        s = df.stack().rename(name)
        s.index.names = ["time", "mascon"]
        long.append(s)
    pd.concat(long, axis=1).reset_index().to_parquet(
        OUT / "cu_monthly_mascon.parquet", index=False)

    # ---------------------------------------------- irrigated-core aggregate
    cov = pd.read_csv(OUT / "mascon_coverage.csv")
    geo = pd.read_csv(OUT / "mascon_geometry.csv")
    core_ids = cov[cov["irr_frac_pct"] >= 10]["mascon_id"].tolist()
    core_k = [k for k in geo.index[geo["mascon_id"].isin(core_ids)] if k in cu.columns]
    wgt = geo["area_km2"].to_numpy()[core_k]

    core = pd.DataFrame(
        {n: np.average(df[core_k].to_numpy(), axis=1, weights=wgt)
         for n, df in frames.items()}, index=cu.index)
    # P must keep its true gaps for the regression: recompute without fill
    pm = p[core_k].to_numpy()
    core["ppt_mm"] = np.where(np.isfinite(pm).all(axis=1),
                              np.average(np.nan_to_num(pm), axis=1, weights=wgt), np.nan)
    core.to_parquet(OUT / "cu_monthly_core.parquet")

    ok = core["cu_mm"].notna()
    seas = core.loc[ok, "cu_mm"].groupby(core.index[ok].month).mean()
    print("\nirrigated-core CU climatology, mm/month (Jan..Dec)")
    print("  " + "  ".join(f"{v:5.1f}" for v in seas.values))
    pseas = core.loc[ok, "ppt_mm"].groupby(core.index[ok].month).mean()
    print("irrigated-core P climatology, mm/month")
    print("  " + "  ".join(f"{v:5.1f}" for v in pseas.values))

    summary = {
        "n_eto_month_mascon_gapfilled": n_eto_filled,
        "n_ppt_month_mascon_gapfilled_for_weights": n_ppt_filled,
        "core_mascon_ids": [int(v) for v in core_ids],
        "core_area_km2": float(geo["area_km2"].to_numpy()[core_k].sum()),
        "months_with_cu": int(ok.sum()),
        "cu_time_range": [str(core.index[ok].min().date()),
                          str(core.index[ok].max().date())],
        "core_cu_mm_month_mean": float(core.loc[ok, "cu_mm"].mean()),
        "core_cu_peak_month": int(seas.idxmax()),
        "core_cu_peak_mm": float(seas.max()),
        "core_cu_min_mm": float(seas.min()),
        "core_ppt_mm_yr": float(core.loc[ok, "ppt_mm"].mean() * 12),
        "core_eto_mm_yr": float(core.loc[ok, "eto_mm"].mean() * 12),
        "corr_cu_vs_cuclim": float(core.loc[ok, ["cu_mm", "cu_clim_mm"]]
                                   .corr().iloc[0, 1]),
    }
    (INV / "cu_monthly_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
