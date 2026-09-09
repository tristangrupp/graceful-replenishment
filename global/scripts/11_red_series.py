"""Red experiment: basin-mean monthly series for every product and predictor.

Writes one parquet per series, indexed by month, one column per level 6 basin.
Nothing is compared here. This script only does the aggregation, so that the
tests downstream all run on series built the same way.

Everything is area weighted through the shared 0.05 degree basin raster, which
is a first-order conservative remap onto the basins. Units are normalized to
millimeters of equivalent water height on the way in, and the unit of every
source is read off the file rather than assumed.
"""

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"E:\Water\_shared")
sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
import red_grid as rg  # noqa: E402
from gsfc_grid import (CM_TO_MM, cell_to_mascon, load_geometry, load_series,  # noqa: E402
                       terrestrial)

RED = rg.RED
LEVEL = "06"
SEDA = rg.RAW / "downscaled" / "GRACE-SeDA_v1_2002_2022.nc"
LIKU = rg.RAW / "downscaled" / "LiKusche_JPL_mascon_downscaled-v2.0.nc"
JPL = rg.RAW / "jpl_mascon" / "jpl_mascon_rl0603v04_cri.nc"
SEC_PER_DAY = 86400.0

basins = rg.load_basins(LEVEL)
n = len(basins)
braster = rg.basin_raster(LEVEL)
cols = basins["HYBAS_ID"].astype("int64").to_numpy()
prov: dict[str, dict] = {}


def to_month(idx) -> pd.DatetimeIndex:
    return pd.DatetimeIndex(pd.DatetimeIndex(idx).to_period("M").to_timestamp())


def save(name: str, times, values: np.ndarray) -> pd.DataFrame:
    df = pd.DataFrame(values, index=to_month(times), columns=cols)
    df = df.groupby(level=0).mean().sort_index()
    df.to_parquet(RED / f"series_{name}.parquet")
    got = int(np.isfinite(df.to_numpy()).any(axis=0).sum())
    print(f"  {name}: {len(df)} months {df.index[0]:%Y-%m}..{df.index[-1]:%Y-%m}, "
          f"{got}/{n} basins with data")
    return df


# ------------------------------------------------------------------ GRACE-SeDA
print("GRACE-SeDA 0.5 deg")
seda = xr.open_dataset(SEDA)
assert seda["twsa"].attrs["units"] == "mm", seda["twsa"].attrs
stime = pd.to_datetime("1858-11-17") + pd.to_timedelta(
    np.asarray(seda["time"].values, dtype="float64"), unit="D")
sv = np.asarray(seda["twsa"].transpose("time", "latitude", "longitude").values, dtype="float64")
smask = np.asarray(seda["mask"].values).T > 0
sv[:, ~smask] = np.nan
ws = rg.GridWeights(braster, seda["latitude"].values, seda["longitude"].values, n)
seda_b = save("seda", stime, ws.means(sv))
prov["seda"] = {
    "file": SEDA.name, "doi": "10.3929/ethz-b-000648738",
    "units_in_file": "mm", "grid": "0.5 deg", "n_months_in_file": int(len(stime)),
    "baseline": "temporal mean 2004.000 to 2009.999 removed (`twsa_baseline` in the file)",
    "coarse_parent": "JPL mascon RL06.1Mv03CRI",
}
del sv

