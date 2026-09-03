"""Phase 3k - reduce every PRISM and CIMIS grid ALREADY ON DISK to per-mascon
monthly series. No network access at all.

Downloads and reduction are deliberately separated: the connection has been
unstable, so the expensive local computation is done once against whatever
arrived and written straight to parquet. Missing months/years are reported,
never silently interpolated.

  PRISM  ppt_YYYYMM.zip -> prism_ppt_mascon.parquet   (mm/month areal depth)
  CIMIS  eto_YYYY.tif   -> cimis_eto_mascon.parquet   (mm/month summed from days)
"""
import io
import json
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"E:\Water\_shared")
from rasterlib import read, cell_centres
from grace_region import load_region

RAW = Path(r"E:\Water\CentralValley\raw")
OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")
LAT_RANGE, LON_RANGE = (34.8, 40.5), (-122.4, -118.6)


def box_index(mascons, lon, lat):
    idx = {}
    for k, r in mascons.iterrows():
        idx[k] = np.where((lon >= r["lon_min"]) & (lon < r["lon_max"])
                          & (lat >= r["lat_min"]) & (lat < r["lat_max"]))[0]
    return idx


# ------------------------------------------------------------------ PRISM
def do_prism(mascons):
    store = OUT / "prism_ppt_mascon.parquet"
    files = sorted((RAW / "prism").glob("ppt_*.zip"))
    done = set()
    prev = None
    if store.exists():
        prev = pd.read_parquet(store)
        done = set(prev["ym"].astype(str))
    idx = None
    rows, n_new, bad = [], 0, []
    for f in files:
        ym = f.name[4:10]
        if ym in done:
            continue
        if f.stat().st_size < 100_000:
            bad.append(ym)
            continue
        try:
            with zipfile.ZipFile(f) as z:
                names = [n for n in z.namelist() if n.endswith(".tif")]
                arr, x0, dx, y0, dy, code, nod = read(io.BytesIO(z.read(names[0])))
        except Exception as e:
            bad.append(f"{ym}:{type(e).__name__}")
            continue
        arr = np.asarray(arr, dtype="float64")
        if nod is not None:
            arr[arr == nod] = np.nan
        ny, nx = arr.shape
        if idx is None:
            xs, ys = cell_centres(x0, dx, y0, dy, nx, ny)
            XX, YY = np.meshgrid(xs, ys)
            flon, flat_ = XX.ravel(), YY.ravel()
            idx = box_index(mascons, flon, flat_)
            wts = {k: np.cos(np.radians(flat_[v])) for k, v in idx.items()}
            print(f"PRISM grid {ny}x{nx} epsg={code}; cells per mascon "
                  f"{min(len(v) for v in idx.values())}-{max(len(v) for v in idx.values())}")
        flatv = arr.ravel()
        for k, hit in idx.items():
            v, w = flatv[hit], wts[k]
            ok = np.isfinite(v)
            rows.append({"ym": ym, "mascon": k,
                         "ppt_mm": float(np.average(v[ok], weights=w[ok])) if ok.any() else np.nan})
        n_new += 1
        if n_new % 24 == 0:
            df = pd.concat([prev, pd.DataFrame(rows)]) if prev is not None else pd.DataFrame(rows)
            df.to_parquet(store, index=False)
            prev, rows = df, []
            print(f"  prism checkpoint {ym}: {len(df)} rows", flush=True)
    if rows:
        df = pd.concat([prev, pd.DataFrame(rows)]) if prev is not None else pd.DataFrame(rows)
        df.to_parquet(store, index=False)
        prev = df
    print(f"PRISM: {n_new} new months reduced, {prev['ym'].nunique()} total, bad={bad}")
    return prev, bad


# ------------------------------------------------------------------ CIMIS
def do_cimis(mascons):
    store = OUT / "cimis_eto_mascon.parquet"
    files = sorted((RAW / "cimis_eto").glob("eto_*.tif"))
    prev = pd.read_parquet(store) if store.exists() else None
    done = set(prev["year"].unique().tolist()) if prev is not None else set()
    idx = None
    for f in files:
        year = int(f.name[4:8])
        if year in done:
            continue
        try:
            arr, x0, dx, y0, dy, code, nod = read(f)
        except Exception as e:
            print(f"  cimis {year}: READ FAILED {type(e).__name__} {e}", flush=True)
            continue
        arr = np.asarray(arr, dtype="float32")
        nb, ny, nx = arr.shape
        if idx is None:
            from pyproj import Transformer
            xs = x0 + (np.arange(nx) + 0.5) * dx
            ys = y0 - (np.arange(ny) + 0.5) * dy
            XX, YY = np.meshgrid(xs, ys)
            tf = Transformer.from_crs(3310, 4326, always_xy=True)
            lon, lat = tf.transform(XX.ravel(), YY.ravel())
            idx = box_index(mascons, lon, lat)
            print(f"CIMIS grid {ny}x{nx} epsg={code} bands={nb}; cells per mascon "
                  f"{min(len(v) for v in idx.values())}-{max(len(v) for v in idx.values())}")
        flat = arr.reshape(nb, -1).astype("float64")
        flat[flat == nod] = np.nan
        days = pd.date_range(f"{year}-01-01", periods=nb, freq="D")
        keep = days.year == year
        rows = []
        for k, hit in idx.items():
            if len(hit) == 0:
                continue
            sub = flat[:, hit]
            valid = np.isfinite(sub).any(axis=1)
            daily = np.full(nb, np.nan)
            daily[valid] = np.nanmean(sub[valid], axis=1)
            s = pd.Series(daily[keep], index=days[keep])
            monthly = s.groupby(s.index.to_period("M").to_timestamp()).sum(min_count=25)
            for t, v in monthly.items():
                rows.append({"year": year, "ym": t.strftime("%Y%m"), "mascon": k,
                             "eto_mm": float(v), "n_cells": int(len(hit))})
        df = pd.DataFrame(rows)
        prev = pd.concat([prev, df]) if prev is not None else df
        prev.to_parquet(store, index=False)
        print(f"  cimis {year}: reduced ({len(df)} rows), cumulative {len(prev)}", flush=True)
    yrs = sorted(int(v) for v in prev["year"].unique()) if prev is not None else []
    print(f"CIMIS years reduced: {yrs}")
    return prev, yrs


def main():
    mascons, _, _ = load_region(LAT_RANGE, LON_RANGE)
    ppt, bad = do_prism(mascons)
    eto, yrs = do_cimis(mascons)

    want = [d.strftime("%Y%m") for d in pd.date_range("2002-01", "2026-06", freq="MS")]
    missing_p = [m for m in want if m not in set(ppt["ym"])]
    missing_e = [y for y in range(2004, 2025) if y not in yrs]
    rep = {
        "prism_months_reduced": int(ppt["ym"].nunique()),
        "prism_months_missing": missing_p,
        "prism_bad_files": bad,
        "cimis_years_reduced": yrs,
        "cimis_years_missing_2004_2024": missing_e,
    }
    (INV / "reduction_coverage.json").write_text(json.dumps(rep, indent=2))
    print("\n" + json.dumps(rep, indent=2))


if __name__ == "__main__":
    main()
