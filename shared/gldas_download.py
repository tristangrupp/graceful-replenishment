"""Serial, resumable GLDAS subset downloader for a lat/lon box.

Pulls only the variables `depletion/attribution.py` needs, spatially subset
through GES DISC OPeNDAP, so a 24-year three-model record for one region is
tens of megabytes rather than tens of gigabytes.

Serial by design. Parallel prefetchers against GES DISC were the likely cause
of the repeated ECONNRESET deaths earlier in this project, and every month is
written to disk the moment it arrives, so an interrupted run resumes instead
of restarting.

Auth is an Earthdata Login bearer token read from a file. The token is never
printed, never logged, and never passed on a command line.
"""

import argparse
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

TOKEN_FILE = Path(os.environ.get("EARTHDATA_TOKEN_FILE", r"C:\Users\grupp\Desktop\earthdata.txt"))
BASE = "https://hydro1.gesdisc.eosdis.nasa.gov/opendap/GLDAS"

# Variables per model: exactly the non-groundwater storage terms
# attribution.py sums, plus the precipitation forcing precipitation.py wants.
MODELS = {
    "noah": {
        "collection": "GLDAS_NOAH025_M",
        "version": "2.1",
        "res": 0.25,
        "nlat": 600,
        "nlon": 1440,
        "vars": [
            "SoilMoi0_10cm_inst",
            "SoilMoi10_40cm_inst",
            "SoilMoi40_100cm_inst",
            "SoilMoi100_200cm_inst",
            "SWE_inst",
            "CanopInt_inst",
            "Rainf_f_tavg",
            "Evap_tavg",
        ],
    },
    "vic": {
        "collection": "GLDAS_VIC10_M",
        "version": "2.1",
        "res": 1.0,
        "nlat": 150,
        "nlon": 360,
        "vars": [
            "SoilMoi0_30cm_inst",
            "SoilMoi_depth2_inst",
            "SoilMoi_depth3_inst",
            "SWE_inst",
            "CanopInt_inst",
            "Rainf_f_tavg",
            "Evap_tavg",
        ],
    },
    "clsm": {
        "collection": "GLDAS_CLSM10_M",
        "version": "2.1",
        "res": 1.0,
        "nlat": 150,
        "nlon": 360,
        "vars": [
            "SoilMoist_RZ_inst",
            "SWE_inst",
            "CanopInt_inst",
            "Rainf_f_tavg",
            "Evap_tavg",
        ],
    },
}


def _token() -> str:
    if not TOKEN_FILE.exists():
        raise SystemExit(f"no Earthdata token at {TOKEN_FILE}; set EARTHDATA_TOKEN_FILE")
    tok = TOKEN_FILE.read_text(encoding="utf-8-sig").strip()
    if not tok.startswith("ey"):
        raise SystemExit(f"{TOKEN_FILE} does not look like an Earthdata JWT")
    return tok


def _index_range(lo: float, hi: float, first: float, res: float, n: int) -> tuple[int, int]:
    """Inclusive index range of a coordinate axis covering [lo, hi].

    GLDAS axes are regular cell centres starting at `first`. Padded outward by
    one cell so the box is fully covered after regridding rather than clipped
    at its edge.
    """
    i0 = int(np.floor((lo - first) / res)) - 1
    i1 = int(np.ceil((hi - first) / res)) + 1
    return max(i0, 0), min(i1, n - 1)


def _fetch(url: str, token: str, timeout: int = 180, attempts: int = 5) -> bytes:
    last = None
    for k in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + token})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit(f"HTTP {e.code} -- token rejected or GESDISC app not authorized")
            if e.code == 404:
                raise
            last = e
        except Exception as e:  # timeouts, resets
            last = e
        time.sleep(2 ** k)
    raise RuntimeError(f"gave up after {attempts} attempts: {type(last).__name__} {last}")


def download(region_dir: Path, lat_range, lon_range, models=("noah", "vic", "clsm"),
             start="2002-04", end="2026-03") -> dict:
    token = _token()
    months = pd.period_range(start, end, freq="M")
    written = {}

    for name in models:
        spec = MODELS[name]
        out = Path(region_dir) / "raw" / "gldas" / name
        out.mkdir(parents=True, exist_ok=True)
        res = spec["res"]
        lat0, lon0 = -60 + res / 2, -180 + res / 2
        iy0, iy1 = _index_range(min(lat_range), max(lat_range), lat0, res, spec["nlat"])
        ix0, ix1 = _index_range(min(lon_range), max(lon_range), lon0, res, spec["nlon"])
        con = ",".join(f"{v}[0:1:0][{iy0}:1:{iy1}][{ix0}:1:{ix1}]" for v in spec["vars"])
        con += ",time"
        print(f"[{name}] lat idx {iy0}..{iy1}  lon idx {ix0}..{ix1}  "
              f"({iy1 - iy0 + 1} x {ix1 - ix0 + 1} cells)", flush=True)

        got = skipped = 0
        for m in months:
            fn = out / f"{spec['collection']}.A{m.year}{m.month:02d}.nc4"
            if fn.exists() and fn.stat().st_size > 1024:
                skipped += 1
                continue
            url = (f"{BASE}/{spec['collection']}.{spec['version']}/{m.year}/"
                   f"{spec['collection']}.A{m.year}{m.month:02d}.021.nc4.nc4?{con}")
            try:
                blob = _fetch(url, token)
            except urllib.error.HTTPError as e:
                print(f"[{name}] {m} HTTP {e.code} -- skipped", flush=True)
                continue
            fn.write_bytes(blob)
            got += 1
            if got % 24 == 0:
                print(f"[{name}] {got} downloaded, at {m}", flush=True)
        print(f"[{name}] done: {got} new, {skipped} already on disk", flush=True)
        written[name] = out

    return written


def assemble(region_dir: Path, models=("noah", "vic", "clsm")) -> dict:
    """Concatenate the per-month subsets into one netCDF per model."""
    out_dir = Path(region_dir) / "processed"
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {}
    for name in models:
        src = sorted((Path(region_dir) / "raw" / "gldas" / name).glob("*.nc4"))
        if not src:
            continue
        # Opened one at a time and concatenated in memory: no dask in this
        # environment, and a region subset is small enough not to need it.
        parts = []
        for f in src:
            with xr.open_dataset(f, engine="netcdf4") as d:
                parts.append(d.load())
        ds = xr.concat(parts, dim="time").sortby("time")
        p = out_dir / f"gldas_{name}_monthly.nc"
        ds.to_netcdf(p)
        paths[name] = p
        print(f"[{name}] {len(src)} months -> {p} ({p.stat().st_size / 1e6:.1f} MB) "
              f"{dict(ds.sizes)}", flush=True)
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("region_dir")
    ap.add_argument("--lat", nargs=2, type=float, required=True)
    ap.add_argument("--lon", nargs=2, type=float, required=True)
    ap.add_argument("--models", nargs="+", default=["noah", "vic", "clsm"])
    ap.add_argument("--start", default="2002-04")
    ap.add_argument("--end", default="2026-03")
    a = ap.parse_args()
    download(Path(a.region_dir), a.lat, a.lon, tuple(a.models), a.start, a.end)
    assemble(Path(a.region_dir), tuple(a.models))
