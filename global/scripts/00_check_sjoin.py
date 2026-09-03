import glob, sys, time
import geopandas as gpd, numpy as np, pandas as pd
sys.path.insert(0, r"E:\Water\_shared")
from gsfc_grid import cell_to_mascon, load_geometry, terrestrial

t0 = time.time()
geo = load_geometry(); land = terrestrial(geo)
basins = pd.concat([gpd.read_file(p) for p in sorted(glob.glob(
    r"E:\Water\Global\raw\hydrobasins\*lev03*.shp"))], ignore_index=True)
basins = gpd.GeoDataFrame(basins, geometry="geometry", crs="EPSG:4326")
basins["basin_idx"] = np.arange(len(basins))

lat = np.arange(-89.95, 90, 0.1); lon = np.arange(-179.95, 180, 0.1)
mp = cell_to_mascon(geo, lat, lon)
LON, LAT = np.meshgrid(lon, lat)
keep = land[mp]
pts = gpd.GeoDataFrame({"mascon_id": mp[keep].astype("int64"),
                        "w": np.cos(np.deg2rad(LAT[keep]))},
                       geometry=gpd.points_from_xy(LON[keep], LAT[keep]), crs="EPSG:4326")
print(f"{len(pts)} land cells; build {time.time()-t0:.1f}s")
t1 = time.time()
j = gpd.sjoin(pts, basins[["basin_idx", "geometry"]], how="inner", predicate="within")
print(f"sjoin {len(j)} matched in {time.time()-t1:.1f}s "
      f"({100*len(j)/len(pts):.1f}% of land cells inside a level-3 basin)")
per = j.groupby("basin_idx")["mascon_id"].nunique()
print(f"basins covered {per.size} of {len(basins)}; mascons per basin "
      f"min {per.min()} median {int(per.median())} max {per.max()}")
print("basins with < 5 mascons:", int((per < 5).sum()))
