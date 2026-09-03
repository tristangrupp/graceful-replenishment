"""Download DWR i15 statewide crop mapping for the Central Valley analysis.

These are the California analogue of Oregon's field boundary inventory: a
statewide polygon layer per survey year, carrying crop class and irrigation
status. DWR publishes discrete survey years rather than an annual series, so
the temporal resolution is coarser than Oregon's monthly record.
"""

import sys
import time
from pathlib import Path

import requests

DEST = Path(r"E:\Water\CentralValley\raw\crop_mapping")
BASE = "https://data.cnra.ca.gov/dataset/6c3d65e3-35bb-49e1-a51e-49d5a2cf09a9/resource"

YEARS = {
    2014: f"{BASE}/3bba74e2-a992-48db-a9ed-19e6fabb8052/download/i15_crop_mapping_2014_shp.zip",
    2016: f"{BASE}/3b57898b-f013-487a-b472-17f54311edb5/download/i15_crop_mapping_2016_shp.zip",
    2018: f"{BASE}/2dde4303-5c83-4980-a1af-4f321abefe95/download/i15_crop_mapping_2018_shp.zip",
    2019: f"{BASE}/1da7b37a-dd97-4b69-a86a-fe824a252eaf/download/i15_crop_mapping_2019.zip",
    2020: f"{BASE}/11dde2fe-dc07-4b10-b54e-ede2b4ce5fe6/download/i15_crop_mapping_2020.zip",
    2021: f"{BASE}/eebd40ab-35a3-4e62-a625-0275b2849531/download/i15_crop_mapping_2021_shp.zip",
    2022: f"{BASE}/b92e0daf-6e2e-4b5c-a112-09474138d1cd/download/i15_crop_mapping_2022_shp.zip",
    2023: f"{BASE}/25d0f174-4bec-4987-a402-602cd1372786/download/i15_crop_mapping_final_2023.zip",
}
LEGEND = (f"{BASE}/9a00d123-7d5f-46a0-8e89-b6b0591a01f0/download/"
          "2022-dwr-standard-land-use-legend-remote-sensing-version.pdf")


def fetch(url, path, tries=3):
    if path.exists() and path.stat().st_size > 10_000:
        print(f"  have {path.name} ({path.stat().st_size / 1e6:,.0f} MB)")
        return True
    for attempt in range(1, tries + 1):
        try:
            with requests.get(url, stream=True, timeout=180) as r:
                r.raise_for_status()
                tmp = path.with_suffix(path.suffix + ".part")
                got = 0
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
                        got += len(chunk)
                tmp.replace(path)
            print(f"  got {path.name} ({got / 1e6:,.0f} MB)")
            return True
        except Exception as exc:
            print(f"  attempt {attempt} failed for {path.name}: {type(exc).__name__} {exc}")
            time.sleep(5)
    return False


def main():
    DEST.mkdir(parents=True, exist_ok=True)
    ok, failed = [], []
    for year, url in sorted(YEARS.items()):
        print(f"{year}:")
        (ok if fetch(url, DEST / f"i15_crop_mapping_{year}.zip") else failed).append(year)
    fetch(LEGEND, DEST / "dwr_land_use_legend.pdf")

    print(f"\ndownloaded: {ok}")
    if failed:
        print(f"FAILED: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
