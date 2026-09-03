"""Parallel, resumable version of the CONAGUA SINA reservoir download.

Same endpoint as 01_download_conagua.py; the serial version runs at about
1.7 dates/minute because each request takes ~30 s server-side, which is
2+ hours for a 20-year monthly record. A small thread pool (default 5)
brings it under 30 minutes without hammering the host.
"""

import json
import random
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import requests
import urllib3

urllib3.disable_warnings()

BASE = "https://sinav30.conagua.gob.mx:8080/PresasPG/presas/reporte/"
OUT = Path(r"E:\Water\NuevoLeon\raw\conagua_presas")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
_local = threading.local()
_lock = threading.Lock()
_state = {"ok": 0, "fail": 0, "empty": 0}


def session():
    if not hasattr(_local, "s"):
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept": "application/json",
                          "Connection": "close"})
        _local.s = s
    return _local.s


def grab(date_str, tries=5):
    f = OUT / f"{date_str}.json"
    if f.exists():
        return
    for k in range(tries):
        try:
            r = session().get(BASE + date_str, verify=False, timeout=120)
            if r.status_code == 200:
                j = r.json()
                f.write_text(json.dumps(j), encoding="utf-8")
                with _lock:
                    _state["ok"] += 1
                    if not j:
                        _state["empty"] += 1
                    n = _state["ok"]
                if n % 25 == 0:
                    print(f"ok={n} fail={_state['fail']} empty={_state['empty']} last={date_str}",
                          flush=True)
                return
        except Exception:
            pass
        _local.s = None
        del _local.s
        time.sleep(2 * (k + 1) + random.random() * 2)
    with _lock:
        _state["fail"] += 1
    print(f"FAIL {date_str}", flush=True)


def main(start="2002-04", end="2026-07", day="15", workers=5):
    OUT.mkdir(parents=True, exist_ok=True)
    dates = [f"{m}-{day}" for m in pd.period_range(start, end, freq="M").astype(str)]
    random.shuffle(dates)
    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(grab, dates))
    print("DONE", _state)


if __name__ == "__main__":
    a = sys.argv[1:]
    main(start=a[0] if len(a) > 0 else "2002-04",
         end=a[1] if len(a) > 1 else "2026-07",
         day=a[2] if len(a) > 2 else "15",
         workers=int(a[3]) if len(a) > 3 else 5)
