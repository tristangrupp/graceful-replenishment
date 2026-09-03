"""Aggregate mascon storage trends onto HydroBASINS polygons at a given level.

    python 02_basins.py 03      # or 04

A mascon is not a basin and the two do not nest, so the aggregation runs on a
0.1 degree grid: every terrestrial cell inherits the trend of the mascon that
contains it and is assigned to the basin polygon it falls inside, then each
basin is a cos(lat)-weighted mean of its cells. That is an area-weighted
overlap without polygon intersection.

The basin *series* is built the same way and the trend fitted on it, rather than
averaging per-mascon trends. Both give the same slope, since the fit is linear
in the data, but only fitting the series gives an honest p-value.

Coverage is tracked rather than assumed. GLDAS models no ice-sheet storage, so
the groundwater term is undefined over Greenland and the ice caps; those basins
are reported with the share of their weight that actually carried a value, and
dropped from the groundwater map below half. Missing values are never averaged
in as zero.
"""

import glob
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
from gsfc_grid import ICE, cell_to_mascon, load_geometry, terrestrial  # noqa: E402

ROOT = Path(r"E:\Water\Global")
RES = 0.1
MIN_COVERAGE = 0.50
MAX_ICE = 0.20
LEVEL = sys.argv[1] if len(sys.argv) > 1 else "03"

geo = load_geometry()
land = terrestrial(geo)
is_ice = geo['location'].isin(ICE).to_numpy()

basins = pd.concat(
    [gpd.read_file(p) for p in sorted(glob.glob(
        str(ROOT / "raw" / "hydrobasins" / f"*lev{LEVEL}*.shp")))],
    ignore_index=True)
basins = gpd.GeoDataFrame(basins, geometry="geometry", crs="EPSG:4326")
basins["basin_idx"] = np.arange(len(basins))
print(f"level {LEVEL}: {len(basins)} basins, {basins.SUB_AREA.sum()/1e6:.1f} million km2, "
      f"median {basins.SUB_AREA.median():,.0f} km2")

lat = np.arange(-90 + RES / 2, 90, RES)
lon = np.arange(-180 + RES / 2, 180, RES)
mapping = cell_to_mascon(geo, lat, lon)
LON, LAT = np.meshgrid(lon, lat)
keep = land[mapping]
pts = gpd.GeoDataFrame(
    {"mascon_id": mapping[keep].astype(np.int64), "w": np.cos(np.deg2rad(LAT[keep]))},
    geometry=gpd.points_from_xy(LON[keep], LAT[keep]), crs="EPSG:4326")
joined = gpd.sjoin(pts, basins[["basin_idx", "geometry"]], how="inner", predicate="within")
print(f"{len(pts):,} terrestrial cells at {RES} deg, {len(joined):,} inside a basin")

wmat = joined.groupby(["basin_idx", "mascon_id"])["w"].sum().reset_index()

tws = pd.read_parquet(ROOT / "processed" / "tws_anomaly_mm_land.parquet")
gws = pd.read_parquet(ROOT / "processed" / "gws_anomaly_mm_land.parquet")
tws.columns = [int(c) for c in tws.columns]
gws.columns = [int(c) for c in gws.columns]
mtr = pd.read_parquet(ROOT / "trends" / "mascon_trends_gracefo.parquet").set_index("mascon_id")
have_series = set(tws.columns)


def endpoints(series):
    """First-year and last-year means of the deseasonalised series.

    Deseasonalised first, because the first and last years of this record are
    partial: 2018 starts in June and 2026 stops in March. Averaging raw months
    would compare one year's summer against another year's winter. Subtracting
    each month-of-year's own mean removes that, though it cannot invent the
    months GRACE did not solve.
    """
    s = series.dropna()
    if s.empty:
        return {}
    clim = s.groupby(s.index.month).transform("mean")
    des = s - clim
    years = des.groupby(des.index.year)
    mean = years.mean()
    count = years.size()
    y0, y1 = int(mean.index.min()), int(mean.index.max())
    return {
        "first_year": y0, "last_year": y1,
        "first_mm": float(mean.loc[y0]), "last_mm": float(mean.loc[y1]),
        "change_mm": float(mean.loc[y1] - mean.loc[y0]),
        "n_first": int(count.loc[y0]), "n_last": int(count.loc[y1]),
    }


def fit_one(series):
    s = series.dropna()
    if len(s) < 36:
        return np.nan, np.nan
    da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                      coords={"time": s.index, "x": [0]})
    r = T.fit_trend(da, dim="time")
    return float(r["trend"].values[0]), float(r["p_value"].values[0])


