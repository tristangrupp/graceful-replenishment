import glob, sys
import geopandas as gpd, numpy as np, pandas as pd
sys.path.insert(0, r"E:\Water\_shared")
from gsfc_grid import LAND, cell_to_mascon, load_geometry

geo = load_geometry(); land = geo.location.to_numpy() == LAND
basins = pd.concat([gpd.read_file(p) for p in sorted(glob.glob(
    r"E:\Water\Global\raw\hydrobasins\*lev03*.shp"))], ignore_index=True)
basins = gpd.GeoDataFrame(basins, geometry="geometry", crs="EPSG:4326")
basins["basin_idx"] = np.arange(len(basins))

lat = np.arange(-89.95, 90, 0.1); lon = np.arange(-179.95, 180, 0.1)
mp = cell_to_mascon(geo, lat, lon); LON, LAT = np.meshgrid(lon, lat)
allpts = gpd.GeoDataFrame({"mascon_id": mp.ravel().astype("int64"),
                           "is_land": land[mp].ravel()},
                          geometry=gpd.points_from_xy(LON.ravel(), LAT.ravel()), crs="EPSG:4326")
j = gpd.sjoin(allpts, basins[["basin_idx", "geometry"]], how="inner", predicate="within")
cov = j.groupby("basin_idx")["is_land"].agg(["size", "sum"])
cov["land_frac"] = cov["sum"] / cov["size"]
b = basins.merge(cov, left_on="basin_idx", right_index=True, how="left")
no_land = b[(b["sum"].fillna(0) == 0)]
print(f"basins with no GSFC land mascon at all: {len(no_land)}")
print(f"  their total area: {no_land.SUB_AREA.sum():,.0f} km2 "
      f"({100*no_land.SUB_AREA.sum()/b.SUB_AREA.sum():.2f}% of level-3 area)")
print(f"  area: median {no_land.SUB_AREA.median():,.0f} max {no_land.SUB_AREA.max():,.0f} km2")
print(no_land.sort_values("SUB_AREA", ascending=False)[["HYBAS_ID","SUB_AREA","COAST"]].head(8).to_string(index=False))
big = b[(b["sum"].fillna(0) > 0)]
print(f"covered basins: {len(big)}, {100*big.SUB_AREA.sum()/b.SUB_AREA.sum():.2f}% of level-3 area")
