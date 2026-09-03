"""Thorough inspection of the GSFC mascon netCDF. Writes dataset_inventory.md."""
import sys
from pathlib import Path

import numpy as np
import xarray as xr
import netCDF4

RAW = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd_halfdegree.nc")
OUT = Path(r"E:\Water\Saudi\processed\dataset_inventory.md")

lines = []
def w(s=""):
    lines.append(str(s))
    print(s)

w(f"# GSFC mascon dataset inventory")
w()
w(f"- File: `{RAW}`")
w(f"- Size: {RAW.stat().st_size:,} bytes")
w(f"- Source URL: https://earth.gsfc.nasa.gov/sites/default/files/geo/{RAW.name}")
w()

# --- raw netCDF4 view first (no xarray decoding), so we see fill values etc.
w("## Raw netCDF4 view (undecoded)")
w()
nc = netCDF4.Dataset(RAW)
w(f"- netCDF format: `{nc.data_model}`")
w(f"- Groups: {list(nc.groups)}")
w()
w("### Global attributes")
w()
w("```")
for k in nc.ncattrs():
    v = nc.getncattr(k)
    sv = str(v)
    if len(sv) > 1500:
        sv = sv[:1500] + " ...[truncated]"
    w(f"{k}: {sv}")
w("```")
w()
w("### Dimensions")
w()
w("| dim | size | unlimited |")
w("|---|---|---|")
for k, d in nc.dimensions.items():
    w(f"| {k} | {len(d)} | {d.isunlimited()} |")
w()
w("### Variables")
w()
w("| name | dims | shape | dtype | attributes |")
w("|---|---|---|---|---|")
for k, v in nc.variables.items():
    attrs = {a: v.getncattr(a) for a in v.ncattrs()}
    sa = "; ".join(f"{a}={attrs[a]!r}" for a in attrs)
    if len(sa) > 500:
        sa = sa[:500] + " ...[trunc]"
    w(f"| `{k}` | {v.dimensions} | {v.shape} | {v.dtype} | {sa} |")
w()

# per-variable numeric summary from raw
w("### Raw value ranges (undecoded, ignoring nothing)")
w()
w("```")
for k, v in nc.variables.items():
    try:
        v.set_auto_mask(False)
        arr = v[:]
        a = np.asarray(arr).ravel()
        if a.dtype.kind in "fiu":
            w(f"{k:24s} min={np.nanmin(a):>16.6g} max={np.nanmax(a):>16.6g} "
              f"n_nan={int(np.isnan(a).sum()) if a.dtype.kind=='f' else 0} n={a.size}")
        else:
            w(f"{k:24s} dtype={a.dtype} (non-numeric) n={a.size}")
    except Exception as e:
        w(f"{k:24s} ERROR: {e}")
w("```")
w()
nc.close()

# --- xarray view
w("## xarray view")
w()
for decode in (True, False):
    try:
        ds = xr.open_dataset(RAW, decode_times=decode)
        w(f"### decode_times={decode}")
        w()
        w("```")
        w(repr(ds))
        w("```")
        w()
        if decode:
            DS = ds
        else:
            ds.close()
    except Exception as e:
        w(f"decode_times={decode} FAILED: {e}")
        w()

ds = xr.open_dataset(RAW)
w("## Coordinate conventions")
w()
for c in ds.coords:
    v = ds[c].values
    w(f"- `{c}`: n={v.size}, first={v[0]}, last={v[-1]}, dtype={v.dtype}")
    if np.issubdtype(v.dtype, np.number) and v.size > 1:
        d = np.diff(v.astype("float64"))
        w(f"    step: min={d.min():.6g} max={d.max():.6g} (uniform={np.allclose(d, d[0])})")
w()

for name in ("lon", "longitude"):
    if name in ds.coords:
        lo = ds[name].values
        w(f"- Longitude convention: **{'0-360' if lo.min() >= 0 and lo.max() > 180 else '-180/180'}** "
          f"(min={lo.min()}, max={lo.max()})")
w()

# time axis details
tname = None
for cand in ("time", "Time", "months"):
    if cand in ds.dims:
        tname = cand
if tname:
    import pandas as pd
    t = ds[tname].values
    w("## Time axis")
    w()
    w(f"- dim `{tname}`: n={len(t)}")
    try:
        ts = pd.to_datetime(t)
        w(f"- range: {ts.min()} .. {ts.max()}")
        ym = ts.to_period("M")
        vc = ym.value_counts().sort_index()
        dupes = vc[vc > 1]
        w(f"- distinct calendar months: {len(vc)}; months with >1 solution: {len(dupes)}")
        if len(dupes):
            w(f"- duplicated months: {list(map(str, dupes.index))}")
        # missing months
        full = pd.period_range(ym.min(), ym.max(), freq="M")
        missing = sorted(set(full) - set(ym))
        w(f"- expected months in span: {len(full)}; missing: {len(missing)}")
        w(f"- missing month list: {[str(m) for m in missing]}")
    except Exception as e:
        w(f"- could not convert to datetime: {e}")
    w()

Path(OUT).parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nWROTE {OUT}")
