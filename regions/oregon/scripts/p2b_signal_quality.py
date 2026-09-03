"""Phase 2b: rigorous GRACE signal quality + EMPIRICAL spatial independence.

Replaces the failed attempt to recover native 1-arc-degree mascon footprints
by hashing identical pixel time series. That does not work: the GSFC
half-degree product *interpolates* ("Land values estimated from land
1-arc-degree mascons"), so every one of the 447 land pixels in the box has a
slightly different series. Counting distinct series would have reported 447
independent mascons, which is exactly the mistake the analysis must avoid.

Instead independence is measured, three ways:
  1. correlation of pixel pairs as a function of separation distance
     -> empirical decorrelation length
  2. eigenvalue spectrum of the spatial covariance -> effective number of
     spatial degrees of freedom over the Oregon box
  3. a noise floor from the 3-point second difference, which for a smooth
     signal plus white noise of std sigma has std sqrt(6)*sigma
"""
import sys
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion.trend import _decimal_years, _design_matrix

NC = r"E:\Water\Oregan\analysis\raw\gsfc_mascons_halfdegree.nc"
P = r"E:\Water\Oregan\analysis\processed"
INV = r"E:\Water\Oregan\analysis\inventory"
OR_BOX = dict(lon0=-124.6, lon1=-116.4, lat0=41.9, lat1=46.3)
BUF = 3.0
OUT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


def sect(t):
    say("\n" + "=" * 74); say(t); say("=" * 74)


