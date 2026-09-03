"""Reconnaissance on the Arabian subset: mascon recovery, mask, units, gaps."""
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path

RAW = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd_halfdegree.nc")

# Buffered box so we can look at leakage across the coast; core box is the deliverable.
BUF = dict(lat=slice(8.0, 36.0), lon=slice(30.0, 64.0))

ds = xr.open_dataset(RAW)
sub = ds.sel(**BUF)
print("buffered subset dims:", dict(sub.sizes))
lwe = sub["lwe_thickness"].load()
lm = sub["land_mask"].load()

print("land_mask unique values:", np.unique(lm.values))
print("n land cells (buffered):", int((lm.values == 1).sum()), "of", lm.size)

core = sub.sel(lat=slice(12.0, 32.0), lon=slice(34.0, 60.0))
print("core dims:", dict(core.sizes))
print("core n land cells:", int((core['land_mask'].values == 1).sum()), "of", core['land_mask'].size)

# ---- recover 1-degree mascon identity by grouping identical time series
v = lwe.values  # (t, lat, lon)
nt, ny, nx = v.shape
flat = v.reshape(nt, -1).T  # (cells, t)
# hash each row exactly
keys = [r.tobytes() for r in np.ascontiguousarray(flat)]
uniq, inv, counts = np.unique(np.array(keys, dtype=object), return_inverse=True, return_counts=True)
print(f"\nBuffered box: {flat.shape[0]} half-degree cells -> {len(uniq)} unique time series")
print("group size histogram:", dict(zip(*np.unique(counts, return_counts=True))))

# does any group mix land and ocean cells?
lmf = lm.values.reshape(-1)
mix = 0
for g in range(len(uniq)):
    sel = inv == g
    if len(np.unique(lmf[sel])) > 1:
        mix += 1
print("groups mixing land_mask=0 and =1 cells:", mix)

# spatial extent of a few groups
lat2d, lon2d = np.meshgrid(sub.lat.values, sub.lon.values, indexing="ij")
lat_f, lon_f = lat2d.reshape(-1), lon2d.reshape(-1)
print("\nSample groups (land only):")
shown = 0
for g in range(len(uniq)):
    sel = inv == g
    if lmf[sel][0] != 1:
        continue
    print(f"  g{g}: n={sel.sum()} lat {lat_f[sel].min()}-{lat_f[sel].max()} lon {lon_f[sel].min()}-{lon_f[sel].max()}")
    shown += 1
    if shown >= 8:
        break

# ---- time axis / bounds
tb = sub["time_bounds"].load()
t = pd.to_datetime(sub.time.values)
print("\nfirst 5 time bounds:")
for i in range(5):
    print("  ", t[i], pd.to_datetime(tb.values[i, 0]), "->", pd.to_datetime(tb.values[i, 1]))
# duplicate month 2018-11
per = t.to_period("M")
dup = per[per.duplicated(keep=False)]
print("duplicate-month timestamps:", [str(x) for x in t[per.isin(dup.unique())]])
idx = np.where(per.isin(dup.unique()))[0]
for i in idx:
    print("  ", t[i], pd.to_datetime(tb.values[i, 0]), "->", pd.to_datetime(tb.values[i, 1]))

# ---- baseline check: mean over 2004-2009 should be ~0
m = (t >= "2004-01-01") & (t < "2010-01-01")
land = lm.values == 1
base = v[m][:, land].mean(axis=0)
print(f"\n2004-2009 mean over land cells: mean={base.mean():.4f} cm, "
      f"max|.|={np.abs(base).max():.4f} cm  (should be ~0 if baseline is that window)")

# ---- magnitude sanity in core
cv = core["lwe_thickness"].values
clm = core["land_mask"].values == 1
print(f"\ncore land cells: {clm.sum()}")
print(f"core land lwe range: {cv[:, clm].min():.2f} .. {cv[:, clm].max():.2f} cm")
print(f"core OCEAN cells lwe range: {cv[:, ~clm].min():.2f} .. {cv[:, ~clm].max():.2f} cm")
print(f"core land std (time) median: {np.median(cv[:, clm].std(axis=0)):.2f} cm")
print(f"core ocean std (time) median: {np.median(cv[:, ~clm].std(axis=0)):.2f} cm")