# ------------------------------------------------------------- Li and Kusche
if LIKU.exists() and LIKU.stat().st_size > 100_000_000:
    print("Li and Kusche 0.25 deg")
    liku = xr.open_dataset(LIKU)
    var = "JPL_EWH_downscaled"
    units = liku[var].attrs.get("units", "unknown")
    if units.strip().lower() != "cm":
        raise SystemExit(f"Li and Kusche units are {units!r}, not the cm this code converts")
    lv = np.asarray(liku[var].transpose("time", "lat", "lon").values,
                    dtype="float64") * CM_TO_MM
    wl = rg.GridWeights(braster, liku["lat"].values, liku["lon"].values, n)
    # Time is a decimal year at mid-month, not a date. 2002.2916 is April 2002.
    dy = np.asarray(liku["time"].values, dtype="float64")
    yr = np.floor(dy).astype(int)
    mo = np.clip((np.floor((dy - yr) * 12) + 1).astype(int), 1, 12)
    ltime = pd.to_datetime([f"{y}-{m:02d}-15" for y, m in zip(yr, mo)])
    save("liku", ltime, wl.means(lv))
    prov["liku"] = {"file": LIKU.name, "doi": "10.5281/zenodo.17265162",
                    "md5": "7d51f349bf74543d3bcd73e504502073",
                    "variable": var, "units_in_file": units,
                    "units_used": "mm, converted from cm", "grid": "0.25 deg",
                    "time_in_file": "decimal year at mid-month",
                    "coverage": f"{ltime[0]:%Y-%m} to {ltime[-1]:%Y-%m}",
                    "n_months_in_file": int(len(ltime)),
                    "coarse_parent": "JPL mascon, release not stated in the file"}
    del lv
else:
    print("Li and Kusche file not present; skipping")

# ---------------------------------------------------------- JPL coarse mascons
print("JPL mascon 0.5 deg grid")
jpl = xr.open_dataset(JPL)
assert jpl["lwe_thickness"].attrs["units"] == "cm", jpl["lwe_thickness"].attrs
jv = np.asarray(jpl["lwe_thickness"].values, dtype="float64") * CM_TO_MM
land = np.asarray(jpl["land_mask"].values) > 0
jv[:, ~land] = np.nan
wj = rg.GridWeights(braster, jpl["lat"].values, jpl["lon"].values, n)
save("jpl", pd.to_datetime(jpl["time"].values), wj.means(jv))
prov["jpl"] = {
    "file": JPL.name, "short_name": "TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4",
    "units_in_file": "cm", "grid": "0.5 deg grid over 3 deg mascons",
    "n_months_in_file": int(jpl.sizes["time"]),
    "note": "gain factors deliberately not applied; they are a model-derived "
            "correction and applying one would itself add model structure",
}
del jv

# --------------------------------------------------------- GSFC coarse mascons
print("GSFC mascons, second solution")
geo = load_geometry()
gs = load_series()
mas_of_master = cell_to_mascon(geo, rg.MLAT, rg.MLON)
area_row = rg.cell_area_km2()
keys, wts = [], []
for j in range(len(rg.MLAT)):
    row = braster[j]
    m = row >= 0
    if not m.any():
        continue
    keys.append(row[m].astype(np.int64) * 100_000 + mas_of_master[j][m].astype(np.int64))
    wts.append(np.full(int(m.sum()), area_row[j]))
