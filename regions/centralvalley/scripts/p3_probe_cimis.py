"""Phase 3e - inspect one Spatial CIMIS ETo yearly COG before pulling 22 of them."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import download, HDR
import requests

URL = ("https://data.cnra.ca.gov/dataset/74b3a94a-f044-4e9c-9cd2-ca6f5b7d9be1/"
       "resource/1d8b7fbe-3f22-4205-9704-afe7cfc0d9c7/download/"
       "eto_20200101-20201231_v1.tif")

r = requests.head(URL, headers=HDR, timeout=60, allow_redirects=True)
print("HEAD", r.status_code, r.headers.get("content-length"), r.headers.get("content-type"))

p, st = download(URL, Path(r"E:\Water\CentralValley\raw\cimis_eto\eto_2020.tif"))
print("download:", st, p)
if p:
    import rasterio
    print("rasterio available")
