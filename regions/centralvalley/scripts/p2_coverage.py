"""Phase 2 - irrigated coverage of each native GSFC mascon over the Central Valley.

Mirrors E:\\Water\\Oregan\\analysis\\scripts\\p7_native_mascon_coverage.py so the
numbers are directly comparable:
  irr_frac_pct       = irrigated km2 / TOTAL mascon area km2
  all_field_frac_pct = every mapped polygon (any class) / total mascon area

Two extra columns Oregon did not need:
  land_frac_pct  - fraction of the mascon box that is land (Natural Earth 10m).
                   GSFC mascons are regular ~1 deg blocks, not coastline-clipped,
                   so a "land" mascon on the coast still contains ocean. The
                   GRACE mascon value is mass over the WHOLE mascon, so total
                   area stays the denominator for signal dilution; land fraction
                   is reported so coastal mascons can be recognised.
  cropped_frac_pct - excludes idle/fallow/unclassified classes.

Coverage is reported per survey year, and the mean over years is ranked.
"""
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import box

import sys
sys.path.insert(0, r"E:\Water\_shared")
from grace_region import load_region

OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")
NE_LAND = Path(r"C:\Users\grupp\.local\share\cartopy\shapefiles\natural_earth"
               r"\physical\ne_10m_land.shp")

ACRE_KM2 = 0.00404686
LAT_RANGE, LON_RANGE = (34.8, 40.5), (-122.4, -118.6)

# Agricultural classes that actually grow a crop. From the DWR Standard Land
# Use Legend (Section II). Excluded on purpose:
#   I  - idle          X  - unclassified fallow      YP - young perennial
#   S/U/UL/N* - semi-ag, urban, native
# YP is excluded from "cropped" but IS irrigated land, so it stays in the
# irrigated total; the two columns differ for exactly that reason.
CROP_CLASSES = {"G", "R", "F", "P", "T", "D", "C", "V"}
IRRIGABLE_AG = CROP_CLASSES | {"YP", "I", "X"}   # ag land with irrigation plumbing


def assign(lon, lat, mascons):
    idx = np.full(len(lon), -1, dtype=int)
    for k, r in mascons.iterrows():
        hit = ((lon >= r["lon_min"]) & (lon < r["lon_max"])
               & (lat >= r["lat_min"]) & (lat < r["lat_max"]) & (idx < 0))
        idx[hit] = k
    return idx


def land_fraction(mascons):
    land = gpd.read_file(NE_LAND)
    land = land[land.geometry.intersects(box(-126, 32, -114, 43))]
    merged = land.union_all()
    fracs = []
    for _, r in mascons.iterrows():
        b = box(r["lon_min"], r["lat_min"], r["lon_max"], r["lat_max"])
        fracs.append(b.intersection(merged).area / b.area)
    return np.array(fracs)


