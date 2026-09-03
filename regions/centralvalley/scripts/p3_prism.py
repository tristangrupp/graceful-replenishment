"""Phase 3g - PRISM 4 km monthly precipitation, reduced to a per-mascon areal depth.

Source: PRISM AN81m monthly precipitation, public web service
        https://services.nacse.org/prism/data/get/us/4km/ppt/YYYYMM
        (returns a zip containing a float32 GeoTIFF, mm/month, EPSG:4269,
         0.0416667 deg, nodata -9999)

P must stay an AREAL DEPTH over the whole mascon. Oregon's run produced a
physically impossible b1(P) = +3.3 by dividing a precipitation volume over
fields by the footprint area; the fix is to never leave depth space.

Each month is downloaded, reduced, appended to disk and the raw zip kept, so an
interrupted run resumes where it stopped.
"""
import io
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"E:\Water\_shared")
from fetch import download
from rasterlib import read, cell_centres
from grace_region import load_region

RAW = Path(r"E:\Water\CentralValley\raw\prism")
OUT = Path(r"E:\Water\CentralValley\processed")
STORE = OUT / "prism_ppt_mascon.parquet"

LAT_RANGE, LON_RANGE = (34.8, 40.5), (-122.4, -118.6)
START, END = "2002-01", "2026-06"


def month_list():
    return [d.strftime("%Y%m") for d in pd.date_range(START, END, freq="MS")]


def build_index(mascons, xs, ys):
    """For each mascon, the flat indices of PRISM cells whose centre is inside,
    plus cos(lat) weights."""
    XX, YY = np.meshgrid(xs, ys)
    flat_x, flat_y = XX.ravel(), YY.ravel()
    w = np.cos(np.radians(flat_y))
    idx = {}
    for k, r in mascons.iterrows():
        hit = np.where((flat_x >= r["lon_min"]) & (flat_x < r["lon_max"])
                       & (flat_y >= r["lat_min"]) & (flat_y < r["lat_max"]))[0]
        idx[k] = (hit, w[hit])
    return idx


def main():
    mascons, _, _ = load_region(LAT_RANGE, LON_RANGE)
    months = month_list()
    done = set()
    if STORE.exists():
        prev = pd.read_parquet(STORE)
        done = set(prev["ym"].astype(str))
        print(f"resuming: {len(done)} months already reduced")
    else:
        prev = None

    idx = None
    rows = []
    for ym in months:
        if ym in done:
            continue
        url = f"https://services.nacse.org/prism/data/get/us/4km/ppt/{ym}"
        p, st = download(url, RAW / f"ppt_{ym}.zip", tries=5)
        if p is None or p.stat().st_size < 100_000:
            print(f"{ym}: {st} size={p.stat().st_size if p else 0}", flush=True)
            continue
        try:
            with zipfile.ZipFile(p) as z:
                names = [n for n in z.namelist() if n.endswith(".tif")]
                if not names:
                    print(f"{ym}: no tif in zip ({z.namelist()})", flush=True)
                    continue
                arr, x0, dx, y0, dy, code, nod = read(io.BytesIO(z.read(names[0])))
        except Exception as e:
            print(f"{ym}: READ FAILED {type(e).__name__} {e}", flush=True)
            continue
        arr = np.asarray(arr, dtype="float64")
        if nod is not None:
            arr[arr == nod] = np.nan
        ny, nx = arr.shape
        if idx is None:
            xs, ys = cell_centres(x0, dx, y0, dy, nx, ny)
            idx = build_index(mascons, xs, ys)
            print(f"PRISM grid {ny}x{nx} epsg={code} "
                  f"lon {xs[0]:.3f}..{xs[-1]:.3f} lat {ys[0]:.3f}..{ys[-1]:.3f}")
        flat = arr.ravel()
        for k, (hit, w) in idx.items():
            v = flat[hit]
            ok = np.isfinite(v)
            rows.append({"ym": ym, "mascon": k,
                         "ppt_mm": float(np.average(v[ok], weights=w[ok]))
                         if ok.any() else np.nan,
                         "cov_frac": float(ok.mean()) if len(ok) else 0.0})
        if len(rows) >= 40 * 12:
            df = pd.DataFrame(rows)
            df = pd.concat([prev, df]) if prev is not None else df
            df.to_parquet(STORE, index=False)
            prev, rows = df, []
            print(f"  checkpoint at {ym}: {len(df)} rows", flush=True)
        time.sleep(0.5)

    if rows:
        df = pd.DataFrame(rows)
        df = pd.concat([prev, df]) if prev is not None else df
        df.to_parquet(STORE, index=False)
        prev = df
    print("total rows:", 0 if prev is None else len(prev))
    if prev is not None:
        print("months:", prev["ym"].nunique())


if __name__ == "__main__":
    main()
