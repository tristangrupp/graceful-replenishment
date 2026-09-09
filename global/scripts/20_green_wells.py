"""Green experiment, step 1: put every product and predictor at every well.

The red experiment could run with no outside data because it only detected
failure. Showing that a downscaled value is right needs an external reference,
and this is that reference: annual groundwater levels from Jasechko et al.
(2024), the open subset of the compilation behind the Nature paper.

What comes out is one table per well of annual anomalies, 2002 to 2022:

    level        the well itself, sign flipped so that up means more water
    tws_*        each product's total water storage at the well's cell
    gws_*        the same minus GLDAS soil moisture, snow and canopy,
                 aggregated to that product's own cell
    precip, sm, snow   the predictor fields, for the ablation

Groundwater level is a head, not a storage. Converting one to the other needs a
specific yield, which is not known per well and is the largest free parameter in
this kind of comparison. Nothing here converts. Every score is a correlation or
a sign, and those are unchanged by any positive scale factor, so the specific
yield never enters.
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
from gsfc_grid import CM_TO_MM  # noqa: E402

GREEN = rg.ROOT / "green"
GREEN.mkdir(parents=True, exist_ok=True)
WELLS = (rg.RAW / "wells" / "Jasechko_et_al_2024_GroundwaterLevelData"
         / "AnnualDepthToGroundwater.csv")
SEDA = rg.RAW / "downscaled" / "GRACE-SeDA_v1_2002_2022.nc"
LIKU = rg.RAW / "downscaled" / "LiKusche_JPL_mascon_downscaled-v2.0.nc"
JPL = rg.RAW / "jpl_mascon" / "jpl_mascon_rl0603v04_cri.nc"
JPL61 = rg.RAW / "jpl_mascon" / "jpl_mascon_rl0601v03_cri.nc"

Y0, Y1 = 2002, 2022
MIN_YEARS = 10
SEC_PER_DAY = 86400.0

# ------------------------------------------------------------------- the wells
d = pd.read_csv(WELLS)
d = d[(d.IntegerYear >= Y0) & (d.IntegerYear <= Y1)]
n_year = d.groupby("StnID")["IntegerYear"].nunique()
keep = n_year[n_year >= MIN_YEARS].index
d = d[d.StnID.isin(keep)]
sites = (d.groupby("StnID")[["Lat", "Lon"]].first()
         .join(n_year.rename("n_years")).reset_index())
print(f"{len(sites):,} wells with at least {MIN_YEARS} annual values in "
      f"{Y0}..{Y1}, {len(d):,} well-years")

# Depth to water increases as the water table falls, so the sign is flipped once
# here and never again. Everything downstream reads "up is more water".
lvl = d.pivot_table(index="IntegerYear", columns="StnID", values="DepthToWater_m",
                    aggfunc="mean")
lvl = -lvl
lvl = lvl.reindex(index=range(Y0, Y1 + 1), columns=sites.StnID.to_numpy())
lvl = lvl - lvl.mean()
lvl.to_parquet(GREEN / "well_level_anomaly_m.parquet")
sites.to_parquet(GREEN / "well_sites.parquet")


def cell_index(lat_ax, lon_ax, lat, lon):
    """Index of the cell containing each point, on a regular grid.

    Located from the axis's own spacing and origin rather than by nearest
    neighbour, so a point on a cell edge always falls the same way.
    """
    lat_ax = np.asarray(lat_ax, dtype="float64")
    lon_ax = np.asarray(lon_ax, dtype="float64")
    dlat = round(abs(float(lat_ax[-1] - lat_ax[0])) / (len(lat_ax) - 1), 6)
    dlon = round(abs(float(lon_ax[-1] - lon_ax[0])) / (len(lon_ax) - 1), 6)
    lat0 = round(float(lat_ax.min()) - dlat / 2, 6)
    lon0 = round(float(lon_ax.min()) - dlon / 2, 6)
    iy = np.floor((np.asarray(lat) - lat0) / dlat).astype(np.int64)
    ix = np.floor(np.mod(np.asarray(lon) - lon0, 360.0) / dlon).astype(np.int64)
    if lat_ax[0] > lat_ax[-1]:
        iy = len(lat_ax) - 1 - iy
    if lon_ax[0] > lon_ax[-1]:
        ix = len(lon_ax) - 1 - ix
    ok = (iy >= 0) & (iy < len(lat_ax)) & (ix >= 0) & (ix < len(lon_ax))
    return np.clip(iy, 0, len(lat_ax) - 1), np.clip(ix, 0, len(lon_ax) - 1), ok, (dlat, dlon)


# ---------------------------------------------------------------- GLDAS Noah
print("GLDAS Noah, the land surface term and the predictors")
SOIL = ["SoilMoi0_10cm_inst", "SoilMoi10_40cm_inst",
        "SoilMoi40_100cm_inst", "SoilMoi100_200cm_inst"]
files = sorted(glob.glob(str(rg.RAW / "gldas" / "noah" / "*.nc4")))
glat = glon = None
lsm_rows, pr_rows, sm_rows, sn_rows, stamps = [], [], [], [], []
for fn in files:
    with xr.open_dataset(fn, engine="netcdf4") as g:
        if glat is None:
            glat, glon = g["lat"].values, g["lon"].values
        sm = sum(np.asarray(g[v].values[0], dtype="float32") for v in SOIL)
        sn = (np.asarray(g["SWE_inst"].values[0], dtype="float32")
              + np.asarray(g["CanopInt_inst"].values[0], dtype="float32"))
        ts = pd.Timestamp(g["time"].values[0])
        days = pd.Period(ts, freq="M").days_in_month
        pr = np.asarray(g["Rainf_f_tavg"].values[0], dtype="float32") * SEC_PER_DAY * days
    lsm_rows.append(sm + sn)
    sm_rows.append(sm)
    sn_rows.append(sn)
    pr_rows.append(pr)
    stamps.append(ts.to_period("M").to_timestamp())
LSM = np.array(lsm_rows)
gtime = pd.DatetimeIndex(stamps)
print(f"  {len(files)} months, grid {len(glat)}x{len(glon)}")

giy, gix, gok, _ = cell_index(glat, glon, sites.Lat.values, sites.Lon.values)
print(f"  {int(gok.sum()):,} of {len(sites):,} wells inside the GLDAS domain")


def annual(cube_at_wells, times):
    """(n_year, n_well) annual means of a (n_month, n_well) block.

    Columns are station ids, not positions. Everything downstream joins these
    frames to the well levels by column, and a positional column would line up
    silently against the wrong well.
    """
    df = pd.DataFrame(cube_at_wells, index=pd.DatetimeIndex(times),
                      columns=sites.StnID.to_numpy())
    a = df.groupby(df.index.year).mean()
    a = a.reindex(range(Y0, Y1 + 1))
    return a - a.mean()


pred = {}
for name, cube in (("sm", np.array(sm_rows)), ("snow", np.array(sn_rows)),
                   ("precip", np.array(pr_rows))):
    at = cube[:, giy, gix].astype("float64")
    at[:, ~gok] = np.nan
    if name == "precip":
        # Storage integrates flux, so the term a level series can answer to is
        # the running total of the anomaly, not the month's rain.
        m = pd.DataFrame(at, index=gtime, columns=sites.StnID.to_numpy())
        clim = m.groupby(m.index.month).transform("mean")
        acc = (m - clim).cumsum()
        a = acc.groupby(acc.index.year).mean().reindex(range(Y0, Y1 + 1))
        pred["precip_accum"] = a - a.mean()
    if name == "precip":
        # The raw climatology, kept because the anomaly cannot say how wet a
        # well is and the wetness split needs to know.
        pd.DataFrame({"StnID": sites.StnID.to_numpy(),
                      "mean_precip_mm_yr": np.nanmean(at, axis=0) * 12.0}
                     ).to_parquet(GREEN / "well_mean_precip.parquet")
    pred[name] = annual(at, gtime)
del sm_rows, sn_rows, pr_rows, lsm_rows

# ------------------------------------------------------------------- products
def lsm_on(lat_ax, lon_ax, iy, ix, ok):
    """GLDAS soil moisture, snow and canopy averaged onto a product cell.

    A 0.5 degree product cell holds four GLDAS cells, and averaging them is the
    only way the subtraction stays on one footprint. At 0.25 degrees the two
    grids coincide and the average is over one cell.
    """
    dlat = round(abs(float(lat_ax[-1] - lat_ax[0])) / (len(lat_ax) - 1), 6)
    dlon = round(abs(float(lon_ax[-1] - lon_ax[0])) / (len(lon_ax) - 1), 6)
    gdlat = round(abs(float(glat[-1] - glat[0])) / (len(glat) - 1), 6)
    gdlon = round(abs(float(glon[-1] - glon[0])) / (len(glon) - 1), 6)
    ky, kx = int(round(dlat / gdlat)), int(round(dlon / gdlon))
    out = np.zeros((LSM.shape[0], len(iy)), dtype="float64")
    wsum = np.zeros(len(iy))
    for a in range(ky):
        for b in range(kx):
            # centre of each sub-cell of the product cell, then its GLDAS cell
            plat = np.asarray(lat_ax)[iy] + (a - (ky - 1) / 2) * gdlat
            plon = np.asarray(lon_ax)[ix] + (b - (kx - 1) / 2) * gdlon
            jy, jx, jok, _ = cell_index(glat, glon, plat, ((plon + 180) % 360) - 180)
            v = LSM[:, jy, jx].astype("float64")
            w = np.cos(np.deg2rad(plat)) * jok * ok
            v[:, ~(jok & ok)] = 0.0
            out += v * w
            wsum += w
    return np.divide(out, wsum, out=np.full_like(out, np.nan), where=wsum > 0)


def product_at_wells(name, path, var, lat_name, lon_name, scale, time_fn,
                     mask_name=None, mask_t=False):
    ds = xr.open_dataset(path)
    lat_ax, lon_ax = ds[lat_name].values, ds[lon_name].values
    iy, ix, ok, _ = cell_index(lat_ax, lon_ax, sites.Lat.values, sites.Lon.values)
    cube = ds[var].transpose("time", lat_name, lon_name).values
    at = np.asarray(cube[:, iy, ix], dtype="float64") * scale
    if mask_name is not None:
        m = np.asarray(ds[mask_name].values)
        if mask_t:
            m = m.T
        at[:, ~(m[iy, ix] > 0)] = np.nan
    at[:, ~ok] = np.nan
    t = time_fn(ds)
    tws = pd.DataFrame(at, index=t)
    tws = tws.groupby(tws.index.to_period("M").to_timestamp()).mean()

    lsm = pd.DataFrame(lsm_on(lat_ax, lon_ax, iy, ix, ok), index=gtime)
    common = tws.index.intersection(lsm.index)
    gws = ((tws.loc[common] - tws.loc[common].mean())
           - (lsm.loc[common] - lsm.loc[common].mean()))
    print(f"  {name}: {len(tws)} months, {len(common)} shared with GLDAS, "
          f"{int(np.isfinite(tws.to_numpy()).any(axis=0).sum()):,} wells with a value")
    annual(tws.to_numpy(), tws.index).to_parquet(GREEN / f"well_tws_{name}.parquet")
    annual(gws.to_numpy(), gws.index).to_parquet(GREEN / f"well_gws_{name}.parquet")
    del cube, at


def mjd(ds):
    return pd.to_datetime("1858-11-17") + pd.to_timedelta(
        np.asarray(ds["time"].values, dtype="float64"), unit="D")


def decimal_year(ds):
    dy = np.asarray(ds["time"].values, dtype="float64")
    yr = np.floor(dy).astype(int)
    mo = np.clip((np.floor((dy - yr) * 12) + 1).astype(int), 1, 12)
    return pd.to_datetime([f"{y}-{m:02d}-15" for y, m in zip(yr, mo)])


print("products at the wells")
product_at_wells("seda", SEDA, "twsa", "latitude", "longitude", 1.0, mjd,
                 mask_name="mask", mask_t=True)
product_at_wells("liku", LIKU, "JPL_EWH_downscaled", "lat", "lon", CM_TO_MM,
                 decimal_year)
product_at_wells("jpl", JPL, "lwe_thickness", "lat", "lon", CM_TO_MM,
                 lambda ds: pd.to_datetime(ds["time"].values), mask_name="land_mask")
product_at_wells("jpl61", JPL61, "lwe_thickness", "lat", "lon", CM_TO_MM,
                 lambda ds: pd.to_datetime(ds["time"].values), mask_name="land_mask")

for k, v in pred.items():
    v.to_parquet(GREEN / f"well_pred_{k}.parquet")

json.dump({"wells_file": WELLS.name, "doi": "10.5281/zenodo.10003697",
           "source": "Jasechko et al. (2024), annual depth to water, open subset",
           "window": [Y0, Y1], "min_years": MIN_YEARS,
           "n_wells": int(len(sites)), "n_well_years": int(len(d)),
           "sign": "depth to water negated, so up is more water",
           "note": "no specific yield is applied anywhere; every score is scale free"},
          open(GREEN / "wells_sources.json", "w"), indent=2)
print("wrote", GREEN)
