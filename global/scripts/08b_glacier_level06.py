"""Glacier share for the level 6 and aquifer units, same source as 08.

The mega-region comparison needs an ice mask at level 6, which 08 does not
build because the main tabs never use that level. Natural Earth's 10m glaciated
areas are generalised, which is fine for a threshold that decides whether to
show a unit rather than what its trend is.
"""
import sys
from pathlib import Path

import geopandas as gpd
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

ROOT = Path(r"E:\Water\Global")
EQUAL_AREA = "+proj=cea +lat_ts=30 +datum=WGS84 +units=m +no_defs"

ice = gpd.read_file(ROOT / "raw" / "naturalearth" / "ne_10m_glaciated_areas.shp").to_crs(EQUAL_AREA)
ice = ice[ice.geometry.notna() & ~ice.geometry.is_empty]
ice["geometry"] = ice.geometry.buffer(0)
ice_union = ice.geometry.union_all()

for level in ("06",):
    b = rg.load_basins(level).to_crs(EQUAL_AREA)
    b["geometry"] = b.geometry.buffer(0)
    frac = (b.geometry.intersection(ice_union).area / b.geometry.area).clip(0, 1)
    out = pd.DataFrame({"HYBAS_ID": b["HYBAS_ID"].astype("int64"),
                        "glacier_fraction": frac.round(4)})
    out.to_csv(ROOT / "trends" / f"glacier_fraction_lev{level}.csv", index=False)
    print(f"unit {level}: {len(out)} units, {(out.glacier_fraction > 0.20).sum()} over one fifth ice")
