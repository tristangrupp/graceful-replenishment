"""Phase 3b - pull one Water Plan water-balance year and see what is inside,
and test the other candidate hosts (PRISM, DAU boundaries, groundwater levels).
"""
import io
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get, download

RAW = Path(r"E:\Water\CentralValley\raw")

WB2020 = ("https://data.cnra.ca.gov/dataset/bf4cf038-80b1-4e72-96a6-0bf37d293b9d/"
          "resource/9ca8a0d4-6b06-40f5-8864-3ab281e253bc/download/"
          "cdwr-20250403_20250409_2020-md5655808ae62b63e27a18bda2accc5dcd7.zip")

p, st = download(WB2020, RAW / "waterbalance" / "wb_2020.zip")
print("water balance 2020:", st, p)
if p:
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            print("   ", n, z.getinfo(n).file_size)

print("\n--- other hosts ---")
TESTS = [
    ("prism-monthly-ppt", "https://services.nacse.org/prism/data/public/4km/ppt/202001"),
    ("prism-normals", "https://services.nacse.org/prism/data/public/normals/4km/ppt/1"),
    ("cnra-arcgis-dau", "https://gis.data.cnra.ca.gov/api/search/v1/collections/dataset/items?q=detailed%20analysis%20unit&limit=5"),
    ("cnra-featureserver", "https://gis.water.ca.gov/arcgis/rest/services?f=json"),
]
for name, url in TESTS:
    try:
        r = get(url, tries=3, timeout=90)
        print(f"{name:20s} {r.status_code} {r.headers.get('content-type','')[:40]:40s} "
              f"{len(r.content):>10,} B")
        if "json" in r.headers.get("content-type", ""):
            print("    ", r.text[:400])
    except Exception as e:
        print(f"{name:20s} FAIL {str(e)[:150]}")