def main():
    ds = xr.open_dataset(NC)
    assert ds["lwe_thickness"].attrs["units"] == "cm"
    lwe = ds["lwe_thickness"] * 10.0            # -> mm
    land = ds["land_mask"]
    lwe = lwe.assign_coords(lon=(((lwe.lon + 180) % 360) - 180)).sortby("lon")
    land = land.assign_coords(lon=(((land.lon + 180) % 360) - 180)).sortby("lon")

    b = dict(lon0=OR_BOX["lon0"] - BUF, lon1=OR_BOX["lon1"] + BUF,
             lat0=OR_BOX["lat0"] - BUF, lat1=OR_BOX["lat1"] + BUF)
    sub = lwe.sel(lon=slice(b["lon0"], b["lon1"]), lat=slice(b["lat0"], b["lat1"])).load()
    lnd = land.sel(lon=slice(b["lon0"], b["lon1"]), lat=slice(b["lat0"], b["lat1"])).load()

    # calendar months; 2018-11 has two solutions -> average
    months = sub.time.values.astype("datetime64[M]").astype("datetime64[ns]")
    sub = sub.assign_coords(time=months).groupby("time").mean("time")
    per = pd.PeriodIndex(pd.to_datetime(sub.time.values), freq="M")

    latv, lonv = sub.lat.values, sub.lon.values
    arr = sub.values                                     # (t, lat, lon)
    nt = arr.shape[0]
    island = lnd.values > 0
    inbox = ((lonv[None, :] >= OR_BOX["lon0"]) & (lonv[None, :] <= OR_BOX["lon1"])
             & (latv[:, None] >= OR_BOX["lat0"]) & (latv[:, None] <= OR_BOX["lat1"]))

    # ---- deseasonalise + detrend every pixel ---------------------------
    x = _design_matrix(_decimal_years(sub.time))
    flat = arr.reshape(nt, -1)
    coef, *_ = np.linalg.lstsq(x, flat, rcond=None)
    anom = (flat - x @ coef).reshape(arr.shape)   # residual: interannual + noise

    # ---- 1. noise floor from 3-point second difference ------------------
    sect("1. NOISE FLOOR (3-point second difference, gap-aware)")
    idx = {p: i for i, p in enumerate(per)}
    trip = [(idx[p - 1], i, idx[p + 1]) for i, p in enumerate(per)
            if (p - 1) in idx and (p + 1) in idx]
    say(f"consecutive month triplets available: {len(trip)} of {len(per)}")
    a0 = np.array([t[0] for t in trip]); a1 = np.array([t[1] for t in trip])
    a2 = np.array([t[2] for t in trip])
    d2 = flat[a0] - 2 * flat[a1] + flat[a2]
    sigma_pix = np.std(d2, axis=0) / np.sqrt(6)
    say(f"per-pixel noise sigma (land): median {np.median(sigma_pix[island.ravel()]):.2f} mm, "
        f"IQR {np.percentile(sigma_pix[island.ravel()],25):.2f}-"
        f"{np.percentile(sigma_pix[island.ravel()],75):.2f} mm")

    # Oregon-mean series noise
    w = np.where(inbox & island, np.cos(np.radians(latv))[:, None], 0.0)
    ormean = (arr * w[None]).sum(axis=(1, 2)) / w.sum()
    d2m = ormean[a0] - 2 * ormean[a1] + ormean[a2]
    sig_reg = float(np.std(d2m) / np.sqrt(6))
    say(f"Oregon-mean series noise sigma          : {sig_reg:.2f} mm")
    say(f"=> dS/dt noise sigma (centred diff)     : {sig_reg/np.sqrt(2):.2f} mm/month")
    say("   (centred difference of white noise has std sigma/sqrt(2))")

    # ---- 2. spatial correlation vs distance ----------------------------
    sect("2. SPATIAL DECORRELATION (deseasonalised, detrended pixel anomalies)")
    li, lj = np.where(island)
    pts = np.column_stack([latv[li], lonv[lj]])
    series = anom[:, li, lj]                      # (t, npix)
    series = series - series.mean(axis=0)
    sd = series.std(axis=0)
    C = (series.T @ series) / nt / np.outer(sd, sd)
    la = np.radians(pts[:, 0])
    dx = (pts[:, 1][None, :] - pts[:, 1][:, None]) * 111.0 * np.cos(la[:, None])
    dy = (pts[:, 0][None, :] - pts[:, 0][:, None]) * 111.0
    D = np.hypot(dx, dy)
    iu = np.triu_indices(len(pts), k=1)
    dd, cc = D[iu], C[iu]
    bins = [0, 50, 100, 150, 200, 250, 300, 400, 500, 700, 1000]
    say(f"{'dist km':>12s} {'n pairs':>8s} {'mean r':>8s}")
    for k in range(len(bins) - 1):
        m = (dd >= bins[k]) & (dd < bins[k + 1])
        if m.sum():
            say(f"{bins[k]:5d}-{bins[k+1]:<6d} {m.sum():8d} {cc[m].mean():8.3f}")
    for thr in (0.9, 0.7, 0.5):
        ok = dd[cc < thr]
        say(f"correlation first drops below {thr}: "
            f"{(ok.min() if len(ok) else np.nan):.0f} km")

    # ---- 3. effective spatial degrees of freedom -----------------------
    sect("3. EFFECTIVE SPATIAL DEGREES OF FREEDOM over the Oregon box")
    sel = (inbox & island)
    si, sj = np.where(sel)
    Y = anom[:, si, sj]
    Y = Y - Y.mean(axis=0)
    say(f"Oregon land pixels: {Y.shape[1]}")
    cov = np.cov(Y.T)
    ev = np.sort(np.linalg.eigvalsh(cov))[::-1]
    ev = ev[ev > 0]
    frac = np.cumsum(ev) / ev.sum()
    for q in (0.90, 0.95, 0.99):
        say(f"  EOFs to explain {q*100:.0f}% of variance: {int(np.searchsorted(frac,q)+1)}")
    n_eff = (ev.sum() ** 2) / (ev ** 2).sum()
    say(f"  participation-ratio effective DOF     : {n_eff:.2f}")
    say(f"  first EOF alone explains              : {100*frac[0]:.1f}% of variance")
    say("\n  INTERPRETATION: the Oregon box behaves as ~1 spatial degree of")
    say("  freedom. Individual half-degree pixels are NOT independent samples,")
    say("  and a single pixel cannot be treated as a local measurement.")

    # ---- 4. leakage ----------------------------------------------------
    sect("4. OCEAN LEAKAGE (deseasonalised, detrended)")
    wo = np.where(~island, np.cos(np.radians(latv))[:, None], 0.0)
    oc = (anom * wo[None]).sum(axis=(1, 2)) / wo.sum()
    orl = (anom * w[None]).sum(axis=(1, 2)) / w.sum()
    say(f"corr(Oregon land anomaly, buffered-ocean anomaly) = "
        f"{np.corrcoef(orl, oc)[0,1]:+.3f}")
    # coastal vs interior land
    coast = island & (lonv[None, :] < -123.0)
    inter = island & (lonv[None, :] > -120.0) & inbox
    for nm, mk in (("coastal land (<123W)", coast), ("interior OR land", inter)):
        ww = np.where(mk, np.cos(np.radians(latv))[:, None], 0.0)
        s = (anom * ww[None]).sum(axis=(1, 2)) / ww.sum()
        say(f"corr({nm:22s}, ocean) = {np.corrcoef(s, oc)[0,1]:+.3f}")
    say("Ocean pixels carry GAD added back (postprocess_1) and are NOT TWS;")
    say("they are excluded from every land statistic by the in-file land_mask.")

    # ---- 5. inter-mission step ----------------------------------------
    sect("5. GRACE -> GRACE-FO STEP (fitted jointly with trend+harmonics)")
    t = pd.to_datetime(sub.time.values)
    step = (t > pd.Timestamp("2018-01-01")).astype(float)
    X2 = np.column_stack([x, step])
    c2, *_ = np.linalg.lstsq(X2, ormean, rcond=None)
    res = ormean - X2 @ c2
    dof = len(ormean) - X2.shape[1]
    cov2 = np.linalg.inv(X2.T @ X2) * (res @ res) / dof
    se = np.sqrt(np.diag(cov2))
    r1 = float(np.corrcoef(res[:-1], res[1:])[0, 1])
    infl = np.sqrt(max((1 + r1) / max(1 - r1, 1e-6), 1.0))
    say(f"trend with step term : {c2[1]:+.3f} +/- {se[1]*infl:.3f} mm/yr")
    say(f"mission step         : {c2[-1]:+.3f} +/- {se[-1]*infl:.3f} mm")
    say("Step is NOT removed from the data: it is indistinguishable from real")
    say("storage change across an 11-month gap. Flagged as an uncertainty.")

    # ---- 6. trend summary ---------------------------------------------
    sect("6. TREND SUMMARY (one statistic, not the deliverable)")
    c1, *_ = np.linalg.lstsq(x, ormean, rcond=None)
    say(f"Oregon land TWS trend (no step term): {c1[1]:+.3f} mm/yr, "
        f"2002-04..2026-03")
    say(f"seasonal peak-to-peak: {ormean.max()-ormean.min():.0f} mm")

    pd.DataFrame({"time": t, "oregon_land_mm": ormean,
                  "oregon_land_anom_mm": orl,
                  "ocean_anom_mm": oc}).to_parquet(
        rf"{P}\grace_oregon_series.parquet", index=False)
    with open(rf"{INV}\grace_signal_quality.txt", "w") as f:
        f.write("\n".join(OUT))
    say("\nwrote processed/grace_oregon_series.parquet, "
        "inventory/grace_signal_quality.txt")


if __name__ == "__main__":
    main()
