"""The mega-drying definition of Chandanpurkar et al. (2025), on our own units.

    python 41_megaregions.py 06      # or aq

Science Advances 11(30) eadx0298 maps a bias-corrected GRACE field at 0.25
degrees and outlines "mega-regions": areas drying faster than -0.2 cm/yr that
join hot spots previously reported separately. The paper releases no gridded
product, so the field itself cannot be summarized on basins. The definition can.

What this does. It applies that threshold to the JPL mascon series this project
already aggregates onto HydroBASINS level 6 and onto WHYMAP hydrogeological
units, then merges touching flagged units into connected clusters, which is the
part of their method that turns separate hot spots into one region.

What it does not do. It is not their figure. They start from JPL RL06 v3 and
bias-correct it against GLDAS-2.2-DA before contouring; this starts from JPL
RL06.3Mv04 CRI with no correction and no downscaling, because the downscaling
tab measures that step adding little at basin scale. Their outlines are drawn on
0.25 degree cells, these on basin polygons, so boundaries differ by the size of
a basin. Treat this as the same question asked of a coarser, unmodified field.

Two windows are reported: theirs, 2003-02 to 2024-04, and everything we have.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"E:\Water\_shared")
sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import trend as T  # noqa: E402
import red_grid as rg  # noqa: E402

RED = rg.RED
LEVEL = sys.argv[1] if len(sys.argv) > 1 else "06"
TAG = "aquifer" if LEVEL in ("aq", "aquifer", "aquifers") else f"level{LEVEL}"

# The paper's cut, in its own units: -0.2 cm/yr. Everything here is mm/yr.
THRESHOLD_MM_YR = -2.0
PAPER_WINDOW = ("2003-02", "2024-04")
MIN_CLUSTER_KM2 = 200_000
# The four mega-regions the paper names, as loose boxes. They exist to label
# our clusters, never to define them: a cluster is built from the data and then
# asked which box holds most of it.
PAPER_REGIONS = {
    "1 northern Canada and Alaska": (-170, -60, 50, 83),
    "2 northern Russia": (30, 180, 50, 80),
    "3 southwestern North America and Central America": (-125, -75, 5, 42),
    "4 MENA and Pan-Eurasia": (-15, 95, 10, 50),
}

series = pd.read_parquet(RED / f"series_{TAG}_jpl.parquet")
basins = rg.load_basins(LEVEL)
n = len(basins)

# The paper works on the continents excluding Greenland and Antarctica, and
# reports its numbers again with glaciers and ice caps removed. Ice loss is not
# drying, and at -135 mm/yr a Greenland basin would dominate any cluster it
# joined, so the headline here is the ice-free set and the all-land number is
# reported beside it.
ice_csv = rg.ROOT / "trends" / f"glacier_fraction_lev{'aq' if TAG == 'aquifer' else LEVEL}.csv"
ice = pd.read_csv(ice_csv).set_index("HYBAS_ID")["glacier_fraction"]
ice_frac = basins["HYBAS_ID"].astype("int64").map(ice).fillna(0).to_numpy()
ice_free = ice_frac <= 0.20
print(f"{int((~ice_free).sum())} units over one fifth ice, excluded from the headline")
assert series.shape[1] == n, (series.shape, n)
print(f"{TAG}: {n:,} units, {len(series)} months, "
      f"{series.index[0]:%Y-%m} to {series.index[-1]:%Y-%m}")


def fit(window):
    """Trend and p-value per unit over one window, same estimator as the rest
    of the project: slope with annual and semi-annual harmonics, significance
    on an effective sample size for lag-1 autocorrelation."""
    x = series.loc[window[0]:window[1]] if window else series
    ok = np.isfinite(x.to_numpy()).all(axis=0)
    cols = np.flatnonzero(ok)
    out = np.full(n, np.nan)
    pv = np.full(n, np.nan)
    da = xr.DataArray(x.to_numpy()[:, cols], dims=("time", "b"),
                      coords={"time": x.index, "b": cols})
    r = T.fit_trend(da, dim="time")
    out[cols] = r["trend"].values
    pv[cols] = r["p_value"].values
    return out, pv, len(x)


def by_fdr(p, alpha=0.05):
    """Benjamini-Yekutieli, which holds under the spatial dependence measured
    in 40_spatial_autocorr.py. Returns a boolean mask over all units."""
    ok = np.isfinite(p)
    q = np.sort(p[ok])
    m = len(q)
    rank = np.arange(1, m + 1)
    c_m = np.log(m) + 0.5772156649 + 1.0 / (2 * m)
    passing = q <= alpha * rank / (m * c_m)
    if not passing.any():
        return np.zeros(n, dtype=bool), np.nan
    cut = q[rank[passing].max() - 1]
    return np.isfinite(p) & (p <= cut), float(cut)


def clusters(flagged):
    """Merge touching flagged units into connected regions.

    This is the step that makes a mega-region: the paper joins hot spots that
    had been reported as separate. Here two flagged units join when their
    polygons touch.
    """
    sub = basins.loc[flagged].copy()
    if not len(sub):
        return pd.Series(dtype="int64"), {}
    pos = {ix: i for i, ix in enumerate(sub.index)}
    pairs = sub.sjoin(sub[["geometry"]], how="inner", predicate="intersects")
    a = np.array([pos[i] for i in pairs.index])
    b = np.array([pos[i] for i in pairs["index_right"]])
    parent = np.arange(len(sub))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in zip(a, b):
        ri, rj = root(i), root(j)
        if ri != rj:
            parent[max(ri, rj)] = min(ri, rj)
    lab = np.array([root(i) for i in range(len(sub))])
    return pd.Series(lab, index=sub.index), sub


def label_cluster(sub_cluster):
    """Which of the paper's four regions holds most of this cluster's area."""
    pt = sub_cluster.geometry.representative_point()
    lon, lat = pt.x.to_numpy(), pt.y.to_numpy()
    area = sub_cluster["SUB_AREA"].to_numpy()
    best, best_share = None, 0.0
    for name, (lo, hi, la, lb) in PAPER_REGIONS.items():
        inside = (lon >= lo) & (lon <= hi) & (lat >= la) & (lat <= lb)
        share = float(area[inside].sum() / area.sum())
        if share > best_share:
            best, best_share = name, share
    return (best, best_share) if best_share >= 0.5 else (None, best_share)


area = basins["SUB_AREA"].to_numpy()
result = {
    "unit": TAG,
    "n_units": int(n),
    "threshold_cm_yr": -0.2,
    "threshold_mm_yr": THRESHOLD_MM_YR,
    "source": "JPL mascon RL06.3Mv04 CRI, aggregated conservatively, no "
              "downscaling and no bias correction",
    "paper": "Chandanpurkar et al. 2025, Science Advances 11(30) eadx0298, "
             "doi 10.1126/sciadv.adx0298",
    "not_a_replication": "the paper contours a GLDAS-2.2-DA bias-corrected "
                         "0.25 degree field, which it does not release; this "
                         "applies its threshold and its merge rule to the "
                         "unmodified coarse solution on basin polygons",
    "ice": "units over one fifth glacier or ice sheet are excluded, as the "
           "paper excludes Greenland and Antarctica; Natural Earth 10m",
    "windows": {},
}

for wname, window in [("paper_2003_02_to_2024_04", PAPER_WINDOW),
                      ("full_record", None)]:
    tr, pv, nm = fit(window)
    have = np.isfinite(tr) & ice_free
    have_all = np.isfinite(tr)
    drying = have & (tr <= THRESHOLD_MM_YR)
    drying_all = have_all & (tr <= THRESHOLD_MM_YR)
    sig, by_cut = by_fdr(pv)
    lab, sub = clusters(drying)

    rows = []
    if len(sub):
        sub = sub.assign(_cluster=lab.to_numpy())
        for cid, part in sub.groupby("_cluster"):
            a_km2 = float(part["SUB_AREA"].sum())
            if a_km2 < MIN_CLUSTER_KM2:
                continue
            name, share = label_cluster(part)
            pt = part.geometry.representative_point()
            rows.append({
                "units": int(len(part)),
                "area_km2": a_km2,
                "area_share_of_land": a_km2 / float(area[have].sum()),
                "paper_region": name,
                "share_inside_that_box": round(share, 3),
                "lon_range": [float(pt.x.min()), float(pt.x.max())],
                "lat_range": [float(pt.y.min()), float(pt.y.max())],
                "median_trend_mm_yr": float(np.median(part.index.map(
                    pd.Series(tr, index=basins.index)).to_numpy())),
            })
    rows.sort(key=lambda r: -r["area_km2"])

    w = {
        "months": int(nm),
        "n_with_trend": int(have.sum()),
        "n_drying": int(drying.sum()),
        "n_drying_including_ice": int(drying_all.sum()),
        "drying_share_of_land_area_including_ice":
            float(area[drying_all].sum() / area[have_all].sum()),
        "n_units_over_one_fifth_ice": int((~ice_free).sum()),
        "drying_share_of_units": float(drying.sum() / have.sum()),
        "drying_area_km2": float(area[drying].sum()),
        "drying_share_of_land_area": float(area[drying].sum() / area[have].sum()),
        "n_drying_significant_p05": int((drying & np.isfinite(pv) & (pv < 0.05)).sum()),
        "n_drying_significant_by_fdr": int((drying & sig).sum()),
        "by_fdr_p_cut": by_cut,
        "median_trend_mm_yr_all": float(np.nanmedian(tr)),
        "median_trend_mm_yr_drying": float(np.nanmedian(tr[drying])),
        "n_clusters_over_200k_km2": len(rows),
        "clusters": rows[:12],
    }
    if TAG == "aquifer" and "aq_group" in basins.columns:
        grp = basins.loc[drying, "aq_group"].value_counts()
        tot = basins.loc[have, "aq_group"].value_counts()
        w["drying_by_aquifer_class"] = {
            k: {"drying": int(v), "of": int(tot.get(k, 0)),
                "share": float(v / tot.get(k, np.nan))}
            for k, v in grp.items()}
    result["windows"][wname] = w

    print(f"\n[{wname}] {nm} months")
    print(f"  drying at {THRESHOLD_MM_YR} mm/yr: {w['n_drying']:,} of "
          f"{w['n_with_trend']:,} units, {w['drying_share_of_land_area']*100:.1f}% "
          f"of land area")
    print(f"  of those, significant at p 0.05: {w['n_drying_significant_p05']:,}; "
          f"under Benjamini-Yekutieli: {w['n_drying_significant_by_fdr']:,}")
    for r in rows[:6]:
        nm_ = r["paper_region"] or "unmatched"
        print(f"  cluster {r['area_km2']/1e6:6.2f} Mkm2  {r['units']:5d} units  "
              f"median {r['median_trend_mm_yr']:+.2f} mm/yr  {nm_}")

out = RED / f"megaregions_{TAG}.json"
json.dump(result, open(out, "w"), indent=2, default=float)
print("\nwrote", out)

# The per-unit table, so the flags can be mapped or joined downstream.
tr, pv, _ = fit(PAPER_WINDOW)
flags = pd.DataFrame({
    "HYBAS_ID": basins["HYBAS_ID"].to_numpy(),
    "SUB_AREA": area,
    "trend_mm_yr_paper_window": tr,
    "p_value": pv,
    "glacier_fraction": ice_frac,
    "drying_02cm": np.isfinite(tr) & ice_free & (tr <= THRESHOLD_MM_YR),
})
flags.to_parquet(RED / f"megaregions_{TAG}.parquet")
print("wrote", RED / f"megaregions_{TAG}.parquet")