keys = np.concatenate(keys)
wts = np.concatenate(wts)
order = np.argsort(keys, kind="stable")
keys, wts = keys[order], wts[order]
uk, start = np.unique(keys, return_index=True)
gb = (uk // 100_000).astype(np.int32)
gm = (uk % 100_000).astype(np.int64)
gw = np.add.reduceat(wts, start)
# Ocean mascons are dropped rather than averaged into a coastal basin: GSFC
# codes them 90 and they hold ocean bottom pressure, not land storage.
gvals = gs.to_numpy().copy()
gvals[:, ~terrestrial(geo)] = np.nan
gout = np.full((len(gs), n), np.nan)
for t in range(len(gs)):
    v = gvals[t][gm]
    ok = np.isfinite(v)
    num = np.bincount(gb, weights=np.where(ok, v, 0.0) * gw, minlength=n)
    den = np.bincount(gb, weights=gw * ok, minlength=n)
    np.divide(num, den, out=gout[t], where=den > 0)
save("gsfc", gs.index, gout)
prov["gsfc"] = {"file": "gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5",
                "units_in_file": "cm", "grid": "native mascons, ~12,400 km2",
                "n_months_in_file": int(len(gs))}

# ------------------------------------------------------------------ predictors
print("GLDAS Noah 0.25 deg")
files = sorted(glob.glob(str(rg.RAW / "gldas" / "noah" / "*.nc4")))
print(f"  {len(files)} monthly files")
wg = None
sm_rows, sn_rows, pr_rows, stamps = [], [], [], []
SOIL = ["SoilMoi0_10cm_inst", "SoilMoi10_40cm_inst",
        "SoilMoi40_100cm_inst", "SoilMoi100_200cm_inst"]
for fn in files:
    with xr.open_dataset(fn, engine="netcdf4") as d:
        if wg is None:
            wg = rg.GridWeights(braster, d["lat"].values, d["lon"].values, n)
        sm = sum(np.asarray(d[v].values[0], dtype="float64") for v in SOIL)
        sn = (np.asarray(d["SWE_inst"].values[0], dtype="float64")
              + np.asarray(d["CanopInt_inst"].values[0], dtype="float64"))
        days = pd.Period(pd.Timestamp(d["time"].values[0]), freq="M").days_in_month
        pr = np.asarray(d["Rainf_f_tavg"].values[0], dtype="float64") * SEC_PER_DAY * days
        stamps.append(pd.Timestamp(d["time"].values[0]))
    sm_rows.append(sm)
    sn_rows.append(sn)
    pr_rows.append(pr)
sm_b = save("sm", stamps, wg.means(np.array(sm_rows)))
sn_b = save("snowcanopy", stamps, wg.means(np.array(sn_rows)))
gldas_pr = save("precip_gldas", stamps, wg.means(np.array(pr_rows)))
prov["gldas_noah"] = {"collection": "GLDAS_NOAH025_M 2.1", "grid": "0.25 deg",
                      "soil": SOIL, "snow_canopy": ["SWE_inst", "CanopInt_inst"],
                      "precip": "Rainf_f_tavg, kg m-2 s-1 converted to mm per month",
                      "n_months": len(files)}
del sm_rows, sn_rows, pr_rows

print("CHIRPS 0.05 deg")
cfiles = sorted(glob.glob(str(rg.RAW / "chirps" / "chirps-v2.0.*.monthly.nc")))
wc, frames = None, []
for fn in cfiles:
    with xr.open_dataset(fn) as d:
        if wc is None:
            wc = rg.GridWeights(braster, d["latitude"].values, d["longitude"].values, n)
        v = np.asarray(d["precip"].values, dtype="float32")
        v[v < -100] = np.nan
        frames.append(pd.DataFrame(wc.means(v), index=to_month(d["time"].values), columns=cols))
chirps = pd.concat(frames).sort_index()
chirps.to_parquet(RED / "series_precip_chirps.parquet")
print(f"  chirps: {len(chirps)} months, "
      f"{int(np.isfinite(chirps.to_numpy()).any(axis=0).sum())}/{n} basins with data")
prov["chirps"] = {"product": "CHIRPS v2.0 global monthly", "grid": "0.05 deg",
                  "coverage": "50S to 50N", "units": "mm per month",
                  "n_months": int(len(chirps))}

# CHIRPS stops at 50 degrees, so the higher latitudes take the GLDAS forcing
# instead. Which source a basin used travels with the basin rather than being
# averaged away.
have_chirps = np.isfinite(chirps.to_numpy()).sum(axis=0) > 12
src = np.where(have_chirps, "chirps", "gldas")
idx = chirps.index.intersection(gldas_pr.index)
precip = gldas_pr.loc[idx].copy()
precip.loc[:, have_chirps] = chirps.loc[idx].to_numpy()[:, have_chirps]
precip.to_parquet(RED / "series_precip.parquet")
pd.DataFrame({"HYBAS_ID": cols, "precip_source": src}).to_parquet(RED / "precip_source.parquet")
print(f"  combined precip: {len(precip)} months, "
      f"{int((src == 'chirps').sum())} basins on CHIRPS, {int((src == 'gldas').sum())} on GLDAS")

json.dump(prov, open(RED / "sources.json", "w"), indent=2)
print("wrote", RED / "sources.json")
