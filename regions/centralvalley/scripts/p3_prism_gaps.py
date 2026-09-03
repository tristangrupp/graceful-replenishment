"""Phase 3l - fetch ONLY the PRISM months still missing, strictly serially.

One request at a time, two attempts each. A month that fails twice is recorded
as unobtained and abandoned - it is not retried further. ~2.9 MB per month.
"""
import json
import sys
import time
from pathlib import Path

import pandas as pd

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))
from fetch import download

RAW = Path(r"E:\Water\CentralValley\raw\prism")
INV = Path(r"E:\Water\CentralValley\inventory")

rep = json.loads((INV / "reduction_coverage.json").read_text())
missing = rep["prism_months_missing"]
print(f"{len(missing)} months to fetch, serially")

got, failed = [], []
for ym in missing:
    url = f"https://services.nacse.org/prism/data/get/us/4km/ppt/{ym}"
    p, st = download(url, RAW / f"ppt_{ym}.zip", tries=2)
    if p is not None and p.stat().st_size > 100_000:
        got.append(ym)
        print(f"  {ym}: ok {p.stat().st_size:,} B", flush=True)
    else:
        if p is not None:
            p.unlink(missing_ok=True)
        failed.append(ym)
        print(f"  {ym}: UNOBTAINED ({st})", flush=True)
    time.sleep(1.0)

(INV / "prism_gap_fetch.json").write_text(json.dumps(
    {"requested": missing, "obtained": got, "unobtained": failed}, indent=2))
print(f"\nobtained {len(got)}, unobtained {len(failed)}: {failed}")
