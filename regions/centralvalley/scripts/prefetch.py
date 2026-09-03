"""Parallel prefetcher for the two bulk sources.

The Phase 3 reducers call fetch.download(), which returns immediately if the
destination already exists, so warming the cache from a separate process just
makes them faster. Started from the far end of each series so the prefetcher
and the sequential reducer do not collide on the same file.

usage:  python prefetch.py cimis 2012
        python prefetch.py prism 2014-01
"""
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from fetch import get, download

RAW = Path(r"E:\Water\CentralValley\raw")


def cimis(from_year):
    meta = get("https://data.cnra.ca.gov/api/3/action/package_show?"
               "id=cimis-spatial-eto-maps").json()["result"]
    jobs = []
    for rs in meta["resources"]:
        m = re.search(r"eto_(\d{4})\d{4}-\d{8}", rs["url"])
        if m and rs["url"].lower().endswith(".tif"):
            y = int(m.group(1))
            if y >= from_year:
                jobs.append((y, rs["url"]))
    jobs.sort(reverse=True)          # newest first, away from the reducer
    print(f"prefetching {len(jobs)} CIMIS years: {[j[0] for j in jobs]}")

    def one(job):
        y, url = job
        p, st = download(url, RAW / "cimis_eto" / f"eto_{y}.tif", tries=10)
        print(f"  cimis {y}: {st}", flush=True)

    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(one, jobs))


def prism(from_ym):
    months = [d.strftime("%Y%m") for d in
              pd.date_range(from_ym + "-01", "2026-06", freq="MS")]
    months.reverse()
    print(f"prefetching {len(months)} PRISM months from {months[-1]} to {months[0]}")

    def one(ym):
        url = f"https://services.nacse.org/prism/data/get/us/4km/ppt/{ym}"
        p, st = download(url, RAW / "prism" / f"ppt_{ym}.zip", tries=6)
        if st != "cached":
            print(f"  prism {ym}: {st}", flush=True)
        time.sleep(0.2)

    with ThreadPoolExecutor(max_workers=4) as ex:
        list(ex.map(one, months))


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "cimis":
        cimis(int(sys.argv[2]))
    else:
        prism(sys.argv[2])
