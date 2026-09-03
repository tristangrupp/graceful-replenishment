"""Phase 2: GSFC mascon preprocessing + signal-quality characterisation.

Emphasis (per updated direction): a clean, well-characterised monthly GRACE
series over Oregon. Trend fitting is one summary statistic, not the point.

Outputs
  processed/grace_pixels_monthly.parquet  per-pixel monthly TWS (mm), buffered box
  processed/grace_native_mascons.parquet  half-degree pixel -> native mascon id
  processed/grace_region_monthly.parquet  area-weighted region means + dS/dt
  inventory/grace_signal_quality.txt      gaps, noise, leakage, offset
"""
import sys, hashlib
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion.trend import fit_trend

NC = r"E:\Water\Oregan\analysis\raw\gsfc_mascons_halfdegree.nc"
P = r"E:\Water\Oregan\analysis\processed"
INV = r"E:\Water\Oregan\analysis\inventory"

# Oregon proper; field centroids span lon -124.54..-115.98, lat 40.87..46.51
OR_BOX = dict(lon0=-124.6, lon1=-116.4, lat0=41.9, lat1=46.3)
BUF = 3.0   # ~240 km lon / ~333 km lat at 44N ~ one 300 km effective-res length
R_EARTH = 6371007.181


def sect(t, f):
    for h in (sys.stdout, f):
        print("\n" + "=" * 76 + f"\n{t}\n" + "=" * 76, file=h)


def cell_area_m2(lat_c, dlat=0.5, dlon=0.5):
    la0, la1 = np.radians(lat_c - dlat / 2), np.radians(lat_c + dlat / 2)
    return (R_EARTH ** 2) * np.radians(dlon) * (np.sin(la1) - np.sin(la0))


