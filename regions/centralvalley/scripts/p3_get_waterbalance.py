"""Phase 3d - download every California Water Plan water-balance year (WY2002-2022)
and extract the agricultural terms by DAUCO.

AG001 = Applied Water - Crop Production
AG003 = Evapotranspiration of Applied Water   <- DWR's own consumptive use
AG005 = Deep Percolation of Applied Water     <- return to storage, not a loss

Units are TAF (thousand acre-feet) per water year. Each DAUCO row carries a
representative Longitude/Latitude, so no separate boundary layer is needed to
fold them onto mascons.
"""
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from fetch import get, download

RAW = Path(r"E:\Water\CentralValley\raw\waterbalance")
OUT = Path(r"E:\Water\CentralValley\processed")
PKG = ("https://data.cnra.ca.gov/api/3/action/package_show?"
       "id=water-plan-water-balance-data")


def main():
    meta = get(PKG).json()["result"]
    rows = []
    for rs in meta["resources"]:
        m = re.search(r"WY\s*(\d{4})", rs.get("name", ""), re.I)
        if not m or not rs["url"].lower().endswith(".zip"):
            continue
        wy = int(m.group(1))
        dest = RAW / f"wb_{wy}.zip"
        p, st = download(rs["url"], dest)
        print(f"WY{wy}: {st}")
        if p is None:
            continue
        with zipfile.ZipFile(p) as z:
            names = [n for n in z.namelist() if "DAUCO" in n and n.endswith(".csv")]
            if not names:
                print(f"  WY{wy}: no DAUCO csv, has {z.namelist()}")
                continue
            df = pd.read_csv(z.open(names[0]))
        rows.append(df)

    if not rows:
        raise SystemExit("no water balance data downloaded")
    all_df = pd.concat(rows, ignore_index=True)
    print(f"\n{len(all_df):,} rows, WY {all_df['WY'].min()}-{all_df['WY'].max()}")

    ag = all_df[all_df["CategoryD"].isin(["AG001", "AG003", "AG005"])].copy()
    wide = (ag.pivot_table(index=["WY", "DAUCO", "DAU.Name", "HR.Name",
                                  "Longitude", "Latitude"],
                           columns="CategoryD", values="TAF", aggfunc="sum")
            .reset_index())
    wide.columns.name = None
    wide = wide.rename(columns={"AG001": "aw_taf", "AG003": "etaw_taf",
                                "AG005": "dp_taf"})
    wide.to_parquet(OUT / "waterbalance_dauco.parquet", index=False)

    tot = wide.groupby("WY")[["aw_taf", "etaw_taf", "dp_taf"]].sum()
    print("\nStatewide totals (TAF/yr)")
    print(tot.to_string(float_format=lambda v: f"{v:,.0f}"))
    print("\nwrote", OUT / "waterbalance_dauco.parquet")


if __name__ == "__main__":
    main()