def main():
    mascons, _, _ = load_region(LAT_RANGE, LON_RANGE)
    print(f"{len(mascons)} land mascons; area "
          f"{mascons['area_km2'].min():,.0f}-{mascons['area_km2'].max():,.0f} km2")

    mascons["land_frac"] = land_fraction(mascons)

    f = pd.read_parquet(OUT / "fields_all_years.parquet")
    f["mascon"] = assign(f["lon"].to_numpy(), f["lat"].to_numpy(), mascons)
    f = f[f["mascon"] >= 0].copy()
    print(f"{len(f):,} of the field-year records fall inside a Central Valley mascon")

    f["km2"] = f["acres"] * ACRE_KM2
    # 2014 has no irrigation-status field. Treat 2014 'irr' as unknown and
    # report it separately rather than guessing.
    f["is_crop"] = f["cls"].isin(CROP_CLASSES)
    f["is_ag"] = f["cls"].isin(IRRIGABLE_AG)
    f["irr_known"] = f["irr"].notna()
    f["is_irr"] = f["irr"].fillna(True).astype(bool) & f["is_ag"]

    per_year = (f.groupby(["mascon", "year"])
                .agg(all_field_km2=("km2", "sum"),
                     ag_km2=("km2", lambda s: np.nan),  # placeholder, filled below
                     )
                .drop(columns="ag_km2"))
    g = f.groupby(["mascon", "year"])
    per_year["ag_km2"] = g.apply(lambda d: d.loc[d["is_ag"], "km2"].sum(),
                                 include_groups=False)
    per_year["crop_km2"] = g.apply(lambda d: d.loc[d["is_crop"], "km2"].sum(),
                                   include_groups=False)
    per_year["irr_km2"] = g.apply(lambda d: d.loc[d["is_irr"], "km2"].sum(),
                                  include_groups=False)
    per_year["irr_crop_km2"] = g.apply(
        lambda d: d.loc[d["is_irr"] & d["is_crop"], "km2"].sum(), include_groups=False)
    per_year = per_year.reset_index()

    area = mascons["area_km2"]
    per_year["mascon_km2"] = area.reindex(per_year["mascon"]).to_numpy()
    for c in ["all_field", "ag", "crop", "irr", "irr_crop"]:
        per_year[c + "_frac_pct"] = 100 * per_year[c + "_km2"] / per_year["mascon_km2"]
    per_year.to_csv(OUT / "mascon_coverage_by_year.csv", index=False)

    # Mean over the 7 years that carry irrigation status (2016-2023).
    wy = per_year[per_year["year"] >= 2016]
    agg = wy.groupby("mascon").agg(
        irr_km2=("irr_km2", "mean"), irr_frac_pct=("irr_frac_pct", "mean"),
        irr_crop_frac_pct=("irr_crop_frac_pct", "mean"),
        crop_frac_pct=("crop_frac_pct", "mean"),
        all_field_frac_pct=("all_field_frac_pct", "mean"),
        irr_frac_min=("irr_frac_pct", "min"), irr_frac_max=("irr_frac_pct", "max"))
    cov = mascons.join(agg).fillna({"irr_km2": 0, "irr_frac_pct": 0,
                                    "crop_frac_pct": 0, "all_field_frac_pct": 0,
                                    "irr_crop_frac_pct": 0})
    cov["land_frac_pct"] = 100 * cov["land_frac"]
    cov["irr_frac_of_land_pct"] = np.where(
        cov["land_frac"] > 0.02, cov["irr_frac_pct"] / cov["land_frac"], np.nan)
    cov = cov.sort_values("irr_frac_pct", ascending=False)

    cols = ["mascon_id", "lat_center", "lon_180", "area_km2", "land_frac_pct",
            "irr_km2", "irr_frac_pct", "irr_frac_of_land_pct", "irr_crop_frac_pct",
            "crop_frac_pct", "all_field_frac_pct", "irr_frac_min", "irr_frac_max"]
    cov[cols].to_csv(OUT / "mascon_coverage.csv", index=False)

    print("\nTop 12 Central Valley mascons by irrigated fraction of mascon area")
    print(cov[cols].head(12).to_string(index=False,
                                       float_format=lambda v: f"{v:,.2f}"))

    summary = {
        "n_mascons": int(len(cov)),
        "mascon_area_km2_median": float(cov["area_km2"].median()),
        "max_irr_frac_pct": float(cov["irr_frac_pct"].max()),
        "max_all_field_frac_pct": float(cov["all_field_frac_pct"].max()),
        "median_irr_frac_pct": float(cov["irr_frac_pct"].median()),
        "total_irrigated_km2_mean_2016_2023": float(cov["irr_km2"].sum()),
        "oregon_best_irr_frac_pct": 14.5,
        "oregon_best_all_field_frac_pct": 42.6,
        "ratio_to_oregon": float(cov["irr_frac_pct"].max() / 14.5),
    }
    (OUT / "mascon_coverage_summary.json").write_text(json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
