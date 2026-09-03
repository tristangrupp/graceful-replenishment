"""Phase 3i - annual agricultural consumptive use per mascon, from DWR's own
California Water Plan water balances.

Source: `Water Plan Water Balance Data` (CNRA CKAN `water-plan-water-balance-data`),
one zip per water year WY2002-WY2022, table `*-DAUCO.csv`. Grain: one row per
Detailed-Analysis-Unit-by-County per water year per budget category, in TAF.
Each DAUCO row carries a representative Longitude/Latitude.

Categories used:
  AG001 Applied Water - Crop Production                 (aw)
  AG003 Evapotranspiration of Applied Water             (etaw)  <- consumptive use
  AG005 Deep Percolation of Applied Water               (dp)    <- returns to storage

AG003 is DWR's own estimate of the water consumed by irrigated agriculture and
is the direct analogue of Oregon's IRR_CU (ETa minus effective precipitation).
It is TAKEN, not derived. What IS derived here is only its distribution over
mascons (by DAUCO centroid) and, later, over months.

Deep percolation is carried through deliberately: consumptive use is not a
storage loss, because AG005 returns to the aquifer. Reporting ETAW alone would
overstate what GRACE could ever see.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
from grace_region import load_region

OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")
TAF_TO_M3 = 1233.4818e3          # 1 thousand acre-feet in m3
LAT_RANGE, LON_RANGE = (34.8, 40.5), (-122.4, -118.6)


def assign(lon, lat, mascons):
    idx = np.full(len(lon), -1, dtype=int)
    for k, r in mascons.iterrows():
        hit = ((lon >= r["lon_min"]) & (lon < r["lon_max"])
               & (lat >= r["lat_min"]) & (lat < r["lat_max"]) & (idx < 0))
        idx[hit] = k
    return idx


def main():
    mascons, _, _ = load_region(LAT_RANGE, LON_RANGE)
    wb = pd.read_parquet(OUT / "waterbalance_dauco.parquet")
    print(f"{len(wb):,} DAUCO-year rows, WY{wb['WY'].min()}-{wb['WY'].max()}, "
          f"{wb['WY'].nunique()} years, {wb['DAUCO'].nunique()} DAUCOs")
    missing = sorted(set(range(wb['WY'].min(), wb['WY'].max() + 1)) - set(wb['WY'].unique()))
    print("missing water years:", missing)

    wb["mascon"] = assign(wb["Longitude"].to_numpy(), wb["Latitude"].to_numpy(), mascons)
    inside = wb[wb["mascon"] >= 0].copy()
    print(f"{inside['DAUCO'].nunique()} DAUCOs fall inside the {len(mascons)} "
          f"Central Valley mascons")

    per = (inside.groupby(["mascon", "WY"])[["aw_taf", "etaw_taf", "dp_taf"]]
           .sum().reset_index())
    area_m2 = (mascons["area_km2"] * 1e6).reindex(per["mascon"]).to_numpy()
    for c, n in [("aw_taf", "aw_mm"), ("etaw_taf", "etaw_mm"), ("dp_taf", "dp_mm")]:
        per[n] = per[c] * TAF_TO_M3 / area_m2 * 1000.0
    per["area_km2"] = mascons["area_km2"].reindex(per["mascon"]).to_numpy()
    per.to_parquet(OUT / "cu_annual_mascon.parquet", index=False)

    # ------------------------------------------------- sanity: depth over crops
    cov = pd.read_csv(OUT / "mascon_coverage.csv").set_index("mascon_id")
    mid = mascons["mascon_id"]
    per["mascon_id"] = mid.reindex(per["mascon"]).to_numpy()
    per["irr_crop_km2"] = (cov["irr_crop_frac_pct"].reindex(per["mascon_id"]).to_numpy()
                           / 100.0 * per["area_km2"].to_numpy())
    per["etaw_over_crops_mm"] = np.where(
        per["irr_crop_km2"] > 50,
        per["etaw_taf"] * TAF_TO_M3 / (per["irr_crop_km2"] * 1e6) * 1000.0, np.nan)

    print("\n=== consumptive use over the irrigated-crop area (mm/yr) ===")
    print("Physically this must land near 500-1100 mm/yr for Central Valley crops.")
    chk = per[per["irr_crop_km2"] > 200].groupby("mascon_id")["etaw_over_crops_mm"].agg(
        ["mean", "min", "max", "count"])
    print(chk.to_string(float_format=lambda v: f"{v:,.0f}"))

    # --------------------------------------------------- valley-scale series
    core_ids = cov[cov["irr_frac_pct"] >= 10].index.tolist()
    core = per[per["mascon_id"].isin(core_ids)]
    tot = core.groupby("WY").agg(
        aw_taf=("aw_taf", "sum"), etaw_taf=("etaw_taf", "sum"),
        dp_taf=("dp_taf", "sum"), area_km2=("area_km2", "sum"))
    tot["etaw_mm"] = tot["etaw_taf"] * TAF_TO_M3 / (tot["area_km2"] * 1e6) * 1000
    tot["dp_mm"] = tot["dp_taf"] * TAF_TO_M3 / (tot["area_km2"] * 1e6) * 1000
    tot["net_mm"] = tot["etaw_mm"]     # ETAW is already net of deep percolation
    print(f"\n=== irrigated-core mascons ({len(core_ids)}), annual totals ===")
    print(tot.to_string(float_format=lambda v: f"{v:,.1f}"))

    # ---------------------------------- methodology step at the Update boundary
    early = tot.loc[tot.index <= 2011, "etaw_mm"]
    late = tot.loc[tot.index >= 2013, "etaw_mm"]
    step = float(late.mean() - early.mean())
    print(f"\nWY<=2011 mean ETAW {early.mean():,.1f} mm/yr; "
          f"WY>=2013 mean {late.mean():,.1f} mm/yr; difference {step:,.1f} mm/yr")

    summary = {
        "n_dauco_in_region": int(inside["DAUCO"].nunique()),
        "water_years": sorted(int(v) for v in wb["WY"].unique()),
        "missing_water_years": [int(v) for v in missing],
        "core_mascon_ids": [int(v) for v in core_ids],
        "core_area_km2": float(tot["area_km2"].iloc[0]),
        "core_etaw_mm_yr_mean": float(tot["etaw_mm"].mean()),
        "core_etaw_mm_yr_std": float(tot["etaw_mm"].std()),
        "core_etaw_mm_yr_min": float(tot["etaw_mm"].min()),
        "core_etaw_mm_yr_max": float(tot["etaw_mm"].max()),
        "core_aw_taf_yr_mean": float(tot["aw_taf"].mean()),
        "core_dp_mm_yr_mean": float(tot["dp_mm"].mean()),
        "etaw_over_crops_mm_yr_mean": float(chk["mean"].mean()),
        "etaw_step_2011_to_2013_mm_yr": step,
        "best_mascon_1850_etaw_mm_yr": float(
            per[per["mascon_id"] == 1850]["etaw_mm"].mean()),
        "best_mascon_1850_etaw_over_crops_mm_yr": float(
            per[per["mascon_id"] == 1850]["etaw_over_crops_mm"].mean()),
    }
    (INV / "cu_annual_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
