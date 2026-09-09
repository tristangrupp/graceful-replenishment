"""Glacier cover per HydroBASINS polygon, from Natural Earth's glaciated areas.

GSFC's own ice codes cannot answer this. It marks only Greenland, Antarctica and
a short list of ice caps, so Svalbard, Novaya Zemlya, Ellesmere, Iceland and
Patagonia all come back as ordinary land. Those are exactly the basins whose
storage trend is glacier loss rather than groundwater.

Natural Earth's 10m glaciated-areas layer is public domain, generalised, and
global. Generalised is fine here: the number decides whether to show a basin in
a ranked list, not what its trend is.
"""

import glob
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

ROOT = Path(r"E:\Water\Global")
EQUAL_AREA = "+proj=cea +lat_ts=30 +datum=WGS84 +units=m +no_defs"

ice = gpd.read_file(ROOT / "raw" / "naturalearth" / "ne_10m_glaciated_areas.shp").to_crs(EQUAL_AREA)
ice = ice[ice.geometry.notna() & ~ice.geometry.is_empty]
# Natural Earth's polygons carry self-intersections that make a union throw a
# side-location conflict. A zero-width buffer repairs the rings without moving
# any boundary that matters at this scale.
ice["geometry"] = ice.geometry.buffer(0)
ice_union = ice.geometry.union_all()
print(f"glacier layer: {len(ice)} polygons, {ice.area.sum()/1e6:,.0f} km2 total")

for level in ("03", "04", "aq"):
    b = rg.load_basins(level).to_crs(EQUAL_AREA)
    b["geometry"] = b.geometry.buffer(0)
    area = b.geometry.area
    inter = b.geometry.intersection(ice_union).area
    frac = (inter / area).clip(0, 1)
    out = pd.DataFrame({"HYBAS_ID": b["HYBAS_ID"].astype("int64"),
                        "glacier_fraction": frac.round(4)})
    out.to_csv(ROOT / "trends" / f"glacier_fraction_lev{level}.csv", index=False)
    print(f"unit {level}: {len(out)} units, {(out.glacier_fraction > 0.01).sum()} above 1% ice, "
          f"{(out.glacier_fraction > 0.05).sum()} above 5%")
    top = out.sort_values("glacier_fraction", ascending=False).head(8)
    print(top.to_string(index=False))