rows = []
for bi, g in wmat.groupby("basin_idx"):
    ids = g["mascon_id"].to_numpy()
    w = g["w"].to_numpy()
    sel = np.array([i in have_series for i in ids])
    ids, w = ids[sel], w[sel]
    if not len(ids):
        continue

    tws_series = (tws[ids] * (w / w.sum())).sum(axis=1)
    tt, tp = fit_one(tws_series)
    te = endpoints(tws_series)

    # GLDAS carries snow water equivalent over Greenland and the ice caps, so a
    # coverage test alone passes there and quietly returns "ice sheet mass loss
    # minus modelled snowpack" as if it were groundwater. Ice-dominated basins
    # are therefore excluded by what they are, not by whether a number exists.
    ice_frac = float(w[is_ice[ids]].sum() / w.sum())
    gvals = gws[ids]
    ok = np.isfinite(gvals.to_numpy()).all(axis=0)
    coverage = float(w[ok].sum() / w.sum())
    if ok.any():
        gsel = gvals.loc[:, gvals.columns[ok]]
        gws_series = (gsel * (w[ok] / w[ok].sum())).sum(axis=1)
        gt, gp = fit_one(gws_series)
        ge = endpoints(gws_series)
        spread = float(np.average(mtr.loc[ids[ok], "gws_model_spread_mm_yr"], weights=w[ok]))
    else:
        gt = gp = spread = np.nan
        ge = {}

    # A basin that fits inside one or two mascons is not resolved by GRACE; the
    # number is still the best available but it is the mascon's number, not the
    # basin's, so the count travels with it.
    rows.append({"basin_idx": bi, "n_mascons": int(len(ids)), "grid_cells": int(len(g)),
                 "tws_trend_mm_yr": tt, "tws_p": tp,
                 "gws_trend_mm_yr": gt, "gws_p": gp,
                 "gws_coverage": coverage, "ice_fraction": ice_frac,
                 "gws_model_spread_mm_yr": spread,
                 "first_year": te.get("first_year"), "last_year": te.get("last_year"),
                 "n_months_first_year": te.get("n_first"), "n_months_last_year": te.get("n_last"),
                 "tws_first_year_mm": te.get("first_mm"), "tws_last_year_mm": te.get("last_mm"),
                 "tws_endpoint_change_mm": te.get("change_mm"),
                 "gws_first_year_mm": ge.get("first_mm"), "gws_last_year_mm": ge.get("last_mm"),
                 "gws_endpoint_change_mm": ge.get("change_mm")})

res = pd.DataFrame(rows)
span_years = (tws.index.max() - tws.index.min()).days / 365.25
res["span_years"] = round(span_years, 2)
res["tws_trend_implied_change_mm"] = res["tws_trend_mm_yr"] * span_years
res["gws_trend_implied_change_mm"] = res["gws_trend_mm_yr"] * span_years
low = (res["gws_coverage"] < MIN_COVERAGE) | (res["ice_fraction"] > MAX_ICE)
res.loc[low, ["gws_trend_mm_yr", "gws_p", "gws_first_year_mm", "gws_last_year_mm",
                  "gws_endpoint_change_mm", "gws_trend_implied_change_mm"]] = np.nan
out = basins.merge(res, on="basin_idx", how="left")
out.to_file(ROOT / "trends" / f"basins_lev{LEVEL}_trends.gpkg", driver="GPKG")
out.drop(columns="geometry").to_csv(ROOT / "trends" / f"basins_lev{LEVEL}_trends.csv", index=False)

has_t = out["tws_trend_mm_yr"].notna()
covered_area = float(out.loc[has_t, "SUB_AREA"].sum())
summary = {
    "level": LEVEL,
    "n_basins": int(len(out)),
    "n_with_tws": int(has_t.sum()),
    "n_with_gws": int(out["gws_trend_mm_yr"].notna().sum()),
    "n_gws_dropped": int(low.sum()),
    "n_gws_dropped_low_coverage": int((res["gws_coverage"] < MIN_COVERAGE).sum()),
    "n_gws_dropped_ice": int((res["ice_fraction"] > MAX_ICE).sum()),
    "share_of_level_area_covered": covered_area / float(out["SUB_AREA"].sum()),
    "basin_area_km2": {"median": float(out["SUB_AREA"].median()),
                       "min": float(out["SUB_AREA"].min()),
                       "max": float(out["SUB_AREA"].max())},
    "mascons_per_basin": {
        "median": float(out.loc[has_t, "n_mascons"].median()),
        "min": int(out.loc[has_t, "n_mascons"].min()),
        "max": int(out.loc[has_t, "n_mascons"].max()),
        "n_basins_under_3_mascons": int((out.loc[has_t, "n_mascons"] < 3).sum()),
    },
    "median_tws_mm_yr": float(out["tws_trend_mm_yr"].median()),
    "median_gws_mm_yr": float(out["gws_trend_mm_yr"].median()),
    "n_tws_significant": int((out["tws_p"] < 0.05).sum()),
    "n_gws_significant": int((out["gws_p"] < 0.05).sum()),
    "tws_range": [float(out["tws_trend_mm_yr"].min()), float(out["tws_trend_mm_yr"].max())],
    "gws_range": [float(out["gws_trend_mm_yr"].min()), float(out["gws_trend_mm_yr"].max())],
    "median_model_spread_mm_yr": float(out["gws_model_spread_mm_yr"].median()),
    "endpoint": {
        "first_year": int(out["first_year"].dropna().mode().iloc[0]),
        "last_year": int(out["last_year"].dropna().mode().iloc[0]),
        "n_months_first_year": int(out["n_months_first_year"].dropna().mode().iloc[0]),
        "n_months_last_year": int(out["n_months_last_year"].dropna().mode().iloc[0]),
        "span_years": float(span_years),
        "median_tws_endpoint_change_mm": float(out["tws_endpoint_change_mm"].median()),
        "median_tws_trend_implied_change_mm": float(out["tws_trend_implied_change_mm"].median()),
        "median_gws_endpoint_change_mm": float(out["gws_endpoint_change_mm"].median()),
        "median_gws_trend_implied_change_mm": float(out["gws_trend_implied_change_mm"].median()),
        "corr_endpoint_vs_trend_implied_tws": float(
            out[["tws_endpoint_change_mm", "tws_trend_implied_change_mm"]].corr().iloc[0, 1]),
    },
}
json.dump(summary, open(ROOT / "trends" / f"basins_lev{LEVEL}_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
