"""Phase 2: inspect GSFC mascon file structure BEFORE using it."""
import numpy as np, xarray as xr, pandas as pd

NC = r"E:\Water\Oregan\analysis\raw\gsfc_mascons_halfdegree.nc"

ds = xr.open_dataset(NC, decode_times=False)
print("=== DIMS ===");  print(dict(ds.sizes))
print("\n=== COORDS ===")
for k, v in ds.coords.items():
    print(f"  {k}: {v.shape} {v.dtype}  attrs={dict(v.attrs)}")
print("\n=== DATA VARS ===")
for k, v in ds.data_vars.items():
    print(f"  {k}: dims={v.dims} shape={v.shape} dtype={v.dtype}")
    for ak, av in v.attrs.items():
        print(f"       {ak} = {av}")
print("\n=== GLOBAL ATTRS ===")
for k, v in ds.attrs.items():
    print(f"  {k} = {str(v)[:400]}")

# axis values
for name in ("lat", "lon", "time", "months", "time_bounds"):
    if name in ds.variables:
        a = np.asarray(ds[name].values)
        print(f"\n--- {name}: shape {a.shape} first5 {a.ravel()[:5]} last5 {a.ravel()[-5:]}")
        if a.ndim == 1 and a.size > 2:
            d = np.diff(a.ravel())
            print(f"    spacing: min {d.min()} max {d.max()}")
