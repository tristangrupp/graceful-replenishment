"""Phase 1f - numbers needed for DATABASE_NOTES.md, all measured."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
from grace_region import load_region

OUT = Path(r"E:\Water\CentralValley\processed")
ACRE_KM2 = 0.00404686
CROP_CLASSES = {"G", "R", "F", "P", "T", "D", "C", "V"}
IRRIGABLE_AG = CROP_CLASSES | {"YP", "I", "X"}

f = pd.read_parquet(OUT / "fields_all_years.parquet")

print("=== statewide, per survey year ===")
g = f.groupby("year")
tab = pd.DataFrame({
    "polygons": g.size(),
    "acres_total": g["acres"].sum(),
    "acres_ag": f[f["cls"].isin(IRRIGABLE_AG)].groupby("year")["acres"].sum(),
    "acres_crop": f[f["cls"].isin(CROP_CLASSES)].groupby("year")["acres"].sum(),
    "acres_non_irr": f[f["irr"] == False].groupby("year")["acres"].sum(),
    "median_acres": g["acres"].median(),
})
tab["pct_non_irr_of_ag"] = 100 * tab["acres_non_irr"] / tab["acres_ag"]
print(tab.to_string(float_format=lambda v: f"{v:,.1f}"))

print("\n=== class composition statewide (acres, thousands) ===")
comp = (f.pivot_table(index="cls", columns="year", values="acres", aggfunc="sum")
        / 1000.0)
print(comp.sort_values(2023, ascending=False).to_string(float_format=lambda v: f"{v:,.0f}"))

# best mascon crop mix
mascons, _, _ = load_region((34.8, 40.5), (-122.4, -118.6))
best = mascons[mascons["mascon_id"] == 1850].iloc[0]
sel = f[(f["lon"] >= best["lon_min"]) & (f["lon"] < best["lon_max"])
        & (f["lat"] >= best["lat_min"]) & (f["lat"] < best["lat_max"])]
print(f"\n=== mascon 1850 ({best['lat_center']:.1f}N {best['lon_180']:.2f}E) crop mix, km2 ===")
mix = (sel[sel["cls"].isin(IRRIGABLE_AG)]
       .pivot_table(index="cls", columns="year", values="acres", aggfunc="sum")
       * ACRE_KM2)
print(mix.sort_values(2023, ascending=False).to_string(float_format=lambda v: f"{v:,.0f}"))

print("\n=== top crop subclasses in mascon 1850, 2023 (km2) ===")
s23 = sel[(sel["year"] == 2023) & sel["cls"].isin(CROP_CLASSES)]
print((s23.groupby("crop")["acres"].sum() * ACRE_KM2)
      .sort_values(ascending=False).head(15).to_string(float_format=lambda v: f"{v:,.1f}"))

print("\n=== 2014 vs 2016 class-code mapping check (statewide km2) ===")
chk = (f[f["year"].isin([2014, 2016])]
       .pivot_table(index="cls", columns="year", values="acres", aggfunc="sum")
       * ACRE_KM2)
print(chk.to_string(float_format=lambda v: f"{v:,.0f}"))
