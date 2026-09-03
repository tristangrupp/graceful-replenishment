"""Phase 1: field centroids + areas -> parquet, for mascon assignment.

Fields are tiny (median ~10s of acres) compared with a 0.5-deg mascon cell
(~46 km x ~40 km at 44N, ~1900 km^2). Assigning a whole field to the mascon
containing its centroid therefore misallocates a negligible amount of area,
and avoids a 259k-polygon x mascon-grid overlay.
"""
import geopandas as gpd
import numpy as np
import pandas as pd

SHP = (r"E:\Water\Oregan\Appendix_6a_Field_and_HUC_Consumptive_Use_Geodatabase"
       r"\Oregon_Hyd_Area_Ag_Boundaries_20241016"
       r"\Oregon_Hyd_Area_Ag_Boundaries_20241016.shp")
OUT = r"E:\Water\Oregan\analysis\processed\field_centroids.parquet"

cols = ["OPENET_ID", "Acres", "HUC8", "OWRD", "srctype", "IRR_EFF"]
gdf = gpd.read_file(SHP, columns=cols, engine="pyogrio")
print("read", len(gdf), "features; crs", gdf.crs)

# Geodesic area check in an equal-area projection (Albers CONUS, EPSG:5070).
ea = gdf.geometry.to_crs(5070)
acres_calc = ea.area / 4046.8564224
cent = gdf.geometry.centroid.to_crs(4326)

out = pd.DataFrame({
    "OPENET_ID": gdf["OPENET_ID"].astype(str),
    "lon": cent.x.values,
    "lat": cent.y.values,
    "acres_attr": gdf["Acres"].values,
    "acres_calc": acres_calc.values,
    "HUC8": gdf["HUC8"].values,
    "OWRD": gdf["OWRD"].values,
    "srctype": gdf["srctype"].values,
    "IRR_EFF": gdf["IRR_EFF"].values,
})
out.to_parquet(OUT, index=False)

print("\n--- attribute vs computed acreage ---")
d = out["acres_attr"] - out["acres_calc"]
print("sum attr acres :", f"{out['acres_attr'].sum():,.0f}")
print("sum calc acres :", f"{out['acres_calc'].sum():,.0f}")
print("median abs diff:", f"{np.abs(d).median():.4f}")
print("\n--- acreage distribution (attr) ---")
print(out["acres_attr"].describe(percentiles=[.05, .25, .5, .75, .95, .99]).to_string())
print("\n--- centroid bbox (WGS84) ---")
print("lon", out.lon.min(), out.lon.max(), "lat", out.lat.min(), out.lat.max())
print("\n--- srctype value counts (NaN = no water right) ---")
print(out["srctype"].value_counts(dropna=False).to_string())
print("\n--- IRR_EFF value counts ---")
print(out["IRR_EFF"].value_counts(dropna=False).head(15).to_string())
print("\nwrote", OUT)
