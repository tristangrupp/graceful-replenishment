"""Does the global pipeline reproduce the regional Arabia run?

Different code path: the regional work subset GLDAS through OPeNDAP and averaged
cells inside each mascon's lat/lon box; the global work downloads whole granules
and assigns every cell to a mascon by searchsorted. If the two disagree on the
same mascons and months, one of them is wrong.
"""

import sys
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"E:\Water\_shared")
sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import attribution as A
from gsfc_grid import CM_TO_MM, cell_to_mascon, load_geometry

geo = load_geometry()

# regional: Saudi's own GLDAS subset, averaged the way script 11 did it
meta = pd.read_csv(r"E:\Water\Saudi\signals\mascon_metadata.csv")
reg = xr.open_dataset(r"E:\Water\Saudi\processed\gldas_noah_monthly.nc")
non_gw = (A._NON_GW_STORAGE["noah"](reg) * CM_TO_MM).transpose("time", "lat", "lon")
lat, lon = non_gw["lat"].values, non_gw["lon"].values
vals = non_gw.values
reg_series = {}
for _, r in meta.iterrows():
    my = (lat >= r.lat_center - r.lat_span_deg / 2) & (lat < r.lat_center + r.lat_span_deg / 2)
    mx = (lon >= r.lon_center - r.lon_span_deg / 2) & (lon < r.lon_center + r.lon_span_deg / 2)
    if not (my.sum() and mx.sum()):
        continue
    blk = vals[:, my, :][:, :, mx]
    w = np.broadcast_to(np.cos(np.deg2rad(lat[my]))[None, :, None], blk.shape).copy()
    w[~np.isfinite(blk)] = 0.0
    tot = w.sum(axis=(1, 2))
    with np.errstate(invalid="ignore"):
        reg_series[int(r.mascon_id) - 1] = np.nansum(blk * w, axis=(1, 2)) / np.where(tot > 0, tot, np.nan)
reg_df = pd.DataFrame(reg_series, index=pd.to_datetime(reg["time"].values))

# global: whole granules, searchsorted assignment
import glob
files = sorted(glob.glob(r"E:\Water\Global\raw\gldas\noah\*.nc4"))
rows, stamps, mapping, cosw = [], [], None, None
n_mas = len(geo)
for fn in files:
    with xr.open_dataset(fn, engine="netcdf4") as d:
        if mapping is None:
            la, lo = d["lat"].values, d["lon"].values
            mapping = cell_to_mascon(geo, la, lo).ravel()
            cosw = np.broadcast_to(np.cos(np.deg2rad(la))[:, None], (len(la), len(lo))).ravel()
        v = (A._NON_GW_STORAGE["noah"](d) * CM_TO_MM).transpose("time", "lat", "lon")
        x = np.asarray(v.values[0], dtype="float64").ravel()
        stamps.append(pd.Timestamp(d["time"].values[0]))
    ok = np.isfinite(x)
    num = np.bincount(mapping[ok], weights=(x * cosw)[ok], minlength=n_mas)
    den = np.bincount(mapping[ok], weights=cosw[ok], minlength=n_mas)
    rows.append(np.divide(num, den, out=np.full(n_mas, np.nan), where=den > 0))
glob_df = pd.DataFrame(np.array(rows), index=pd.DatetimeIndex(stamps)).sort_index()

ids = [c for c in reg_df.columns if c in glob_df.columns]
idx = reg_df.index.intersection(glob_df.index)
a, b = reg_df.loc[idx, ids], glob_df.loc[idx, ids]
d = (a - b).to_numpy()
print("NOTE: regional mascon_id is 1-based, global index is 0-based; aligned by -1")
print(f"{len(ids)} shared mascons, {len(idx)} shared months")
print(f"mean |difference| {np.nanmean(np.abs(d)):.4f} mm, max {np.nanmax(np.abs(d)):.4f} mm")
print(f"relative to the mean storage of {np.nanmean(a.to_numpy()):.1f} mm: "
      f"{100*np.nanmean(np.abs(d))/np.nanmean(a.to_numpy()):.4f}%")
worst = int(np.nanargmax(np.nanmax(np.abs(d), axis=0)))
print(f"worst mascon {ids[worst]}: regional {a.iloc[:, worst].mean():.2f} mm, "
      f"global {b.iloc[:, worst].mean():.2f} mm")
