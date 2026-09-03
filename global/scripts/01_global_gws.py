"""Global GRACE-FO-era storage trends per GSFC mascon, with and without GLDAS.

Two products, same estimator, same months:

    TWS  -- GRACE total water storage
    GWS  -- TWS minus GLDAS soil moisture + snow water equivalent + canopy,
            averaged over the NOAH, VIC and CLSM land-surface models

The window is the GRACE-FO record, 2018-06 to 2026-03, which is where the GSFC
RL06v2.0 release ends. GLDAS runs two months further and is cut to match.

Done in native mascon space. GSFC mascons are ~1 degree equal-area cells and are
the real resolution element, so GLDAS is averaged up onto them rather than GRACE
being interpolated down: interpolating up invents structure the measurement does
not have.
"""

import glob
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"E:\Water\_shared")
sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion import attribution as A  # noqa: E402
from dark_water.depletion_watchlist.depletion import trend as T  # noqa: E402
from gsfc_grid import CM_TO_MM, cell_to_mascon, load_geometry, load_series, terrestrial  # noqa: E402

ROOT = Path(r"E:\Water\Global")
START, END = "2018-06", "2026-03"
MODELS = ("noah", "vic", "clsm")

geo = load_geometry()
n_mas = len(geo)
land = terrestrial(geo)
print(f"{n_mas} mascons, {land.sum()} terrestrial (ocean excluded, ice sheets kept)")

tws = load_series().loc[START:END]
print(f"GRACE {len(tws)} months {tws.index[0]:%Y-%m}..{tws.index[-1]:%Y-%m}")


def gldas_to_mascons(model):
    """Non-groundwater storage (mm) per mascon per month for one GLDAS model."""
    files = sorted(glob.glob(str(ROOT / "raw" / "gldas" / model / "*.nc4")))
    if not files:
        raise SystemExit(f"no GLDAS files for {model}")
    rows, stamps, mapping, cosw = [], [], None, None
    for fn in files:
        with xr.open_dataset(fn, engine="netcdf4") as d:
            if mapping is None:
                lat, lon = d["lat"].values, d["lon"].values
                mapping = cell_to_mascon(geo, lat, lon).ravel()
                cosw = np.broadcast_to(np.cos(np.deg2rad(lat))[:, None],
                                       (len(lat), len(lon))).ravel().astype("float64")
                print(f"[{model}] grid {len(lat)}x{len(lon)}, "
                      f"{len(np.unique(mapping))} mascons touched")
            v = (A._NON_GW_STORAGE[model](d) * CM_TO_MM).transpose("time", "lat", "lon")
            vals = np.asarray(v.values[0], dtype="float64").ravel()
            stamps.append(pd.Timestamp(d["time"].values[0]).to_period("M").to_timestamp())
        ok = np.isfinite(vals)
        num = np.bincount(mapping[ok], weights=(vals * cosw)[ok], minlength=n_mas)
        den = np.bincount(mapping[ok], weights=cosw[ok], minlength=n_mas)
        rows.append(np.divide(num, den, out=np.full(n_mas, np.nan), where=den > 0))
    df = pd.DataFrame(np.array(rows), index=pd.DatetimeIndex(stamps)).sort_index()
    print(f"[{model}] {len(df)} months, "
          f"{int(np.isfinite(df.to_numpy()).all(axis=0).sum())} mascons with a complete series")
    return df


storage = {m: gldas_to_mascons(m) for m in MODELS}

idx = tws.index
for s in storage.values():
    idx = idx.intersection(s.index)
tws_c = tws.loc[idx]
print(f"common months: {len(idx)} {idx[0]:%Y-%m}..{idx[-1]:%Y-%m}")

# Baselines removed only over the shared months, per the fix in
# attribution.groundwater_storage_anomaly.
tws_a = tws_c - tws_c.mean()
gws_by_model = {m: tws_a - (storage[m].loc[idx] - storage[m].loc[idx].mean()) for m in MODELS}
gws = sum(gws_by_model.values()) / len(MODELS)


def fit(df):
    da = xr.DataArray(df.to_numpy(), dims=("time", "mascon"),
                      coords={"time": df.index, "mascon": np.arange(df.shape[1])})
    r = T.fit_trend(da, dim="time", alpha=0.05)
    return r["trend"].values, r["p_value"].values


tws_trend, tws_p = fit(tws_a)
gws_trend, gws_p = fit(gws)
per_model_trend = {m: fit(gws_by_model[m])[0] for m in MODELS}
stack = np.array([per_model_trend[m] for m in MODELS])
spread = np.nanmax(stack, axis=0) - np.nanmin(stack, axis=0)

out = geo.copy()
out["land"] = land
out["tws_trend_mm_yr"] = tws_trend
out["tws_p"] = tws_p
out["gws_trend_mm_yr"] = gws_trend
out["gws_p"] = gws_p
out["gws_model_spread_mm_yr"] = spread
for m in MODELS:
    out[f"gws_trend_{m}_mm_yr"] = per_model_trend[m]
out.to_parquet(ROOT / "trends" / "mascon_trends_gracefo.parquet")

# series kept for the basin aggregation, land only to keep the file small
cols = np.where(land)[0]
tws_a.iloc[:, cols].to_parquet(ROOT / "processed" / "tws_anomaly_mm_land.parquet")
gws.iloc[:, cols].to_parquet(ROOT / "processed" / "gws_anomaly_mm_land.parquet")

summary = {
    "window": [f"{idx[0]:%Y-%m}", f"{idx[-1]:%Y-%m}"],
    "n_months": len(idx),
    "n_mascons": int(n_mas),
    "n_land_mascons": int(land.sum()),
    "n_land_with_gws": int(np.isfinite(gws_trend[land]).sum()),
    "median_land_tws_trend_mm_yr": float(np.nanmedian(tws_trend[land])),
    "median_land_gws_trend_mm_yr": float(np.nanmedian(gws_trend[land])),
    "median_model_spread_mm_yr": float(np.nanmedian(spread[land])),
}
json.dump(summary, open(ROOT / "trends" / "mascon_trends_summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
