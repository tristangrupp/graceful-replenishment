import h5py, numpy as np, pandas as pd
from pathlib import Path
P = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
f = h5py.File(P, "r")
g = lambda k: np.asarray(f[k][()]).squeeze()

lat, lon = g("mascon/lat_center"), g("mascon/lon_center")
latsp, lonsp = g("mascon/lat_span"), g("mascon/lon_span")
area = g("mascon/area_km2"); labels = g("mascon/labels")
loc = g("mascon/location"); basin = g("mascon/basin"); elev = g("mascon/elev_flag")
print("location value counts:", dict(zip(*np.unique(loc, return_counts=True))))

lon180 = ((lon + 180) % 360) - 180
box = (lat >= 12) & (lat <= 32) & (lon180 >= 34) & (lon180 <= 60)
print("\nmascons with center in box 12-32N,34-60E:", box.sum())
for lv in np.unique(loc[box]):
    print(f"  location={lv:.0f} n={int((loc[box]==lv).sum())}")
land = box & (loc == 80)
print("LAND mascons in box:", land.sum())
print("lat_span range:", latsp[land].min(), latsp[land].max())
print("lon_span range:", lonsp[land].min(), lonsp[land].max())
print("area_km2 range:", area[land].min(), area[land].max())
print("labels contiguous?", np.array_equal(labels, np.arange(1, len(labels)+1)))
print("distinct basins in box land:", len(np.unique(basin[land])), sorted(np.unique(basin[land]))[:20])
print("elev_flag counts:", dict(zip(*np.unique(elev[land], return_counts=True))))

# time
rd_mid = g("time/ref_days_middle"); rd_f = g("time/ref_days_first"); rd_l = g("time/ref_days_last")
ydp = np.asarray(f["time/yyyy_doy_yrplot_middle"][()])
epoch = pd.Timestamp("2002-01-01")
tm = epoch + pd.to_timedelta(rd_mid - 1, "D")
tf = epoch + pd.to_timedelta(rd_f - 1, "D")
tl = epoch + pd.to_timedelta(rd_l - 1, "D")
print("\ntime middle first/last:", tm[0], tm[-1], "n=", len(tm))
print("yrplot first/last:", ydp[2,0], ydp[2,-1])
print("cross-check vs netCDF time (2002-04-18 .. 2026-03-17):", tm[0].date(), tm[-1].date())
per = pd.PeriodIndex(tm, freq="M")
print("dup months:", [str(p) for p in per[per.duplicated(keep=False)]])

idx = np.where(land)[0]
cm = f["solution/cmwe"][:, :]
noise = f["uncertainty/noise_2sigma"][:, :]
lk2 = np.asarray(f["uncertainty/leakage_2sigma"][()]).squeeze()
lkt = np.asarray(f["uncertainty/leakage_trend"][()]).squeeze()
sub = cm[idx]; nsub = noise[idx]
print("\ncmwe (box land): min %.2f max %.2f" % (sub.min(), sub.max()))
print("temporal std per mascon: median %.2f cm, range %.2f-%.2f" % (
    np.median(sub.std(axis=1)), sub.std(axis=1).min(), sub.std(axis=1).max()))
print("noise_2sigma: median %.2f cm, range %.2f-%.2f" % (
    np.median(nsub), nsub.min(), nsub.max()))
print("leakage_2sigma: median %.2f cm, range %.2f-%.2f" % (
    np.median(lk2[idx]), lk2[idx].min(), lk2[idx].max()))
print("leakage_trend: median %.4f cm/yr, range %.3f-%.3f" % (
    np.median(lkt[idx]), lkt[idx].min(), lkt[idx].max()))

# baseline check
m = (tm >= "2004-01-01") & (tm < "2010-01-01")
print("\n2004-2009 mean per mascon: max|.| = %.6f cm" % np.abs(sub[:, m].mean(axis=1)).max())

# quick trend by simple OLS on decimal year, to sanity check magnitude
yr = ydp[2]
A = np.vstack([np.ones_like(yr), yr - yr.mean()]).T
c, *_ = np.linalg.lstsq(A, sub.T, rcond=None)
tr = c[1]
print("\nquick OLS trend (no harmonics) cm/yr: min %.3f max %.3f median %.3f" % (tr.min(), tr.max(), np.median(tr)))
ordr = np.argsort(tr)
print("10 most negative mascons (lat, lon, trend cm/yr):")
for j in ordr[:10]:
    print(f"   id={int(labels[idx[j]]):6d} lat={lat[idx[j]]:6.2f} lon={lon180[idx[j]]:6.2f} trend={tr[j]:7.3f}")
f.close()
