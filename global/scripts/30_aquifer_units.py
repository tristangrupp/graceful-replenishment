"""Build the aquifer unit of analysis from WHYMAP, as an alternative to basins.

A HydroSHEDS basin is a surface water catchment. Groundwater does not respect
one: an aquifer can underlie several catchments and a catchment can sit over
several aquifers. WHYMAP's Groundwater Resources map is the standard global
alternative, so this turns it into a unit the rest of the pipeline can use in
place of a basin level.

What the polygons are, and are not. WHYMAP classifies land into hydrogeological
environments at 1:25,000,000, not into named aquifer systems. A polygon is a
patch of one class, so it is a region of similar groundwater behaviour rather
than a bounded reservoir with a name. That is still a hydrogeologically
meaningful unit, and the class travels with every polygon so results can be read
by aquifer type, which no basin level can do. It is not a substitute for a
named-aquifer inventory.

Ice sheets, class 88, are dropped. They are in the file because the map covers
the whole land surface, and they are not aquifers.
"""

import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

SRC = (rg.RAW / "whymap" / "gwr" / "WHYMAP_GWR" / "shp"
       / "whymap_GW_aquifers_v1_poly.shp")
OUT = rg.RAW / "whymap" / "aquifer_units.gpkg"
EQUAL_AREA = "+proj=cea +lat_ts=30 +datum=WGS84 +units=m +no_defs"

# WHYMAP's own legend, from metadata_WHYMAP_GWR_v1.0.pdf. The first digit is the
# hydrogeological environment, the second is groundwater recharge in mm a-1.
CLASS = {
    15: ("Major groundwater basin", "very high, over 300"),
    14: ("Major groundwater basin", "high, 100 to 300"),
    13: ("Major groundwater basin", "medium, 20 to 100"),
    12: ("Major groundwater basin", "low, 2 to 20"),
    11: ("Major groundwater basin", "very low, under 2"),
    25: ("Complex hydrogeological structure", "very high, over 300"),
    24: ("Complex hydrogeological structure", "high, 100 to 300"),
    23: ("Complex hydrogeological structure", "medium, 20 to 100"),
    22: ("Complex hydrogeological structure", "low to very low, under 20"),
    34: ("Local and shallow aquifer", "very high to high, over 100"),
    33: ("Local and shallow aquifer", "medium to very low, under 100"),
}
ICE_CLASSES = (88, 89)
# WHYMAP's metadata names the CONTINENT field but never gives its legend, so
# these were read off the geometry rather than guessed. The first version of
# this file assumed the codes ran alphabetically and got five of six wrong,
# which is why the check below runs on every build: each code has to sit inside
# the box its name implies, or the build stops.
CONTINENT = {1: "North America", 2: "South America", 3: "Europe",
             4: "Africa", 5: "Asia", 6: "Australia and Oceania",
             99: "unassigned"}
# lon_min, lon_max, lat_min, lat_max that each code's polygon centres must sit
# inside. Deliberately loose: this catches a relabelling, not a stray island.
CONTINENT_BOX = {
    1: (-180, -50, 5, 85),      # North America, down to the Caribbean
    2: (-95, -30, -60, 25),     # South America
    3: (-35, 70, 33, 85),       # Europe, east to the Urals
    4: (-30, 65, -40, 40),      # Africa and the Arabian side of the Red Sea
    5: (-180, 180, -15, 85),    # Asia, which crosses the dateline in Chukotka
    6: (110, 180, -60, -5),     # Australia and Oceania
}

g = gpd.read_file(SRC)
g["HYGEO2"] = pd.to_numeric(g["HYGEO2"], errors="coerce").astype("Int64")
g["CONTINENT"] = pd.to_numeric(g["CONTINENT"], errors="coerce").astype("Int64")
print(f"{len(g)} WHYMAP polygons")

ice = g["HYGEO2"].isin(ICE_CLASSES)
print(f"dropping {int(ice.sum())} ice sheet polygons, "
      f"{g.loc[ice].to_crs(EQUAL_AREA).area.sum()/1e12:.1f} million km2")
g = g[~ice].copy()

