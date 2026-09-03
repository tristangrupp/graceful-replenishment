"""Phase 3a - query the CNRA CKAN catalogue for the datasets that could supply
consumptive use, reference ET, precipitation and groundwater ground-truth.

Prints package titles and every resource URL so nothing has to be guessed.
"""
import json
import sys
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
API = "https://data.cnra.ca.gov/api/3/action/package_search"

QUERIES = sys.argv[1:] or [
    "spatial CIMIS reference evapotranspiration",
    "water plan water portfolio applied water",
    "consumptive use agriculture",
    "periodic groundwater level measurements",
    "land IQ crop mapping",
]


def search(q, rows=8, tries=6):
    """The CNRA endpoint resets connections intermittently; retry with backoff."""
    last = None
    for k in range(tries):
        try:
            r = requests.get(API, params={"q": q, "rows": rows},
                             headers={"User-Agent": UA}, timeout=60)
            r.raise_for_status()
            return r.json()["result"]
        except Exception as e:
            last = e
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"query {q!r} failed after {tries} tries: {last}")


for q in QUERIES:
    res = search(q)
    print(f"\n########## QUERY: {q}   ({res['count']} hits)")
    for p in res["results"]:
        print(f"\n  == {p['title']}   [{p['name']}]")
        notes = (p.get("notes") or "").replace("\n", " ")[:220]
        print(f"     {notes}")
        for rs in p.get("resources", []):
            print(f"     - {rs.get('format','?'):8s} {rs.get('name','')[:60]:60s} {rs.get('url','')}")
