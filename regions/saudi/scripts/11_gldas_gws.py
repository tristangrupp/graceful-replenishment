"""GRACE-minus-GLDAS groundwater storage for every Arabian Peninsula mascon.

This is the subtraction the dark-water package implements and that every
earlier Saudi figure had to do without, because no Earthdata credentials
existed on this machine. With the token in place:

    GWS(t) = TWS(t) - [soil moisture + snow water equivalent + canopy](t)

run once per GLDAS land-surface model (NOAH 0.25 deg, VIC 1.0 deg, CLSM
1.0 deg) so the model spread becomes a stated uncertainty rather than an
assumption.

Done in mascon space, not on the interpolated half-degree grid. The GSFC
mascon is the native resolution element; interpolating GRACE to a finer grid
and subtracting there would invent structure the measurement does not have.
GLDAS is averaged up to each mascon's box instead, which is the direction that
loses no information.

Baselines are removed only over the months the two records share, per the fix
in attribution.groundwater_storage_anomaly -- GRACE has the 2017-2018
intermission and scattered missing months, GLDAS has none, so de-meaning each
over its own axis would leave a constant offset with no physical meaning.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

from dark_water.depletion_watchlist.depletion import attribution as A
from dark_water.depletion_watchlist.depletion import trend as T
from dark_water.depletion_watchlist.depletion import precipitation as P

ROOT = Path(r"E:\Water\Saudi")
PROC, SIG, TR = ROOT / "processed", ROOT / "signals", ROOT / "trends"
MODELS = ("noah", "vic", "clsm")

# ------------------------------------------------------------------ GRACE
ds = xr.open_dataset(PROC / "arabia_mascons.nc")
meta = pd.read_csv(SIG / "mascon_metadata.csv")
obs = ds["observed"].values.astype(bool)
mid = pd.to_datetime(ds["solution_mid_date"].values)[obs]
tws = xr.DataArray(
    ds["lwe_thickness"].values[:, obs].T,
    dims=("time", "mascon"),
    coords={"time": mid.to_numpy(), "mascon": ds["mascon"].values},
)
mascon_id = ds["mascon"].values
n_mas = len(mascon_id)
print(f"GRACE: {n_mas} mascons x {tws.sizes['time']} observed months")


def to_mascons(da: xr.DataArray) -> xr.DataArray:
    """Area-mean a lat/lon field onto each mascon's bounding box.

    Cells whose centre falls inside the box are averaged with cos(lat)
    weights. A mascon smaller than a VIC/CLSM 1.0 deg cell can contain no
    centre at all, so those fall back to the single nearest cell -- reported,
    not silent, because a fallback mascon carries no sub-cell information.
    """
    lat, lon = da["lat"].values, da["lon"].values
    vals = da.transpose("time", "lat", "lon").values
    out = np.full((vals.shape[0], n_mas), np.nan)
    n_fallback = 0
    for i in range(n_mas):
        la, lo = meta.lat_center[i], meta.lon_center[i]
        hy, hx = meta.lat_span_deg[i] / 2, meta.lon_span_deg[i] / 2
        my = (lat >= la - hy) & (lat < la + hy)
        mx = (lon >= lo - hx) & (lon < lo + hx)
        if my.sum() and mx.sum():
            blk = vals[:, my, :][:, :, mx]
            w = np.cos(np.deg2rad(lat[my]))[None, :, None]
            w = np.broadcast_to(w, blk.shape).copy()
            w[~np.isfinite(blk)] = 0.0
            with np.errstate(invalid="ignore"):
                out[:, i] = np.nansum(blk * w, axis=(1, 2)) / np.where(
                    w.sum(axis=(1, 2)) > 0, w.sum(axis=(1, 2)), np.nan)
        else:
            n_fallback += 1
            out[:, i] = vals[:, np.abs(lat - la).argmin(), np.abs(lon - lo).argmin()]
    if n_fallback:
        print(f"    {n_fallback} mascons smaller than a grid cell -> nearest-cell fallback")
    return xr.DataArray(out, dims=("time", "mascon"),
                        coords={"time": da["time"].values, "mascon": mascon_id})


# --------------------------------------------------------- per-model GWS
gws_by_model, nongw_by_model = {}, {}
for m in MODELS:
    g = xr.open_dataset(PROC / f"gldas_{m}_monthly.nc")
    non_gw = A._NON_GW_STORAGE[m](g)  # kg/m2 summed -> cm inside the package
    print(f"[{m}] {dict(g.sizes)}  non-GW storage {float(non_gw.mean()):.2f} cm mean")
    non_gw_mas = A.monthly_mean(to_mascons(non_gw))

    # the fixed baseline logic: restrict to common months FIRST, then de-mean
    grace_c, non_gw_c = xr.align(A.monthly_mean(tws), non_gw_mas, join="inner")
    gws = (grace_c - grace_c.mean("time")) - (non_gw_c - non_gw_c.mean("time"))
    gws_by_model[m] = gws
    nongw_by_model[m] = non_gw_c - non_gw_c.mean("time")
    print(f"[{m}] GWS on {gws.sizes['time']} common months")

aligned = xr.align(*[gws_by_model[m] for m in MODELS], join="inner")
stack = xr.concat(aligned, dim=pd.Index(MODELS, name="model"))
ens_mean = stack.mean("model")
ens_spread = stack.max("model") - stack.min("model")
# A coastal mascon can have no land cell in the 1.0 deg VIC/CLSM grids, in
# which case the nan-skipping mean quietly becomes NOAH alone. Counted, so a
# one-model "ensemble" is never reported as a three-model one.
n_models = np.isfinite(stack.values).all(axis=1).sum(axis=0)
print(f"ensemble on {ens_mean.sizes['time']} months; "
      f"median spread {float(ens_spread.median()):.2f} cm; "
      f"{int((n_models < len(MODELS)).sum())} mascons backed by fewer than {len(MODELS)} models")

# ------------------------------------------------------------------ trends
pen = meta.on_arabian_peninsula.values.astype(bool)


def trends(da):
    f = T.fit_trend(da, dim="time", alpha=0.05)
    return f["trend"].values, f["p_value"].values


tws_common = A.monthly_mean(tws).sel(time=ens_mean["time"])
tr_tws, p_tws = trends(tws_common)
tr_gws, p_gws = trends(ens_mean)
per_model_tr = {m: trends(stack.sel(model=m))[0] for m in MODELS}

# how much of the TWS trend the land-surface models themselves carry
tr_nongw = {m: trends(nongw_by_model[m].sel(time=ens_mean["time"]))[0] for m in MODELS}

# ------------------------------------- GLDAS precipitation as a CHIRPS check
g = xr.open_dataset(PROC / "gldas_noah_monthly.nc")
pr_depth = P.precipitation_depth(g)  # cm/month
pr_mas = to_mascons(pr_depth)
cum = P.cumulative_anomaly(pr_mas, dim="time")
cum_c = A.monthly_mean(cum).sel(time=ens_mean["time"])
adj = P.adjusted_trend(ens_mean, cum_c, dim="time")

out = meta.copy()
out["tws_trend_cm_per_yr"] = tr_tws
out["tws_p_value"] = p_tws
out["gws_trend_cm_per_yr"] = tr_gws
out["gws_p_value"] = p_gws
out["gws_significant_decline"] = (tr_gws < 0) & (p_gws < 0.05)
for m in MODELS:
    out[f"gws_trend_{m}_cm_per_yr"] = per_model_tr[m]
    out[f"nongw_trend_{m}_cm_per_yr"] = tr_nongw[m]
out["gws_model_spread_cm_per_yr"] = (
    np.max([per_model_tr[m] for m in MODELS], axis=0)
    - np.min([per_model_tr[m] for m in MODELS], axis=0))
out["gws_mean_ensemble_spread_cm"] = ens_spread.mean("time").values
out["n_models"] = n_models
out["gws_precip_adjusted_trend_cm_per_yr"] = adj["trend"].values
out["gws_fraction_unexplained_by_precip"] = adj["fraction_unexplained"].values
out.to_csv(TR / "mascon_gws_gldas.csv", index=False)

# corrected/GWS series for plotting
wide = pd.DataFrame(ens_mean.values, index=pd.PeriodIndex(
    pd.to_datetime(ens_mean["time"].values), freq="M").astype(str),
    columns=[f"m{i}" for i in mascon_id])
wide.index.name = "month"
wide.loc[:, [f"m{i}" for i in mascon_id[pen]]].to_csv(SIG / "peninsula_gws_ensemble_cmwe.csv")

p = out[pen]
old = pd.read_csv(TR / "mascon_trends_and_quality.csv")
old_p = old[old.on_arabian_peninsula]

# Area weights: mascon area times the share of it that is actually peninsula,
# so a half-offshore mascon does not vote at full strength.
w = (p.area_km2 * p.frac_area_arabian_peninsula).values


def wavg(col):
    v = p[col].values
    ok = np.isfinite(v)
    return float(np.average(v[ok], weights=w[ok]))


area_km2 = float(w.sum())
summary = {
    "n_peninsula": int(pen.sum()),
    "n_mascons_with_fewer_than_3_models": int((p.n_models < len(MODELS)).sum()),
    "area_weighted_mm_per_yr": {
        "tws": wavg("tws_trend_cm_per_yr") * 10,
        "gws_ensemble": wavg("gws_trend_cm_per_yr") * 10,
        **{f"gws_{m}": wavg(f"gws_trend_{m}_cm_per_yr") * 10 for m in MODELS},
        "model_spread": wavg("gws_model_spread_cm_per_yr") * 10,
        "leakage_floor": float(np.average(
            old_p.trend_leakage_uncert_cm_per_yr.abs().values, weights=w)) * 10,
    },
    "peninsula_area_km2": area_km2,
    "gws_volume_km3_per_yr": wavg("gws_trend_cm_per_yr") / 100 * area_km2 / 1000,
    "n_gws_steeper_than_tws": int((p.gws_trend_cm_per_yr < p.tws_trend_cm_per_yr).sum()),
    "n_common_months": int(ens_mean.sizes["time"]),
    "median_tws_trend_cm_yr": float(p.tws_trend_cm_per_yr.median()),
    "median_gws_trend_cm_yr": float(p.gws_trend_cm_per_yr.median()),
    "median_gldas_storage_trend_cm_yr": {
        m: float(p[f"nongw_trend_{m}_cm_per_yr"].median()) for m in MODELS},
    "median_gws_trend_by_model_cm_yr": {
        m: float(p[f"gws_trend_{m}_cm_per_yr"].median()) for m in MODELS},
    "median_model_spread_cm_yr": float(p.gws_model_spread_cm_per_yr.median()),
    "median_leakage_uncert_cm_yr": float(old_p.trend_leakage_uncert_cm_per_yr.median()),
    "n_gws_significant_decline": int(p.gws_significant_decline.sum()),
    "n_gws_trend_exceeds_model_spread": int(
        (p.gws_trend_cm_per_yr.abs() > p.gws_model_spread_cm_per_yr).sum()),
    "median_gws_fraction_unexplained_by_gldas_precip": float(
        p.gws_fraction_unexplained_by_precip.median()),
    "median_chirps_fraction_unexplained_prev": float(
        old_p.fraction_unexplained_by_precip.median()),
}
json.dump(summary, open(TR / "gws_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
print("\nwrote", TR / "mascon_gws_gldas.csv")
print("wrote", SIG / "peninsula_gws_ensemble_cmwe.csv")