unknown = ~g["HYGEO2"].isin(list(CLASS))
if unknown.any():
    raise SystemExit(f"unmapped HYGEO2 codes: {sorted(g.loc[unknown,'HYGEO2'].unique())}")

# Geometry from a 1:25M map has self-intersections in places; buffer(0) repairs
# them without moving anything a reader would notice at this scale.
g["geometry"] = g.geometry.buffer(0)
g = g[~g.geometry.is_empty & g.geometry.notna()].copy()

g = g.reset_index(drop=True)
g["HYBAS_ID"] = np.arange(1, len(g) + 1, dtype="int64")
g["SUB_AREA"] = g.to_crs(EQUAL_AREA).area.to_numpy() / 1e6
g["aq_group"] = [CLASS[int(c)][0] for c in g["HYGEO2"]]
g["aq_recharge"] = [CLASS[int(c)][1] for c in g["HYGEO2"]]
g["region"] = [CONTINENT.get(int(c) if pd.notna(c) else 99, "unassigned")
               for c in g["CONTINENT"]]
# Verify the continent legend against the geometry rather than trusting it.
pt = g.geometry.representative_point()
g["_lon"], g["_lat"] = pt.x.to_numpy(), pt.y.to_numpy()
for code, (lo, hi, la, lb) in CONTINENT_BOX.items():
    sub = g[g["CONTINENT"] == code]
    if not len(sub):
        continue
    bad = ~(sub["_lon"].between(lo, hi) & sub["_lat"].between(la, lb))
    share = float(bad.mean())
    if share > 0.05:
        raise SystemExit(
            f"CONTINENT code {code} is labelled {CONTINENT[code]!r} but "
            f"{share*100:.0f} percent of its polygons fall outside that region "
            f"(lon {sub['_lon'].min():.0f}..{sub['_lon'].max():.0f}, "
            f"lat {sub['_lat'].min():.0f}..{sub['_lat'].max():.0f}). "
            "The legend is wrong; read it off the geometry again.")
    print(f"  code {code} = {CONTINENT[code]}: {len(sub)} polygons, "
          f"{share*100:.1f} percent outside the expected box")
g = g.drop(columns=["_lon", "_lat"])

g = g[["HYBAS_ID", "HYGEO2", "aq_group", "aq_recharge", "region", "SUB_AREA",
       "geometry"]]

OUT.parent.mkdir(parents=True, exist_ok=True)
g.to_file(OUT, driver="GPKG", layer="aquifer_units")

by_group = (g.groupby("aq_group")
            .agg(polygons=("HYBAS_ID", "size"),
                 area_Mkm2=("SUB_AREA", lambda x: x.sum() / 1e6),
                 median_km2=("SUB_AREA", "median"))
            .sort_values("area_Mkm2", ascending=False))
print(by_group.to_string())

area = g["SUB_AREA"].to_numpy()
summary = {
    "source": "WHYMAP Groundwater Resources of the World, v1, BGR and UNESCO",
    "url": "https://www.whymap.org/whymap/EN/Maps_Data/Gwr/gwr_node_en.html",
    "file": "WHYMAP_GWR_v1.zip, whymap_GW_aquifers_v1_poly.shp",
    "scale": "1:25,000,000",
    "n_units": int(len(g)),
    "total_area_km2": float(area.sum()),
    "area_km2": {str(q): float(np.percentile(area, q)) for q in (5, 25, 50, 75, 95)},
    "n_over_reliable_63000": int((area >= 63000).sum()),
    "n_under_1000": int((area < 1000).sum()),
    "by_group": {k: {"polygons": int(v.polygons), "area_km2": float(v.area_Mkm2 * 1e6),
                     "median_km2": float(v.median_km2)}
                 for k, v in by_group.iterrows()},
    "classes": {str(k): {"group": v[0], "recharge_mm_yr": v[1]} for k, v in CLASS.items()},
    "note": "ice sheet classes 88 and 89 dropped; they are not aquifers",
}
json.dump(summary, open(rg.RAW / "whymap" / "aquifer_units_summary.json", "w"), indent=2)
print(json.dumps({k: v for k, v in summary.items() if k not in ("by_group", "classes")},
                 indent=2))
print("wrote", OUT)
