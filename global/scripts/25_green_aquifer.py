"""Attach the WHYMAP aquifer unit to every well.

The wells page is a set of points, so swapping HydroSHEDS basins for aquifers
does not change its geometry the way it changes a basin map. What it changes is
the question that can be asked: does the answer depend on what kind of aquifer
the well sits in?

That is a question a catchment cannot answer. A HydroSHEDS basin is a surface
water divide and says nothing about what is underneath it. WHYMAP classifies the
subsurface, so a well can be sorted into a major groundwater basin, a complex
hydrogeological structure, or a local and shallow aquifer, and the comparison
between products can be read within each.
"""

import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

GREEN = rg.ROOT / "green"

sites = pd.read_parquet(GREEN / "well_sites.parquet")
sites["StnID"] = sites["StnID"].astype(str)
# Drop any attribution from a previous run, so re-running is idempotent rather
# than colliding with its own output in the spatial join.
sites = sites.drop(columns=[c for c in ("aq_id", "aq_group", "aq_recharge", "aq_region")
                            if c in sites.columns])
aq = rg.load_basins("aq")[["HYBAS_ID", "aq_group", "aq_recharge", "region", "geometry"]]
aq = aq.rename(columns={"HYBAS_ID": "aq_id"})

pts = gpd.GeoDataFrame(sites.copy(),
                       geometry=gpd.points_from_xy(sites.Lon, sites.Lat),
                       crs="EPSG:4326")
joined = gpd.sjoin(pts, aq, how="left", predicate="within")
# A well on a shared boundary can land in two polygons; keep the first so the
# table stays one row per well.
joined = joined[~joined.index.duplicated(keep="first")]

out = sites.copy()
for c in ("aq_id", "aq_group", "aq_recharge"):
    out[c] = joined[c].to_numpy()
out["aq_region"] = joined["region"].to_numpy()

n_hit = int(out["aq_group"].notna().sum())
print(f"{n_hit:,} of {len(out):,} wells fall inside a WHYMAP polygon "
      f"({n_hit/len(out)*100:.1f} percent)")
print(out["aq_group"].fillna("outside any polygon").value_counts().to_string())

out.to_parquet(GREEN / "well_sites.parquet")
summary = {
    "n_wells": int(len(out)),
    "n_with_aquifer": n_hit,
    "by_group": {str(k): int(v) for k, v in
                 out["aq_group"].fillna("none").value_counts().items()},
    "by_recharge": {str(k): int(v) for k, v in
                    out["aq_recharge"].fillna("none").value_counts().items()},
    "note": "wells outside any WHYMAP polygon are small coastal or island cases; "
            "they keep their other scores and are excluded from the aquifer split",
}
json.dump(summary, open(GREEN / "well_aquifer_summary.json", "w"), indent=2)
print("wrote", GREEN / "well_aquifer_summary.json")
