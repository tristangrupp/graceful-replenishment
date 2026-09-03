"""Phase 1b - value domains of the key DWR i15 attribute fields, per survey year.

Reads attributes only (read_geometry=False), full table, and reports value counts
for the fields that determine crop class and irrigation status.
"""
import json
from pathlib import Path

import pyogrio
import pandas as pd

TMP = Path(r"E:\Water\CentralValley\tmp")
OUT = Path(r"E:\Water\CentralValley\inventory")
YEARS = [2014, 2016, 2018, 2019, 2020, 2021, 2022, 2023]

KEYS = ["CLASS1", "SUBCLASS1", "SPECOND1", "IRR_TYP1PA", "IRR_TYP1PB",
        "MULTIUSE", "PCNT1", "CLASS2", "SYMB_CLASS", "Symb_class",
        "Crop2014", "DWR_Standa", "DWR_REVISE", "DWR_revise",
        "CROPTYP1", "UCF_ATT"]


def find_shp(year):
    shps = sorted((TMP / f"cm_{year}").rglob("*.shp"))
    return max(shps, key=lambda p: p.stat().st_size) if shps else None


def main():
    out = {}
    for y in YEARS:
        shp = find_shp(y)
        if shp is None:
            print(f"{y}: missing")
            continue
        info = pyogrio.read_info(shp)
        cols = [c for c in KEYS if c in info["fields"]]
        area_col = "ACRES" if "ACRES" in info["fields"] else "Acres"
        df = pyogrio.read_dataframe(shp, columns=cols + [area_col],
                                    read_geometry=False, use_arrow=True)
        df = pd.DataFrame(df)
        rec = {"n": len(df), "acres_total": float(df[area_col].sum()),
               "acres_col": area_col}
        print(f"\n===== {y} =====  n={len(df):,} acres={rec['acres_total']:,.0f}")
        for c in cols:
            vc = df[c].astype("string").fillna("<NA>").value_counts()
            rec[c] = {str(k): int(v) for k, v in vc.head(60).items()}
            rec[c + "_nunique"] = int(vc.size)
            head = ", ".join(f"{k!r}:{v}" for k, v in list(vc.items())[:25])
            print(f"  {c} ({vc.size} distinct): {head}")
        out[y] = rec
    (OUT / "domains.json").write_text(json.dumps(out, indent=2))
    print("\nwrote", OUT / "domains.json")


if __name__ == "__main__":
    main()
