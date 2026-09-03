"""Phase 3h - Spatial CIMIS daily reference ET (ETo), reduced to monthly per-mascon means.

Source: DWR / CIMIS "Spatial CIMIS ETo maps - Daily Reference Evapotranspiration
for California", one cloud-optimised GeoTIFF per calendar year, 366 daily bands,
2 km grid, EPSG:3310 (NAD83 / California Albers), mm/day, nodata -9999.
Resource URLs come from the CNRA CKAN package, not guessed.

ETo is used ONLY as the measured monthly weighting that spreads DWR's annual
evapotranspiration-of-applied-water over the months of each water year. It is
not itself consumptive use.
"""
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"E:\Water\_shared")
from fetch import get, download
from rasterlib import read
from grace_region import load_region

RAW = Path(r"E:\Water\CentralValley\raw\cimis_eto")
OUT = Path(r"E:\Water\CentralValley\processed")
STORE = OUT / "cimis_eto_mascon.parquet"
PKG = "https://data.cnra.ca.gov/api/3/action/package_show?id=cimis-spatial-eto-maps"

LAT_RANGE, LON_RANGE = (34.8, 40.5), (-122.4, -118.6)


def resources():
    meta = get(PKG).json()["result"]
    out = {}
    for rs in meta["resources"]:
        m = re.search(r"eto_(\d{4})\d{4}-\d{8}", rs["url"])
        if m and rs["url"].lower().endswith(".tif"):
            out[int(m.group(1))] = rs["url"]
    return dict(sorted(out.items()))


def grid_lonlat(nx, ny, x0, dx, y0, dy):
    """Cell-centre lon/lat for an EPSG:3310 grid."""
    from pyproj import Transformer
    xs = x0 + (np.arange(nx) + 0.5) * dx
    ys = y0 - (np.arange(ny) + 0.5) * dy
    XX, YY = np.meshgrid(xs, ys)
    tf = Transformer.from_crs(3310, 4326, always_xy=True)
    lon, lat = tf.transform(XX.ravel(), YY.ravel())
    return lon, lat


def main():
    mascons, _, _ = load_region(LAT_RANGE, LON_RANGE)
    urls = resources()
    print("CIMIS years available:", list(urls))

    done = set()
    prev = None
    if STORE.exists():
        prev = pd.read_parquet(STORE)
        done = set(prev["year"].unique().tolist())
        print("already reduced:", sorted(done))

    idx = None
    for year, url in urls.items():
        if year in done:
            continue
        dest = RAW / f"eto_{year}.tif"
        p, st = download(url, dest, tries=8)
        if p is None:
            print(f"{year}: {st}", flush=True)
            continue
        try:
            arr, x0, dx, y0, dy, code, nod = read(p)
        except Exception as e:
            print(f"{year}: READ FAILED {type(e).__name__} {e}", flush=True)
            continue
        arr = np.asarray(arr, dtype="float32")
        if arr.ndim != 3:
            print(f"{year}: unexpected shape {arr.shape}", flush=True)
            continue
        nb, ny, nx = arr.shape
        if idx is None:
            lon, lat = grid_lonlat(nx, ny, x0, dx, y0, dy)
            idx = {}
            for k, r in mascons.iterrows():
                hit = np.where((lon >= r["lon_min"]) & (lon < r["lon_max"])
                               & (lat >= r["lat_min"]) & (lat < r["lat_max"]))[0]
                idx[k] = hit
            print(f"CIMIS grid {ny}x{nx} epsg={code} bands={nb}; "
                  f"cells per mascon: "
                  f"{min(len(v) for v in idx.values())}-{max(len(v) for v in idx.values())}")
        flat = arr.reshape(nb, -1).astype("float64")
        flat[flat == nod] = np.nan
        days = pd.date_range(f"{year}-01-01", periods=nb, freq="D")
        # band count is 365/366; trailing band on non-leap years is padding
        keep = days.year == year
        rows = []
        for k, hit in idx.items():
            if len(hit) == 0:
                continue
            sub = flat[:, hit]
            daily = np.nanmean(sub, axis=1)
            s = pd.Series(daily[keep], index=days[keep])
            monthly = s.groupby(s.index.to_period("M").to_timestamp()).sum(min_count=25)
            ndays = s.groupby(s.index.to_period("M").to_timestamp()).count()
            for t, v in monthly.items():
                rows.append({"year": year, "ym": t.strftime("%Y%m"), "mascon": k,
                             "eto_mm": float(v), "n_days": int(ndays[t]),
                             "n_cells": int(len(hit))})
        df = pd.DataFrame(rows)
        prev = pd.concat([prev, df]) if prev is not None else df
        prev.to_parquet(STORE, index=False)
        print(f"{year}: reduced, cumulative rows {len(prev)}", flush=True)

    if prev is not None:
        print("years:", sorted(prev['year'].unique()))


if __name__ == "__main__":
    main()
