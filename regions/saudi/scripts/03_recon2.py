"""Is the half-degree grid a block map of 1-arc-deg mascons, or interpolated?"""
import numpy as np
import pandas as pd
import xarray as xr
from pathlib import Path

RAW = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd_halfdegree.nc")
ds = xr.open_dataset(RAW)
sub = ds.sel(lat=slice(8.0, 36.0), lon=slice(30.0, 64.0))
v = sub["lwe_thickness"].load().values
lm = sub["land_mask"].load().values
nt, ny, nx = v.shape
lat, lon = sub.lat.values, sub.lon.values

flat = np.ascontiguousarray(v.reshape(nt, -1).T)
lmf = lm.reshape(-1)
keys = np.array([r.tobytes() for r in flat], dtype=object)

for label, mask in [("LAND", lmf == 1), ("OCEAN", lmf == 0)]:
    k = keys[mask]
    uniq, inv, counts = np.unique(k, return_inverse=True, return_counts=True)
    hist = dict(zip(*np.unique(counts, return_counts=True)))
    print(f"{label}: {mask.sum()} cells -> {len(uniq)} unique series; group-size hist {hist}")

# For land: map group id back to grid and print a small window to see block structure
kl = keys.copy()
uniq, inv = np.unique(kl, return_inverse=True)
gid = inv.reshape(ny, nx).astype(float)
gid[lm == 0] = np.nan

# print a 12x14 window over central Saudi (lat 22-28, lon 42-49)
iy = np.where((lat >= 22) & (lat <= 28))[0]
ix = np.where((lon >= 42) & (lon <= 49))[0]
# relabel locally for readability
win = gid[np.ix_(iy, ix)]
uu = {v_: i for i, v_ in enumerate(sorted(set(win[~np.isnan(win)])))}
print("\nGroup-id map over central Saudi (rows=lat descending, cols=lon):")
print("lon:", " ".join(f"{l:5.2f}" for l in lon[ix]))
for r in reversed(range(len(iy))):
    row = " ".join("  ." if np.isnan(x) else f"{uu[x]:4d}" for x in win[r])
    print(f"{lat[iy][r]:6.2f} {row}")

# neighbour correlation & difference magnitude (are neighbours identical or just similar?)
d_lon = np.abs(np.diff(v, axis=2))
d_lat = np.abs(np.diff(v, axis=1))
landpair_lon = (lm[:, :-1] == 1) & (lm[:, 1:] == 1)
landpair_lat = (lm[:-1, :] == 1) & (lm[1:, :] == 1)
print(f"\nmedian |diff| between E-W land neighbours: {np.median(d_lon[:, landpair_lon]):.4f} cm")
print(f"median |diff| between N-S land neighbours: {np.median(d_lat[:, landpair_lat]):.4f} cm")
print(f"median temporal std of land cells:         {np.median(v[:, lm==1].std(axis=0)):.4f} cm")
print(f"fraction of E-W land neighbour pairs identical: "
      f"{(d_lon[:, landpair_lon].max(axis=0)==0).mean():.3f}")

# effective spatial DOF: singular value spectrum of the core land block
core_mask = (lat[:,None] >= 12) & (lat[:,None] <= 32) & (lon[None,:] >= 34) & (lon[None,:] <= 60) & (lm==1)
X = v[:, core_mask]          # (t, cells)
Xc = X - X.mean(axis=0)
u, s, vt = np.linalg.svd(Xc, full_matrices=False)
var = s**2 / (s**2).sum()
print(f"\ncore land cells: {core_mask.sum()}; variance explained by first modes:")
print("  " + " ".join(f"PC{i+1}={var[i]*100:.1f}%" for i in range(8)))
print(f"  cumulative to 95%: {int(np.searchsorted(np.cumsum(var), 0.95))+1} modes")
print(f"  cumulative to 99%: {int(np.searchsorted(np.cumsum(var), 0.99))+1} modes")