def main():
    f = open(rf"{INV}\grace_signal_quality.txt", "w")

    ds = xr.open_dataset(NC, decode_times=True)
    lwe = ds["lwe_thickness"]
    assert ds["lwe_thickness"].attrs["units"] == "cm", "unit assumption broken"
    lwe = lwe * 10.0                      # cm -> mm
    lwe.attrs["units"] = "mm"
    land = ds["land_mask"]

    # ---- longitude 0-360 -> -180/180 -------------------------------------
    lwe = lwe.assign_coords(lon=(((lwe.lon + 180) % 360) - 180)).sortby("lon")
    land = land.assign_coords(lon=(((land.lon + 180) % 360) - 180)).sortby("lon")

    b = dict(lon0=OR_BOX["lon0"] - BUF, lon1=OR_BOX["lon1"] + BUF,
             lat0=OR_BOX["lat0"] - BUF, lat1=OR_BOX["lat1"] + BUF)
    sub = lwe.sel(lon=slice(b["lon0"], b["lon1"]), lat=slice(b["lat0"], b["lat1"])).load()
    subland = land.sel(lon=slice(b["lon0"], b["lon1"]), lat=slice(b["lat0"], b["lat1"])).load()
    sect("SUBSET", f)
    for h in (sys.stdout, f):
        print(f"buffered box lon {b['lon0']}..{b['lon1']} lat {b['lat0']}..{b['lat1']}", file=h)
        print(f"dims {dict(sub.sizes)}", file=h)
        print(f"land pixels {int((subland>0).sum())} / {subland.size}"
              f" ({100*float((subland>0).mean()):.1f}%)", file=h)

    # ---- collapse to calendar months (2018-11 has two solutions) ---------
    t = pd.to_datetime(sub.time.values)
    months = t.values.astype("datetime64[M]").astype("datetime64[ns]")
    sub = sub.assign_coords(time=months).groupby("time").mean("time")
    per = pd.PeriodIndex(pd.to_datetime(sub.time.values), freq="M")
    sect("MONTHLY AXIS", f)
    for h in (sys.stdout, f):
        print(f"n monthly steps {len(per)}  {per[0]} .. {per[-1]}", file=h)

    # ---- native mascon detection ----------------------------------------
    # On land each 0.5deg pixel is a copy of its 1-arc-degree mascon's value,
    # so identical time series identify one native mascon.
    sect("NATIVE MASCON FOOTPRINTS (identical time series => one mascon)", f)
    arr = sub.values                       # (time, lat, lon)
    nt, nla, nlo = arr.shape
    flat = arr.reshape(nt, -1).T           # (pixel, time)
    keys = [hashlib.md5(np.ascontiguousarray(r).tobytes()).hexdigest()[:12]
            for r in flat]
    latg, long_ = np.meshgrid(sub.lat.values, sub.lon.values, indexing="ij")
    pix = pd.DataFrame({"lat": latg.ravel(), "lon": long_.ravel(),
                        "mascon_key": keys,
                        "is_land": (subland.values.ravel() > 0)})
    pix["cell_area_km2"] = cell_area_m2(pix["lat"]) / 1e6
    grp = pix.groupby("mascon_key")
    sizes = grp.size()
    for h in (sys.stdout, f):
        print(f"half-degree pixels in box : {len(pix)}", file=h)
        print(f"distinct native mascons   : {pix['mascon_key'].nunique()}", file=h)
        print(f"pixels per native mascon  : median {sizes.median():.0f} "
              f"mean {sizes.mean():.1f} min {sizes.min()} max {sizes.max()}", file=h)
        lp = pix[pix.is_land]
        print(f"LAND pixels {len(lp)}, distinct land mascons "
              f"{lp['mascon_key'].nunique()}, median pixels/mascon "
              f"{lp.groupby('mascon_key').size().median():.0f}", file=h)
        print(f"mean native mascon area (land) : "
              f"{lp.groupby('mascon_key')['cell_area_km2'].sum().mean():,.0f} km2", file=h)
    pix.to_parquet(rf"{P}\grace_native_mascons.parquet", index=False)

    # ---- per-pixel monthly table ----------------------------------------
    long = (sub.to_dataframe(name="tws_mm").reset_index()
            .merge(pix[["lat", "lon", "mascon_key", "is_land", "cell_area_km2"]],
                   on=["lat", "lon"], how="left"))
    long.to_parquet(rf"{P}\grace_pixels_monthly.parquet", index=False)

    # ---- region means ----------------------------------------------------
    sect("REGION MEAN SERIES", f)
    # Explicit numpy area weighting: w_ij = cos(lat_i), zero outside the mask.
    arrv = sub.values                                    # (time, lat, lon)
    latv = sub.lat.values
    lonv = sub.lon.values
    wlat = np.cos(np.radians(latv))[:, None] * np.ones((1, len(lonv)))
    inbox = ((lonv[None, :] >= OR_BOX["lon0"]) & (lonv[None, :] <= OR_BOX["lon1"])
             & (latv[:, None] >= OR_BOX["lat0"]) & (latv[:, None] <= OR_BOX["lat1"]))
    island = subland.values > 0
    masks = {
        "oregon_land": inbox & island,
        "buffered_land": island,
        "buffered_ocean": ~island,
    }
    regions = {}
    for name, m in masks.items():
        w = np.where(m, wlat, 0.0)
        tot = w.sum()
        ser = (arrv * w[None, :, :]).sum(axis=(1, 2)) / tot
        regions[name] = ser
        for h in (sys.stdout, f):
            print(f"{name:16s} npix {int(m.sum()):5d}  "
                  f"mean {np.nanmean(ser):+.2f} mm  std {np.nanstd(ser):.2f} mm", file=h)

    reg = pd.DataFrame(regions)
    reg.insert(0, "time", pd.to_datetime(sub.time.values))
    reg["period"] = per.astype(str)

    # ---- dS/dt: gap-aware centred difference -----------------------------
    sect("dS/dt (CENTRED DIFFERENCE, GAP-AWARE)", f)
    idx = {p: i for i, p in enumerate(per)}
    for name in regions:
        s = reg[name].values
        d = np.full(len(s), np.nan)
        for i, p in enumerate(per):
            a, bb = idx.get(p - 1), idx.get(p + 1)
            if a is not None and bb is not None:
                d[i] = (s[bb] - s[a]) / 2.0     # mm per month
        reg["dSdt_" + name] = d
    n_ok = int(np.isfinite(reg["dSdt_oregon_land"]).sum())
    for h in (sys.stdout, f):
        print(f"months with a defined dS/dt (oregon_land): {n_ok} of {len(reg)}", file=h)
        print("dS/dt std (oregon_land): "
              f"{np.nanstd(reg['dSdt_oregon_land']):.2f} mm/month", file=h)

    reg.to_parquet(rf"{P}\grace_region_monthly.parquet", index=False)

    # ---- noise, leakage, inter-mission offset ----------------------------
    sect("SIGNAL QUALITY", f)
    ser = xr.DataArray(reg["oregon_land"].values,
                       coords={"time": pd.to_datetime(reg["time"])}, dims="time")
    ft = fit_trend(ser)
    resid = ser.values - _model(ser, ft)
    for h in (sys.stdout, f):
        print(f"trend+harmonics fit: trend {float(ft.trend):+.3f} mm/yr  "
              f"p {float(ft.p_value):.4f}", file=h)
        print(f"residual std (noise proxy) : {np.nanstd(resid):.2f} mm", file=h)
        print(f"seasonal peak-to-peak      : "
              f"{np.nanmax(ser.values)-np.nanmin(ser.values):.1f} mm", file=h)

    # month-to-month roughness = high-frequency noise proxy
    dif = np.diff(reg["oregon_land"].values)
    for h in (sys.stdout, f):
        print(f"std of 1-month differences : {np.nanstd(dif):.2f} mm", file=h)

    # leakage: land vs adjacent ocean correlation
    ok = np.isfinite(reg["oregon_land"]) & np.isfinite(reg["buffered_ocean"])
    r_lo = np.corrcoef(reg["oregon_land"][ok], reg["buffered_ocean"][ok])[0, 1]
    for h in (sys.stdout, f):
        print(f"corr(oregon land, buffered ocean) = {r_lo:+.3f}  "
              "(ocean-leakage indicator)", file=h)

    # inter-mission offset on the residual
    tt = pd.to_datetime(reg["time"])
    pre = resid[(tt < "2017-07-01").values]
    post = resid[(tt > "2018-05-31").values]
    for h in (sys.stdout, f):
        print(f"residual mean GRACE era   ({np.isfinite(pre).sum()} mo): "
              f"{np.nanmean(pre):+.2f} mm", file=h)
        print(f"residual mean GRACE-FO era({np.isfinite(post).sum()} mo): "
              f"{np.nanmean(post):+.2f} mm", file=h)
        print(f"apparent inter-mission offset: "
              f"{np.nanmean(post)-np.nanmean(pre):+.2f} mm "
              "(confounded with real trend; not removed)", file=h)
    f.close()
    print("\nwrote outputs to processed/ and inventory/grace_signal_quality.txt")


def _model(ser, ft):
    """Reconstruct trend+harmonics fit for residuals."""
    from dark_water.depletion_watchlist.depletion.trend import _decimal_years, _design_matrix
    y = ser.values.reshape(len(ser), -1)
    x = _design_matrix(_decimal_years(ser.time))
    c, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    return (x @ c).ravel()


if __name__ == "__main__":
    main()
