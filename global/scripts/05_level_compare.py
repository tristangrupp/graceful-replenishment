"""How much does level 4 add over level 3?

Level-4 basins nest inside level-3 ones by Pfafstetter code, so the question is
answerable: how much do a parent's children disagree with the parent, and is
that disagreement real signal or just a smaller sample of mascons?
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"E:\Water\Global")
l3 = pd.read_csv(ROOT / "trends" / "basins_lev03_trends.csv")
l4 = pd.read_csv(ROOT / "trends" / "basins_lev04_trends.csv")

l3["pfaf3"] = l3["PFAF_ID"].astype("int64")
l4["pfaf3"] = (l4["PFAF_ID"].astype("int64") // 10)
m = l4.merge(l3[["pfaf3", "tws_trend_mm_yr", "gws_trend_mm_yr", "n_mascons"]],
             on="pfaf3", suffixes=("", "_parent"))
print(f"{len(m)} level-4 basins matched to a level-3 parent of {len(l4)}")

for col in ("tws_trend_mm_yr", "gws_trend_mm_yr"):
    d = m.dropna(subset=[col, col + "_parent"])
    resid = d[col] - d[col + "_parent"]
    # weight by area so a 200 km2 basin does not count like a 2 million km2 one
    w = d["SUB_AREA"].to_numpy()
    var_within = np.average(resid**2, weights=w)
    var_total = np.average((d[col] - np.average(d[col], weights=w))**2, weights=w)
    print(f"\n{col}")
    print(f"  n = {len(d)}")
    print(f"  median |child - parent| = {resid.abs().median():.2f} mm/yr")
    print(f"  90th percentile         = {resid.abs().quantile(0.9):.2f} mm/yr")
    print(f"  area-weighted share of variance the level-3 parent already explains: "
          f"{1 - var_within/var_total:.3f}")

for name, df in (("level 3", l3), ("level 4", l4)):
    t = df.dropna(subset=["tws_trend_mm_yr"])
    g = df.dropna(subset=["gws_trend_mm_yr"])
    print(f"\n{name}: {len(t)} basins with TWS, "
          f"{100*(t['tws_p'] < 0.05).mean():.0f}% separable from zero; "
          f"{len(g)} with GWS, {100*(g['gws_p'] < 0.05).mean():.0f}% separable")
    print(f"  median |TWS| {t['tws_trend_mm_yr'].abs().median():.2f} mm/yr, "
          f"median |GWS| {g['gws_trend_mm_yr'].abs().median():.2f} mm/yr, "
          f"median mascons/basin {t['n_mascons'].median():.0f}")
    print(f"  basins resting on fewer than 3 mascons: {(t['n_mascons'] < 3).sum()}")

# where the two levels disagree most, by area
d = m.dropna(subset=["tws_trend_mm_yr", "tws_trend_mm_yr_parent"]).copy()
d["gap"] = (d["tws_trend_mm_yr"] - d["tws_trend_mm_yr_parent"]).abs()
big = d[d["SUB_AREA"] > 50000].nlargest(8, "gap")
print("\nlargest child-parent gaps among basins over 50,000 km2 (TWS):")
print(big[["HYBAS_ID", "SUB_AREA", "n_mascons", "tws_trend_mm_yr",
           "tws_trend_mm_yr_parent", "gap"]].round(1).to_string(index=False))
