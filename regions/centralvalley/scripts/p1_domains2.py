"""Phase 1c - the *second* attribute block.

The first pass showed CLASS1/IRR_TYP1* are almost entirely '*' (pad). UCF_ATT
decodes as MULTIUSE(1) + 4 (or 3) blocks of 9 chars:
  CLASS(2) SUBCLASS(2) SPECOND(1) IRR_TYP_PA(1) IRR_TYP_PB(1) PCNT(2)
and a single-crop parcel (MULTIUSE='S') carries its crop in block *2*, not 1.
So irrigation type / special condition for the main crop live in the block-2
fields. This pass reads those.
"""
import json
from pathlib import Path

import pyogrio
import pandas as pd

TMP = Path(r"E:\Water\CentralValley\tmp")
OUT = Path(r"E:\Water\CentralValley\inventory")
YEARS = [2016, 2018, 2019, 2020, 2021, 2022, 2023]

KEYS = ["MULTIUSE", "SYMB_CLASS", "Symb_class", "CLASS2", "SUBCLASS2",
        "SPECOND2", "IRR_TYP2PA", "IRR_TYP2PB", "PCNT2",
        "CLASS3", "SPECOND3", "IRR_TYP3PA", "CLASS4",
        "CROPTYP2", "MAIN_CROP", "EMRG_CROP", "REGION", "Region", "HYDRO_RGN"]


def find_shp(year):
    shps = sorted((TMP / f"cm_{year}").rglob("*.shp"))
    return max(shps, key=lambda p: p.stat().st_size) if shps else None


def main():
    out = {}
    for y in YEARS:
        shp = find_shp(y)
        info = pyogrio.read_info(shp)
        cols = [c for c in KEYS if c in info["fields"]]
        df = pd.DataFrame(pyogrio.read_dataframe(
            shp, columns=cols, read_geometry=False, use_arrow=True))
        rec = {}
        print(f"\n===== {y} =====")
        for c in cols:
            vc = df[c].astype("string").fillna("<NA>").value_counts()
            rec[c] = {str(k): int(v) for k, v in vc.head(80).items()}
            print(f"  {c} ({vc.size} distinct): "
                  + ", ".join(f"{k!r}:{v}" for k, v in list(vc.items())[:22]))
        # consistency: does SYMB_CLASS equal the last non-pad CLASS block?
        sc = "SYMB_CLASS" if "SYMB_CLASS" in df else "Symb_class"
        agree = (df[sc].astype("string").str.strip()
                 == df["CLASS2"].astype("string").str.strip()).mean()
        rec["frac_symbclass_eq_class2"] = float(agree)
        print(f"  SYMB_CLASS == CLASS2 in {agree:.4%} of rows")
        out[y] = rec
    (OUT / "domains_block2.json").write_text(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
