"""Is the GSFC north-south contrast hydrology, or the solution's own region blocks?

GSFC RL06v2 carries a `mascon/basin` code per mascon. In this window it takes
value 1004 on the United States side of the Rio Grande and 2001 / 2004 / 2005
on the Mexican side, and the code boundary follows the river exactly. GSFC
regularizes within those regions, so a trend contrast that lands on the
boundary is not automatically hydrological.

This quantifies how much of the per-mascon trend variance the basin code
explains, in GSFC and in CSR sampled on the identical footprints. CSR uses a
different mascon definition and knows nothing about GSFC's regions, so if the
contrast is real CSR should show it too.
"""

import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(r"E:\Water\NuevoLeon")
H5 = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")


def eta_squared(y, groups):
    """Fraction of variance in y explained by a categorical grouping."""
    y = np.asarray(y, float)
    ok = np.isfinite(y)
    y, groups = y[ok], np.asarray(groups)[ok]
    grand = y.mean()
    ss_tot = ((y - grand) ** 2).sum()
    ss_bet = sum(((y[groups == g].mean() - grand) ** 2) * (groups == g).sum()
                 for g in np.unique(groups))
    return float(ss_bet / ss_tot)


def main():
    g = pd.read_csv(ROOT / "trends" / "post2020_gradient.csv")
    with h5py.File(H5, "r") as f:
        basin = np.ravel(f["mascon/basin"][:])
    g["basin"] = basin[g["mascon_id"].to_numpy()]
    g["country"] = np.where(g["basin"] < 2000, "United States", "Mexico")
    g.to_csv(ROOT / "trends" / "post2020_gradient.csv", index=False)

    res = {"n_mascons": len(g),
           "basin_codes": {str(int(k)): int(v) for k, v in g["basin"].value_counts().items()}}
    for var, label in (("tws_trend_mm_yr", "gsfc_trend"),
                       ("csr_trend_mm_yr", "csr_trend"),
                       ("post2020_tws_mm", "gsfc_post2020_level"),
                       ("post2020_csr_mm", "csr_post2020_level")):
        y = g[var].to_numpy()
        lat = g["lat_center"].to_numpy()
        res[label] = {
            "eta2_basin_code": eta_squared(y, g["basin"].to_numpy()),
            "eta2_us_vs_mexico": eta_squared(y, g["country"].to_numpy()),
            "r2_latitude": float(stats.linregress(lat, y).rvalue ** 2),
            "mean_us": float(g.loc[g.country == "United States", var].mean()),
            "mean_mexico": float(g.loc[g.country == "Mexico", var].mean()),
        }
    # the sharpest test: mascon pairs that share a latitude band and are
    # immediate neighbours across the border
    pairs = [(1814, 3140), (1819, 3145), (1822, 3150), (1824, 3153)]
    res["cross_border_neighbour_pairs"] = [
        {"us_mascon": a, "mx_mascon": b,
         "lat": float(g.loc[g.mascon_id == a, "lat_center"].iloc[0]),
         "gsfc_trend_us": float(g.loc[g.mascon_id == a, "tws_trend_mm_yr"].iloc[0]),
         "gsfc_trend_mx": float(g.loc[g.mascon_id == b, "tws_trend_mm_yr"].iloc[0]),
         "csr_trend_us": float(g.loc[g.mascon_id == a, "csr_trend_mm_yr"].iloc[0]),
         "csr_trend_mx": float(g.loc[g.mascon_id == b, "csr_trend_mm_yr"].iloc[0])}
        for a, b in pairs]
    (ROOT / "trends" / "basin_block_check.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
