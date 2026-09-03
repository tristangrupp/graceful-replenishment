"""Phase 2a - reduce the eight DWR i15 survey years to a compact field table.

One row per mapped polygon per survey year:
    year, lon, lat, acres, cls, subclass, irr (bool), multiuse

Definitions established in Phase 1 and taken from the DWR FGDC metadata, not
assumed:
  * CLASS2/SUBCLASS2 hold the MAIN SEASON crop for single-cropped polygons
    (CLASS1 is blank unless the polygon is double/triple/quadruple cropped).
    SYMB_CLASS == CLASS2 in 100% of rows in every year, verified.
  * IRR_TYP2PA is the IRRIGATION STATUS of that main-season land use:
    "All fields are presumed irrigated unless an 'n' for non-irrigated has
    been applied."  IRR_TYP2PB is the irrigation *method*, not status.
  * 2014 has a completely different schema (Crop2014 text + DWR_Standa) and is
    a CALENDAR year; 2016-2023 are WATER years Oct(Y-1)..Sep(Y).

Centroids, not exact overlay: median polygon is ~30 acres (0.12 km2) against a
12,390 km2 mascon, so the assignment error is ~1e-5 of the mascon.
"""
from pathlib import Path

import numpy as np
import pandas as pd
import pyogrio
import geopandas as gpd

TMP = Path(r"E:\Water\CentralValley\tmp")
OUT = Path(r"E:\Water\CentralValley\processed")
OUT.mkdir(parents=True, exist_ok=True)

YEARS = [2014, 2016, 2018, 2019, 2020, 2021, 2022, 2023]

# 2014 DWR_Standa strings -> the standard legend class symbol.
CLS2014 = {
    "D | DECIDUOUS FRUITS AND NUTS": "D",
    "V | VINEYARD": "V",
    "T | TRUCK NURSERY AND BERRY CROPS": "T",
    "P | PASTURE": "P",
    "C | CITRUS AND SUBTROPICAL": "C",
    "I | IDLE": "I",
    "F | FIELD CROPS": "F",
    "R | RICE": "R",
    "G | GRAIN AND HAY CROPS": "G",
    "Y | YOUNG PERENNIAL": "YP",
    "U | URBAN": "U",
    "NR | RIPARIAN VEGETATION": "NR",
}


def find_shp(year):
    shps = sorted((TMP / f"cm_{year}").rglob("*.shp"))
    return max(shps, key=lambda p: p.stat().st_size)


def one_year(year):
    shp = find_shp(year)
    info = pyogrio.read_info(shp)
    fields = set(info["fields"])
    acres = "ACRES" if "ACRES" in fields else "Acres"
    if year == 2014:
        cols = [acres, "DWR_Standa", "Crop2014"]
    else:
        cols = [acres, "CLASS2", "SUBCLASS2", "IRR_TYP2PA", "MULTIUSE",
                "SYMB_CLASS" if "SYMB_CLASS" in fields else "Symb_class"]
    gdf = pyogrio.read_dataframe(shp, columns=cols, use_arrow=False)
    gdf = gdf.to_crs(4326)
    pts = gdf.geometry.representative_point()
    df = pd.DataFrame({
        "year": np.int16(year),
        "lon": pts.x.to_numpy(),
        "lat": pts.y.to_numpy(),
        "acres": gdf[acres].to_numpy(dtype="float64"),
    })
    if year == 2014:
        df["cls"] = pd.Series(gdf["DWR_Standa"].map(CLS2014)).fillna("?").to_numpy()
        df["subclass"] = ""
        df["crop"] = gdf["Crop2014"].to_numpy()
        # 2014 carries no irrigation-status field at all.
        df["irr"] = pd.NA
        df["multiuse"] = ""
    else:
        cls = pd.Series(gdf["CLASS2"].astype("string")).str.strip().fillna("")
        sub = pd.Series(gdf["SUBCLASS2"].astype("string")).str.strip().str.replace("*", "", regex=False).fillna("")
        irrp = pd.Series(gdf["IRR_TYP2PA"].astype("string")).str.strip().fillna("")
        df["cls"] = cls.to_numpy()
        df["subclass"] = sub.to_numpy()
        df["crop"] = (cls + sub).to_numpy()
        df["irr"] = (irrp != "n").to_numpy()          # 'n' == non-irrigated
        df["multiuse"] = pd.Series(gdf["MULTIUSE"].astype("string")).fillna("").to_numpy()
    return df


def main():
    parts = []
    for y in YEARS:
        d = one_year(y)
        print(f"{y}: {len(d):,} polygons, {d['acres'].sum():,.0f} acres, "
              f"lon {d['lon'].min():.2f}..{d['lon'].max():.2f} "
              f"lat {d['lat'].min():.2f}..{d['lat'].max():.2f}", flush=True)
        parts.append(d)
    all_df = pd.concat(parts, ignore_index=True)
    all_df.to_parquet(OUT / "fields_all_years.parquet", index=False)
    print("wrote", OUT / "fields_all_years.parquet", len(all_df))


if __name__ == "__main__":
    main()
