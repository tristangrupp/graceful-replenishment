"""Gap-aware dS/dt over Nuevo Leon, and its summary statistics.

GRACE measures a storage state; its time derivative is the flux that closes
dS/dt = P - ET - runoff - net abstraction. `02_build_signals.py` computes a
centred difference only where both neighbouring solutions lie within 80 days
of the centre epoch, so no derivative is manufactured across the
2017-07..2018-05 mission gap or any of the other 22 missing months.

Month-to-month differencing amplifies noise enormously, so only the
13-month centred mean is interpretable; both are written out.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"E:\Water\NuevoLeon")
SIG, TR = ROOT / "signals", ROOT / "trends"

if __name__ == "__main__":
    long = pd.read_parquet(SIG / "mascon_monthly_long.parquet")
    g = pd.read_csv(TR / "post2020_gradient.csv")
    w = dict(zip(g["mascon_id"], g["area_km2"] * np.nan_to_num(g["nl_area_frac"])))
    d = long.dropna(subset=["dSdt_cm_per_yr"]).assign(
        w=lambda x: x["mascon_id"].map(w))
    ser = (d.assign(x=d["dSdt_cm_per_yr"] * d["w"]).groupby("month")["x"].sum()
           / d.groupby("month")["w"].sum()) * 10.0                      # cm -> mm
    out = pd.DataFrame({"dSdt_mm_per_yr": ser,
                        "dSdt_mm_per_yr_13mo": ser.rolling(13, center=True,
                                                           min_periods=7).mean()})
    out.to_csv(SIG / "dsdt_nuevo_leon.csv")
    sm = out["dSdt_mm_per_yr_13mo"]
    summary = {
        "n_months_with_dSdt": int(len(ser)),
        "n_grace_months": int(long["observed"].groupby(long["month"]).first().sum()),
        "max_gap_days_allowed": 80,
        "monthly_sd_mm_per_yr": float(ser.std()),
        "mean_grace_era_mm_per_yr": float(ser[ser.index < "2018-01-01"].mean()),
        "mean_gracefo_era_mm_per_yr": float(ser[ser.index >= "2018-06-01"].mean()),
        "smoothed_min_mm_per_yr": float(sm.min()),
        "smoothed_min_month": str(sm.idxmin().date()),
        "smoothed_max_mm_per_yr": float(sm.max()),
        "smoothed_mean_drought_window_mm_per_yr": float(sm.loc["2022-07":"2023-04"].mean()),
        "smoothed_mean_2020_on_mm_per_yr": float(sm.loc["2020-01":].mean()),
    }
    (TR / "dsdt_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
