"""Probe which external data endpoints this machine can actually reach.

Reports status codes and content-types. Nothing is assumed to work.
"""
import sys
import json
import requests

URLS = [
    ("cnra-ckan-api", "https://data.cnra.ca.gov/api/3/action/package_search?q=cimis+eto&rows=5"),
    ("ca-ckan-api", "https://data.ca.gov/api/3/action/package_search?q=water+portfolio&rows=5"),
    ("cimis-web", "https://cimis.water.ca.gov/"),
    ("openet-api", "https://openet-api.org/openapi.json"),
    ("sgma-web", "https://sgma.water.ca.gov/"),
    ("prism", "https://prism.oregonstate.edu/"),
    ("gridmet-thredds", "https://www.northwestknowledge.net/metdata/data/"),
]

for name, url in URLS:
    try:
        r = requests.get(url, timeout=45, headers={"User-Agent": "research-script"})
        ct = r.headers.get("content-type", "")
        print(f"{name:18s} {r.status_code} {ct[:40]:40s} {len(r.content):>10,} B  {url}")
    except Exception as e:
        print(f"{name:18s} FAIL {type(e).__name__}: {str(e)[:120]}  {url}")
