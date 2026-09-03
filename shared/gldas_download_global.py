"""Global GLDAS monthly files over plain HTTPS, resumable and serial.

The OPeNDAP host `gldas_download.py` used (hydro1.gesdisc.eosdis.nasa.gov)
started returning 410 Gone at the end of August 2026, so spatial subsetting
through DAP is no longer available. For a global product there is nothing to
subset anyway: this pulls whole granules from data.gesdisc.earthdata.nasa.gov
and lets the caller reduce them.

Serial by design, one file written to disk the moment it arrives, so an
interrupted run resumes. Auth is an Earthdata bearer token read from a file and
never placed on a command line.
"""

import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

TOKEN_FILE = Path(os.environ.get("EARTHDATA_TOKEN_FILE", r"C:\Users\grupp\Desktop\earthdata.txt"))
BASE = "https://data.gesdisc.earthdata.nasa.gov/data/GLDAS"

COLLECTIONS = {
    "noah": ("GLDAS_NOAH025_M", "2.1"),
    "vic": ("GLDAS_VIC10_M", "2.1"),
    "clsm": ("GLDAS_CLSM10_M", "2.1"),
}


def token() -> str:
    t = TOKEN_FILE.read_text(encoding="utf-8-sig").strip()
    if not t.startswith("ey"):
        raise SystemExit(f"{TOKEN_FILE} does not look like an Earthdata JWT")
    return t


def fetch(url: str, tok: str, attempts: int = 5, timeout: int = 600) -> bytes:
    last = None
    for k in range(attempts):
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                b = r.read()
            if b[:4] != b"\x89HDF":
                raise RuntimeError(f"not HDF5 (got {b[:16]!r}) -- probably an auth redirect page")
            return b
        except urllib.error.HTTPError as e:
            if e.code in (401, 403):
                raise SystemExit(f"HTTP {e.code}: token rejected or GESDISC app not authorised")
            if e.code == 404:
                raise
            last = e
        except Exception as e:
            last = e
        time.sleep(2 ** k)
    raise RuntimeError(f"gave up on {url}: {type(last).__name__} {last}")


def download(out_root: Path, start: str, end: str, models=("noah", "vic", "clsm")) -> None:
    tok = token()
    months = pd.period_range(start, end, freq="M")
    for m in models:
        coll, ver = COLLECTIONS[m]
        out = Path(out_root) / "raw" / "gldas" / m
        out.mkdir(parents=True, exist_ok=True)
        got = skipped = missing = 0
        for p in months:
            fn = out / f"{coll}.A{p.year}{p.month:02d}.nc4"
            if fn.exists() and fn.stat().st_size > 100_000:
                skipped += 1
                continue
            url = f"{BASE}/{coll}.{ver}/{p.year}/{coll}.A{p.year}{p.month:02d}.021.nc4"
            try:
                fn.write_bytes(fetch(url, tok))
            except urllib.error.HTTPError as e:
                print(f"[{m}] {p} HTTP {e.code} -- not published", flush=True)
                missing += 1
                continue
            got += 1
            if got % 12 == 0:
                print(f"[{m}] {got} downloaded, at {p}", flush=True)
        print(f"[{m}] done: {got} new, {skipped} on disk, {missing} unpublished", flush=True)


if __name__ == "__main__":
    root = Path(sys.argv[1])
    start, end = sys.argv[2], sys.argv[3]
    download(root, start, end)
