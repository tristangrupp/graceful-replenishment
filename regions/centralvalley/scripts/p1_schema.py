"""Phase 1 - enumerate DWR i15 crop-mapping layers, fields, CRS and value domains.

Reads only the .dbf/.prj header plus a bounded sample of attributes; never loads
geometry, so it is cheap. Everything printed is measured from the files.
"""
import json
import sys
from pathlib import Path

import pyogrio
import pandas as pd

TMP = Path(r"E:\Water\CentralValley\tmp")
OUT = Path(r"E:\Water\CentralValley\inventory")
OUT.mkdir(parents=True, exist_ok=True)

YEARS = [2014, 2016, 2018, 2019, 2020, 2021, 2022, 2023]


def find_shp(year):
    d = TMP / f"cm_{year}"
    shps = sorted(d.rglob("*.shp"))
    if not shps:
        return None
    return max(shps, key=lambda p: p.stat().st_size)


def main():
    report = {}
    for y in YEARS:
        shp = find_shp(y)
        if shp is None:
            print(f"{y}: NOT EXTRACTED YET", flush=True)
            continue
        layers = pyogrio.list_layers(shp)
        info = pyogrio.read_info(shp)
        prj = shp.with_suffix(".prj")
        crs_wkt = prj.read_text().strip() if prj.exists() else "(no .prj)"
        rec = {
            "path": str(shp),
            "layers": [list(map(str, r)) for r in layers],
            "n_features": int(info["features"]),
            "geometry_type": str(info["geometry_type"]),
            "crs": str(info.get("crs")),
            "prj_head": crs_wkt[:160],
            "fields": dict(zip(info["fields"].tolist(),
                               [str(d) for d in info["dtypes"]])),
            "total_bounds": [float(v) for v in info["total_bounds"]],
        }
        report[y] = rec
        print(f"=== {y} === n={rec['n_features']:,} crs={rec['crs']} "
              f"geom={rec['geometry_type']}", flush=True)
        print("  fields:", ", ".join(f"{k}:{v}" for k, v in rec["fields"].items()),
              flush=True)
    (OUT / "schema_raw.json").write_text(json.dumps(report, indent=2))
    print("\nwrote", OUT / "schema_raw.json")


if __name__ == "__main__":
    main()
