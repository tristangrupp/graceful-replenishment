"""Per-mascon GRACE signals for the Nuevo Leon window.

Reads the native GSFC RL06v2.0 mascon HDF5 (never the interpolated
half-degree grid, which destroys mascon identity), keeps land mascons only
(`location == 80`; 90 is ocean and the Gulf of Mexico is one mascon away),
and writes:

  signals/mascon_monthly_long.parquet   tidy per-mascon monthly series
  signals/mascon_metadata.csv           geometry + GSFC uncertainty terms
  signals/gaps.json                     the observed/missing month record

dS/dt is a centred difference computed only where both neighbours are
within 80 days of the centre epoch, so no derivative is manufactured
across the 2017-07..2018-05 mission gap.
"""

import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

H5 = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
OUT = Path(r"E:\Water\NuevoLeon")
LAND = 80.0
LAT = (22.0, 29.0)      # the padded window already used for decorrelation
LON = (-102.7, -97.0)
MAX_GAP_DAYS = 80


def main():
    (OUT / "signals").mkdir(parents=True, exist_ok=True)
    with h5py.File(H5, "r") as f:
        m = f["mascon"]
        geo = pd.DataFrame({
            "lat_center": np.ravel(m["lat_center"][:]),
            "lon_center": np.ravel(m["lon_center"][:]),
            "lat_span": np.ravel(m["lat_span"][:]),
            "lon_span": np.ravel(m["lon_span"][:]),
            "area_km2": np.ravel(m["area_km2"][:]),
            "location": np.ravel(m["location"][:]),
        })
        geo["mascon_id"] = np.arange(len(geo))
        geo["lon_180"] = ((geo["lon_center"] + 180) % 360) - 180
        keep = (geo["lat_center"].between(*LAT) & geo["lon_180"].between(*LON)
                & (geo["location"] == LAND))
        sel = geo[keep].copy().reset_index(drop=True)
        ids = sel["mascon_id"].to_numpy()

        cmwe = f["solution/cmwe"][ids, :]                       # cm
        noise = f["uncertainty/noise_2sigma"][ids, :]           # cm
        # leakage_2sigma is one value per mascon, not per month
        leak = np.ravel(f["uncertainty/leakage_2sigma"][:])[ids]
        leak_tr = np.ravel(f["uncertainty/leakage_trend"][:])[ids]
        ymd = f["time/yyyy_doy_yrplot_middle"][:]
        ndays = np.ravel(f["time/n_ref_days_solution"][:]) if "n_ref_days_solution" in f["time"] else None

    mid = (pd.to_datetime([f"{int(y)}-01-01" for y in ymd[0]])
           + pd.to_timedelta(ymd[1].astype(int) - 1, unit="D"))
    mid = pd.DatetimeIndex(mid)
    sel["leakage_trend_cm_yr"] = leak_tr
    sel["leakage_2sigma_cm"] = leak
    sel["lat_min"] = sel["lat_center"] - sel["lat_span"] / 2
    sel["lat_max"] = sel["lat_center"] + sel["lat_span"] / 2
    sel["lon_min"] = sel["lon_180"] - sel["lon_span"] / 2
    sel["lon_max"] = sel["lon_180"] + sel["lon_span"] / 2

    # --- collapse to calendar months, weighting duplicate solutions by length
    month = pd.PeriodIndex(mid, freq="M")
    w = ndays.astype(float) if ndays is not None else np.ones(len(mid))
    rows = []
    for p in month.unique():
        k = np.where(month == p)[0]
        ww = w[k] / w[k].sum()
        # Weighted mean of the true solution midpoints, in integer nanoseconds.
        # `np.average(...).astype("datetime64[ns]")` mis-scales silently here and
        # put every midpoint in January 1970, which made dS/dt meaningless while
        # leaving the storage values themselves untouched.
        # NB the index is datetime64[us] here, so `asi8` would be microseconds
        # while pd.Timestamp(int) reads nanoseconds - hence the explicit cast.
        ns = int(np.average(mid[k].values.astype("datetime64[ns]").astype("int64"),
                            weights=ww))
        rows.append({"month": p, "solution_mid_date": pd.Timestamp(ns), "idx": k, "w": ww})
    mrec = pd.DataFrame(rows).sort_values("month").reset_index(drop=True)

    n_mas = len(sel)
    obs_months = pd.period_range(month.min(), month.max(), freq="M")
    lwe = np.full((n_mas, len(obs_months)), np.nan)
    nz = np.full((n_mas, len(obs_months)), np.nan)
    mid_full = np.full(len(obs_months), np.datetime64("NaT", "ns"), dtype="datetime64[ns]")
    pos = {p: i for i, p in enumerate(obs_months)}
    for _, r in mrec.iterrows():
        i = pos[r["month"]]
        lwe[:, i] = (cmwe[:, r["idx"]] * r["w"]).sum(axis=1)
        nz[:, i] = (noise[:, r["idx"]] * r["w"]).sum(axis=1)
        mid_full[i] = np.datetime64(r["solution_mid_date"])
    observed = np.isfinite(lwe).all(axis=0)

    # --- gap-aware centred dS/dt (cm/yr) on the true solution midpoints
    t_days = (mid_full - np.datetime64("2000-01-01")) / np.timedelta64(1, "D")
    dsdt = np.full_like(lwe, np.nan)
    oi = np.where(observed)[0]
    for a, b, c in zip(oi[:-2], oi[1:-1], oi[2:]):
        if (t_days[b] - t_days[a] <= MAX_GAP_DAYS) and (t_days[c] - t_days[b] <= MAX_GAP_DAYS):
            dsdt[:, b] = (lwe[:, c] - lwe[:, a]) / (t_days[c] - t_days[a]) * 365.25

    long = pd.DataFrame({
        "mascon_id": np.repeat(sel["mascon_id"].to_numpy(), len(obs_months)),
        "month": np.tile(obs_months.to_timestamp(), n_mas),
        "solution_mid_date": np.tile(mid_full, n_mas),
        "observed": np.tile(observed, n_mas),
        "lwe_cm": lwe.ravel(),
        "noise_2sigma_cm": nz.ravel(),
        "leakage_2sigma_cm": np.repeat(leak, len(obs_months)),
        "dSdt_cm_per_yr": dsdt.ravel(),
    })
    long["mission"] = np.where(long["month"] < pd.Timestamp("2018-01-01"), "GRACE", "GRACE-FO")
    long.to_parquet(OUT / "signals" / "mascon_monthly_long.parquet", index=False)
    sel.to_csv(OUT / "signals" / "mascon_metadata.csv", index=False)

    missing = [str(p) for p, o in zip(obs_months, observed) if not o]
    (OUT / "signals" / "gaps.json").write_text(json.dumps({
        "n_mascons": int(n_mas),
        "n_months_axis": int(len(obs_months)),
        "n_observed": int(observed.sum()),
        "missing_months": missing,
        "first_month": str(obs_months[0]), "last_month": str(obs_months[-1]),
        "duplicate_solution_months": [str(r["month"]) for _, r in mrec.iterrows()
                                      if len(r["idx"]) > 1],
        "lat_window": list(LAT), "lon_window": list(LON),
    }, indent=2))
    print(f"{n_mas} land mascons, {observed.sum()}/{len(obs_months)} months observed, "
          f"{len(missing)} missing")
    print("missing:", missing)


if __name__ == "__main__":
    main()
