"""Download CONAGUA SINA daily reservoir monitoring, resumable.

Endpoint discovered by reading the React bundle of the public SINA
"Monitoreo de Presas" app (https://sinav30.conagua.gob.mx:8080/Presas/):

    urlApi = "https://sinav30.conagua.gob.mx:8080/PresasPG"
    fetch(urlApi + "/presas/reporte/" + YYYY-MM-DD)

It returns a JSON array, one object per monitored dam, with `namoalmac`
(NAMO conservation capacity, hm^3), `almacenaactual` (current storage,
hm^3), `llenano` (fill fraction), lat/lon and state/municipality.

The host sits behind Imperva, which drops connections aggressively, so
every date is retried with backoff and cached to its own file. Re-running
skips dates already on disk.
"""

import json
import random
import sys
import time
from pathlib import Path

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings()

BASE = "https://sinav30.conagua.gob.mx:8080/PresasPG/presas/reporte/"
OUT = Path(r"E:\Water\NuevoLeon\raw\conagua_presas")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")


def make_session():
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json",
                      "Connection": "close"})
    return s


def fetch_date(s, date_str, tries=6):
    for k in range(tries):
        try:
            r = s.get(BASE + date_str, verify=False, timeout=90)
            if r.status_code == 200:
                return r.json()
            if r.status_code == 404:
                return []
        except Exception:
            pass
        time.sleep(1.5 * (k + 1) + random.random())
    return None


def main(days=("05", "15", "25"), start="2007-01", end="2026-07"):
    OUT.mkdir(parents=True, exist_ok=True)
    months = pd.period_range(start, end, freq="M")
    wanted = [f"{m}-{d}" for m in months.astype(str) for d in days]
    s = make_session()
    ok = fail = skip = 0
    for i, d in enumerate(wanted):
        f = OUT / f"{d}.json"
        if f.exists():
            skip += 1
            continue
        j = fetch_date(s, d)
        if j is None:
            fail += 1
            print(f"FAIL {d}", flush=True)
            s = make_session()
            time.sleep(5)
            continue
        f.write_text(json.dumps(j), encoding="utf-8")
        ok += 1
        if ok % 20 == 0:
            print(f"{i + 1}/{len(wanted)} ok={ok} fail={fail} skip={skip} last={d} n={len(j)}",
                  flush=True)
        time.sleep(0.4)
    print(f"DONE ok={ok} fail={fail} skip={skip}")


if __name__ == "__main__":
    main(days=tuple(sys.argv[1].split(",")) if len(sys.argv) > 1 else ("05", "15", "25"))
