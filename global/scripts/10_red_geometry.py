"""Red experiment, test 1: is a level 6 basin nominally resolved at all?

Pure geometry. No time series, no trends. For every HydroBASINS level 6 basin
this counts the grid cells each downscaled product puts inside it, counts the
coarse GRACE mascons the basin overlaps, and measures how much of the basin
sits inside its single largest mascon.

The point of the last number: if a basin lies almost entirely within one
mascon footprint, then whatever structure a downscaled product draws inside
that basin did not come from gravimetry. It came from whatever field the
downscaling was conditioned on. That is true by construction, before any
question of skill.

The coarse reference is the JPL mascon solution rather than the GSFC solution
the rest of this repository uses, because both downscaled products are built
from JPL. Differencing a downscaled product against a different center's
solution would put center-to-center differences into the residual and score
them as added information.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

RED = rg.RED
RED.mkdir(parents=True, exist_ok=True)
LEVEL = "06"

# Vishwakarma, Devaraju and Sneeuw (2018) put the smallest area over which a
# GRACE-derived storage change stays reliable at about 63,000 square km.
RELIABLE_AREA_KM2 = 63_000

SEDA = rg.RAW / "downscaled" / "GRACE-SeDA_v1_2002_2022.nc"
LIKU = rg.RAW / "downscaled" / "LiKusche_JPL_mascon_downscaled-v2.0.nc"
JPL = rg.RAW / "jpl_mascon" / "jpl_mascon_rl0603v04_cri.nc"

basins = rg.load_basins(LEVEL)
n = len(basins)
braster = rg.basin_raster(LEVEL)
print(f"level {LEVEL}: {n} basins, {basins.SUB_AREA.sum()/1e6:.1f} million km2, "
      f"median {basins.SUB_AREA.median():,.0f} km2")

# ---------------------------------------------------------------- coarse GRACE
jpl = xr.open_dataset(JPL)
jlat = jpl["lat"].values
jlon = jpl["lon"].values
wj = rg.GridWeights(braster, jlat, jlon, n)
print(f"JPL grid {len(jlat)}x{len(jlon)}, {len(wj.basin):,} basin-cell overlaps")

# Every basin's rasterized area, as a check on the overlap bookkeeping. It will
# not match SUB_AREA exactly: HydroSHEDS computes area in its own projection
# and a 0.05 degree raster cannot follow a coastline.
basins["raster_area_km2"] = wj.basin_area_km2

# Which 3-degree mascon each master cell belongs to, through the JPL grid.
mid = np.asarray(jpl["mascon_ID"].values)
jy = np.clip(np.floor((rg.MLAT - (jlat.min() - 0.25)) / 0.5).astype(int), 0, len(jlat) - 1)
jx = np.clip(np.floor(np.mod(rg.MLON - (jlon.min() - 0.25), 360.0) / 0.5).astype(int),
             0, len(jlon) - 1)
if jlat[0] > jlat[-1]:
    jy = len(jlat) - 1 - jy
mascon_of_master = mid[np.ix_(jy, jx)]

area_row = rg.cell_area_km2()
keys, wts = [], []
for j in range(len(rg.MLAT)):
    row = braster[j]
    m = row >= 0
    if not m.any():
        continue
    keys.append(row[m].astype(np.int64) * 1_000_000 + mascon_of_master[j][m].astype(np.int64))
    wts.append(np.full(int(m.sum()), area_row[j]))
keys = np.concatenate(keys)
wts = np.concatenate(wts)
order = np.argsort(keys, kind="stable")
keys, wts = keys[order], wts[order]
uk, start = np.unique(keys, return_index=True)
uw = np.add.reduceat(wts, start)
kb = (uk // 1_000_000).astype(np.int64)

n_footprints = np.bincount(kb, minlength=n)
tot = np.bincount(kb, weights=uw, minlength=n)
big = np.zeros(n)
np.maximum.at(big, kb, uw)
frac_dominant = np.divide(big, tot, out=np.zeros(n), where=tot > 0)

# A mascon that clips one corner of a basin is not a second measurement of it,
# so the count is also reported with slivers under a twentieth of the basin
# dropped.
share = uw / np.where(tot[kb] > 0, tot[kb], np.nan)
n_footprints_5pct = np.bincount(kb[share >= 0.05], minlength=n)

basins["n_native_footprints"] = n_footprints
basins["n_native_footprints_5pct"] = n_footprints_5pct
basins["frac_dominant_mascon"] = frac_dominant

# ---------------------------------------------------------- downscaled products
seda = xr.open_dataset(SEDA)
ws = rg.GridWeights(braster, seda["latitude"].values, seda["longitude"].values, n)
basins["n_cells_G"] = ws.n_cells_centroid(braster)
seda_valid = np.asarray(seda["mask"].values).T > 0        # stored (lon, lat)
basins["cover_G"] = ws.coverage(seda_valid)

if LIKU.exists():
    liku = xr.open_dataset(LIKU)
    lat_name = "lat" if "lat" in liku.coords else "latitude"
    lon_name = "lon" if "lon" in liku.coords else "longitude"
    wl = rg.GridWeights(braster, liku[lat_name].values, liku[lon_name].values, n)
    basins["n_cells_L"] = wl.n_cells_centroid(braster)
else:
    print("Li and Kusche file not present yet; n_cells_L left empty")
    basins["n_cells_L"] = np.nan

# The JPL grid is 0.5 degrees too, so cell counts there say what the coarse
# solution nominally offers before the mascon footprint is taken into account.
basins["n_cells_coarse"] = wj.n_cells_centroid(braster)

out = basins.drop(columns="geometry")
out.to_parquet(RED / "level6_geometry.parquet")

area = basins["SUB_AREA"].to_numpy()
summary = {
    "level": LEVEL,
    "n_basins": int(n),
    "total_area_km2": float(area.sum()),
    "area_km2": {q: float(np.percentile(area, q)) for q in (5, 25, 50, 75, 95)},
    "reliable_area_threshold_km2": RELIABLE_AREA_KM2,
    "n_above_reliable_threshold": int((area >= RELIABLE_AREA_KM2).sum()),
    "area_share_above_reliable_threshold": float(
        area[area >= RELIABLE_AREA_KM2].sum() / area.sum()),
    "median_n_cells_G": float(np.median(basins["n_cells_G"])),
    "median_n_cells_L": (float(np.nanmedian(basins["n_cells_L"]))
                         if basins["n_cells_L"].notna().any() else None),
    "median_n_native_footprints": float(np.median(n_footprints)),
    "median_frac_dominant_mascon": float(np.median(frac_dominant)),
    "n_frac_dominant_over_0p95": int((frac_dominant > 0.95).sum()),
    "n_cells_G_under_2": int((basins["n_cells_G"] < 2).sum()),
    "raster_area_check": {
        "median_ratio_raster_to_subarea": float(
            np.median(basins["raster_area_km2"] / basins["SUB_AREA"])),
        "n_basins_with_no_raster_cell": int((basins["raster_area_km2"] == 0).sum()),
    },
}
json.dump(summary, open(RED / "level6_geometry_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
