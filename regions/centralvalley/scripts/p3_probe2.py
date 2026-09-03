"""Phase 3f - three things at once, all with retries, all writing to disk:

 1. Retry the two water-balance years that failed (WY2012, WY2021).
 2. Download one Spatial CIMIS yearly ETo GeoTIFF and find out whether Pillow
    (the only raster reader in the venv) can actually open it.  There is no
    rasterio/GDAL python binding available and the venv must not be modified.
 3. Download one PRISM 4 km monthly precipitation grid and check the BIL can be
    read with numpy alone.
"""
import io
import json
import re
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get, download

RAW = Path(r"E:\Water\CentralValley\raw")

# ---------------------------------------------------------------- 1. water balance
print("=== water balance retry ===")
meta = get("https://data.cnra.ca.gov/api/3/action/package_show?"
           "id=water-plan-water-balance-data").json()["result"]
have = {int(m.group(1)) for m in
        (re.search(r"wb_(\d{4})\.zip", p.name) for p in
         (RAW / "waterbalance").glob("wb_*.zip")) if m}
print("already have:", sorted(have))
for rs in meta["resources"]:
    m = re.search(r"WY\s*(\d{4})", rs.get("name", ""), re.I)
    if not m or not rs["url"].lower().endswith(".zip"):
        continue
    wy = int(m.group(1))
    if wy in have:
        continue
    p, st = download(rs["url"], RAW / "waterbalance" / f"wb_{wy}.zip", tries=10)
    print(f"  WY{wy}: {st}")

# ---------------------------------------------------------------- 2. CIMIS ETo
print("\n=== Spatial CIMIS ETo GeoTIFF ===")
CIMIS = ("https://data.cnra.ca.gov/dataset/74b3a94a-f044-4e9c-9cd2-ca6f5b7d9be1/"
         "resource/1d8b7fbe-3f22-4205-9704-afe7cfc0d9c7/download/"
         "eto_20200101-20201231_v1.tif")
p, st = download(CIMIS, RAW / "cimis_eto" / "eto_2020.tif", tries=10)
print("download:", st, p, p.stat().st_size if p else "")
if p:
    try:
        from PIL import Image
        Image.MAX_IMAGE_PIXELS = None
        im = Image.open(p)
        print("  PIL opened:", im.size, im.mode, "n_frames=",
              getattr(im, "n_frames", "?"))
        tags = {k: v for k, v in im.tag_v2.items()}
        for k in (256, 257, 258, 259, 277, 339, 33550, 33922, 34735, 42112, 42113):
            if k in tags:
                v = tags[k]
                print(f"    tag {k}: {str(v)[:200]}")
    except Exception as e:
        print("  PIL FAILED:", type(e).__name__, str(e)[:300])

# ---------------------------------------------------------------- 3. PRISM
print("\n=== PRISM 4 km monthly ppt ===")
PR = "https://services.nacse.org/prism/data/get/us/4km/ppt/202001"
p, st = download(PR, RAW / "prism" / "ppt_202001.zip", tries=6)
print("download:", st, p, p.stat().st_size if p else "")
if p and p.stat().st_size > 1000:
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            print("   ", n, z.getinfo(n).file_size)
        hdr = [n for n in z.namelist() if n.endswith(".hdr")]
        if hdr:
            print(z.read(hdr[0]).decode("latin-1"))
