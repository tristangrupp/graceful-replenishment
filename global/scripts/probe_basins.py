import glob, os
import geopandas as gpd
tot = 0
for p in sorted(glob.glob(r"E:\Water\Global\raw\hydrobasins\*lev03*.shp")):
    g = gpd.read_file(p)
    tot += len(g)
    print(os.path.basename(p), len(g), g.crs.to_string() if g.crs else None)
print("total basins", tot)
g = gpd.read_file(r"E:\Water\Global\raw\hydrobasins\hybas_af_lev03_v1c.shp")
print(list(g.columns))
print(g[["HYBAS_ID", "SUB_AREA", "COAST"]].head(3).to_string())
