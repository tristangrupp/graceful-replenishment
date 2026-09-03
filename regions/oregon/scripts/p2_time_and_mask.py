"""Read lon/lat/time/land_mask from the (still partial) GSFC file.

NetCDF3-classic stores fixed-size variables contiguously in declaration
order: lon, lat, time, land_mask, then the 528 MB lwe_thickness. So the
grid, the time axis and the land mask are all readable from the first
~12 MB, long before the bulk array arrives.
"""
import shutil, os
import numpy as np
import pandas as pd
from netCDF4 import Dataset

src = r"E:\Water\Oregan\analysis\tmp\parts\part00"
dst = r"E:\Water\Oregan\analysis\tmp\peek.nc"
shutil.copyfile(src, dst)
print("peek size", f"{os.path.getsize(dst):,}")

d = Dataset(dst)
for v in ("lon", "lat", "time", "land_mask", "lwe_thickness", "time_bounds"):
    if v in d.variables:
        var = d.variables[v]
        print(f"\n--- {v}: dims={var.dimensions} shape={var.shape} dtype={var.dtype}")
        for a in var.ncattrs():
            print(f"      @{a} = {getattr(var, a)}")

lon = d.variables["lon"][:]
lat = d.variables["lat"][:]
t = d.variables["time"][:]
print("\nlon:", lon[:3], "...", lon[-3:], " d=", np.diff(lon)[:3])
print("lat:", lat[:3], "...", lat[-3:], " d=", np.diff(lat)[:3])
print("time raw:", t[:5], "...", t[-5:])

tu = getattr(d.variables["time"], "units", "")
print("time units:", tu)

# decode
from netCDF4 import num2date
dt = num2date(t, tu, only_use_cftime_datetimes=False)
ts = pd.to_datetime([str(x) for x in dt])
print("\nfirst 5 dates:", list(ts[:5].astype(str)))
print("last  5 dates:", list(ts[-5:].astype(str)))

per = ts.to_period("M")
print("\nn solutions:", len(ts))
dups = per[per.duplicated(keep=False)]
print("months carrying >1 solution:", sorted(set(dups.astype(str))))
full = pd.period_range(per.min(), per.max(), freq="M")
missing = sorted(set(full) - set(per))
print(f"\nmissing calendar months: {len(missing)} of {len(full)}")
runs, cur = [], []
for m in full:
    if m in missing:
        cur.append(str(m))
    elif cur:
        runs.append(cur); cur = []
if cur:
    runs.append(cur)
for r in runs:
    print(f"   gap {r[0]} .. {r[-1]}  ({len(r)} months)")

lm = d.variables["land_mask"][:]
print("\nland_mask shape", lm.shape, "unique", np.unique(lm)[:10],
      "land frac", float((lm > 0).mean()))

np.savez(r"E:\Water\Oregan\analysis\processed\grace_axes.npz",
         lon=lon, lat=lat, time=t, land_mask=lm,
         dates=np.array([str(x) for x in ts]))
print("\nsaved grace_axes.npz")
d.close()
