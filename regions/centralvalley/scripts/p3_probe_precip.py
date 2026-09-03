"""Phase 3c - find a reachable gridded monthly precipitation source and test
whether OpenET can be used at all without an API key."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get

import requests
from fetch import HDR

print("--- PRISM web service response body ---")
for url in ["https://services.nacse.org/prism/data/public/4km/ppt/202001",
            "https://services.nacse.org/prism/data/get/us/800m/ppt/20200101"]:
    try:
        r = get(url, tries=2, timeout=60)
        print(url, r.status_code, repr(r.text[:400]))
    except Exception as e:
        print(url, "FAIL", str(e)[:150])

print("\n--- NOAA PSL / other gridded precip ---")
TESTS = [
    ("psl-cpc-us", "https://downloads.psl.noaa.gov/Datasets/cpc_us_precip/precip.V1.0.2020.nc"),
    ("psl-catalog", "https://psl.noaa.gov/thredds/catalog/Datasets/cpc_global_precip/catalog.xml"),
    ("psl-gpcc", "https://downloads.psl.noaa.gov/Datasets/gpcc/full_v2020/precip.mon.total.2.5x2.5.v2020.nc"),
    ("chirps", "https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/netcdf/"),
    ("noaa-nclimgrid", "https://www.ncei.noaa.gov/thredds/fileServer/nclimgrid-monthly/nclimgrid_prcp.nc"),
]
for name, url in TESTS:
    try:
        r = requests.head(url, headers=HDR, timeout=60, allow_redirects=True)
        print(f"{name:16s} HEAD {r.status_code} {r.headers.get('content-type','')[:35]:35s} "
              f"len={r.headers.get('content-length','?')}")
    except Exception as e:
        print(f"{name:16s} FAIL {type(e).__name__} {str(e)[:110]}")

print("\n--- OpenET without a key ---")
try:
    r = requests.post("https://openet-api.org/raster/timeseries/point",
                      json={"date_range": ["2020-01-01", "2020-12-31"],
                            "interval": "monthly",
                            "geometry": [-119.5, 36.2],
                            "model": "Ensemble", "variable": "ET",
                            "reference_et": "gridMET", "units": "mm",
                            "file_format": "JSON"},
                      headers=HDR, timeout=90)
    print("openet POST", r.status_code, r.text[:300])
except Exception as e:
    print("openet POST FAIL", str(e)[:200])
