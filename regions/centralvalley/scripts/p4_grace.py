"""Phase 4a - GRACE signal quality over the Central Valley, GSFC native mascons,
plus an independent CSR RL06.3 cross-check.

Produces, all measured from the files:
  * monthly TWS per mascon and for the valley as a whole
  * the gap-aware dS/dt noise floor, by the same 3-point second-difference
    estimator Oregon used, so the two are comparable
  * the solution's own reported uncertainty (uncertainty/noise_2sigma) and
    leakage terms
  * trend with and without an inter-mission step at the 2017-07..2018-05 gap
  * corr(GSFC, CSR) deseasonalised - a result present in only one processing
    centre is not a result

No gain/scale factor is applied. None exists for GSFC and JPL's is not
interchangeable. Amplitudes are therefore biased LOW, which biases against
detection.
"""
import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"E:\Water\_shared")
sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from grace_region import load_region, to_monthly, deseasonalise
from dark_water.depletion_watchlist.depletion.trend import fit_trend

H5 = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
CSR = Path(r"E:\Water\Saudi\raw\csr_rl0603_mascons.nc")
OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")

LAT_RANGE, LON_RANGE = (34.8, 40.5), (-122.4, -118.6)
GAP0, GAP1 = pd.Timestamp("2017-07-01"), pd.Timestamp("2018-05-31")


def gap_aware_dsdt(df):
    """Centred difference, mm/month. NaN wherever either neighbour is absent, so
    nothing is ever differenced across the 11-month mission gap."""
    full = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    fwd, back = full.shift(-1), full.shift(1)
    out = (fwd - back) / 2.0
    out[fwd.isna() | back.isna()] = np.nan
    return out


def noise_floor(df):
    """3-point second difference x_{t-1} - 2 x_t + x_{t+1}. For white noise of
    std sigma this has std sqrt(6)*sigma. Only triples with all three months
    present are used."""
    full = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    d2 = full.shift(1) - 2 * full + full.shift(-1)
    d2[full.shift(1).isna() | full.isna() | full.shift(-1).isna()] = np.nan
    return d2.std() / np.sqrt(6.0)


def load_csr():
    ds = xr.open_dataset(CSR, decode_times=False)
    # Trap: the time attribute is spelled 'Units' with a capital U, so the CF
    # decoder skips it and every timestamp would collapse to 1970.
    t = ds["time"].values
    times = pd.Timestamp("2002-01-01") + pd.to_timedelta(t, unit="D")
    lwe = ds["lwe_thickness"]
    return ds, lwe, pd.DatetimeIndex(times)


def main():
    mascons, tws_mm, times = load_region(LAT_RANGE, LON_RANGE)
    print(f"{len(mascons)} land mascons, {len(times)} solutions "
          f"{times.min():%Y-%m} .. {times.max():%Y-%m}")

    monthly = to_monthly(tws_mm, times)
    monthly.columns = mascons.index
    monthly.to_parquet(OUT / "grace_gsfc_mascon_monthly.parquet")

    full_idx = pd.date_range(monthly.index.min(), monthly.index.max(), freq="MS")
    missing = full_idx.difference(monthly.index)
    print(f"{len(monthly)} months present, {len(missing)} absent")

    # Area-weighted valley mean over the mascons with real irrigation.
    cov = pd.read_csv(OUT / "mascon_coverage.csv")
    area = mascons["area_km2"].to_numpy()
    valley = pd.Series(np.average(monthly.to_numpy(), axis=1, weights=area),
                       index=monthly.index, name="tws_mm")

    # Irrigated-core subset: mascons above 10% irrigated.
    core_ids = cov[cov["irr_frac_pct"] >= 10]["mascon_id"].tolist()
    core_k = mascons.index[mascons["mascon_id"].isin(core_ids)].tolist()
    core = pd.Series(np.average(monthly[core_k].to_numpy(), axis=1,
                                weights=area[core_k]),
                     index=monthly.index, name="tws_mm")
    print(f"irrigated core: {len(core_k)} mascons "
          f"({', '.join(str(i) for i in core_ids)})")

    # ---------------------------------------------------------- noise floor
    nf_per = noise_floor(monthly)
    nf_valley = float(noise_floor(valley.to_frame()).iloc[0])
    nf_core = float(noise_floor(core.to_frame()).iloc[0])
    dsdt_sigma_valley = nf_valley / np.sqrt(2.0)
    dsdt_sigma_core = nf_core / np.sqrt(2.0)
    # centred difference (x_{t+1}-x_{t-1})/2 of white noise sigma has std sigma/sqrt(2)

    # -------------------------------------------- solution's own uncertainty
    with h5py.File(H5, "r") as f:
        ids = mascons["mascon_id"].to_numpy()
        unc_keys = list(f["uncertainty"].keys())
        noise2 = f["uncertainty/noise_2sigma"][ids, :]
        leak2 = f["uncertainty/leakage_2sigma"][ids, :] if "leakage_2sigma" in f["uncertainty"] else None
        leaktr = f["uncertainty/leakage_trend"][ids] if "leakage_trend" in f["uncertainty"] else None
    print("uncertainty datasets:", unc_keys)
    noise1_mm = float(np.nanmean(noise2) * 10.0 / 2.0)      # cm 2-sigma -> mm 1-sigma

    # ------------------------------------------------------------- trends
    def trend_of(series, with_step):
        s = series.dropna()
        yrs = (s.index - s.index[0]).days / 365.25
        cols = [np.ones(len(s)), yrs,
                np.cos(2 * np.pi * yrs), np.sin(2 * np.pi * yrs),
                np.cos(4 * np.pi * yrs), np.sin(4 * np.pi * yrs)]
        if with_step:
            cols.append((s.index > GAP1).astype(float))
        X = np.column_stack(cols)
        beta, *_ = np.linalg.lstsq(X, s.to_numpy(), rcond=None)
        resid = s.to_numpy() - X @ beta
        dof = len(s) - X.shape[1]
        sig2 = (resid ** 2).sum() / dof
        cov_b = sig2 * np.linalg.inv(X.T @ X)
        # lag-1 autocorrelation inflation, as in fit_trend
        r1 = np.clip(np.corrcoef(resid[1:], resid[:-1])[0, 1], -0.99, 0.99)
        n_eff = max(3.0, len(s) * (1 - r1) / (1 + r1))
        se = np.sqrt(cov_b[1, 1] * len(s) / n_eff)
        return float(beta[1]), float(se), (float(beta[-1]) if with_step else np.nan), float(r1), float(n_eff)

    tr_no, se_no, _, r1_no, neff_no = trend_of(valley, False)
    tr_st, se_st, step, r1_st, neff_st = trend_of(valley, True)
    ctr_no, cse_no, _, _, _ = trend_of(core, False)
    ctr_st, cse_st, cstep, _, _ = trend_of(core, True)

    # cross-check with the package's fit_trend on the same series
    da = xr.DataArray(valley.dropna().to_numpy(),
                      coords={"time": valley.dropna().index}, dims="time")
    ft = fit_trend(da)
    pkg_trend = float(ft["trend"]) * 1.0     # mm per year (decimal-year design)

    # --------------------------------------------------------------- CSR
    csr_res = {}
    try:
        ds, lwe, ctimes = load_csr()
        lat = ds["lat"].values
        lon = ds["lon"].values
        lon180 = ((lon + 180) % 360) - 180
        li = np.where((lat >= LAT_RANGE[0]) & (lat <= LAT_RANGE[1]))[0]
        oi = np.where((lon180 >= LON_RANGE[0]) & (lon180 <= LON_RANGE[1]))[0]
        sub = lwe.values[:, li[:, None], oi[None, :]] * 10.0    # cm -> mm
        w = np.cos(np.radians(lat[li]))[:, None] * np.ones((1, len(oi)))
        flat = sub.reshape(len(ctimes), -1)
        wf = w.ravel()
        ok = np.isfinite(flat).all(axis=0)
        csr_series = pd.Series((flat[:, ok] * wf[ok]).sum(axis=1) / wf[ok].sum(),
                               index=ctimes)
        csr_m = csr_series.groupby(csr_series.index.to_period("M").to_timestamp()).mean()
        csr_m.to_frame("tws_mm").to_parquet(OUT / "grace_csr_valley_monthly.parquet")

        both = pd.concat([deseasonalise(valley.to_frame("gsfc")),
                          deseasonalise(csr_m.to_frame("csr"))], axis=1).dropna()
        r = float(both.corr().iloc[0, 1])
        # trends of both over the common window
        def simple_trend(s):
            yrs = (s.index - s.index[0]).days / 365.25
            X = np.column_stack([np.ones(len(s)), yrs,
                                 np.cos(2 * np.pi * yrs), np.sin(2 * np.pi * yrs),
                                 np.cos(4 * np.pi * yrs), np.sin(4 * np.pi * yrs)])
            return float(np.linalg.lstsq(X, s.to_numpy(), rcond=None)[0][1])
        common = valley.index.intersection(csr_m.index)
        csr_res = {
            "n_csr_months": int(len(csr_m)),
            "csr_time_range": [str(ctimes.min().date()), str(ctimes.max().date())],
            "n_common_months": int(len(common)),
            "corr_deseasonalised_gsfc_csr": r,
            "gsfc_trend_mm_yr_common": simple_trend(valley.loc[common].dropna()),
            "csr_trend_mm_yr_common": simple_trend(csr_m.loc[common].dropna()),
            "csr_noise_floor_mm": float(noise_floor(csr_m.to_frame()).iloc[0]),
        }
    except Exception as e:
        csr_res = {"error": f"{type(e).__name__}: {e}"}

    dsdt = gap_aware_dsdt(monthly)
    dsdt.to_parquet(OUT / "grace_gsfc_dsdt.parquet")
    pd.DataFrame({"valley": valley, "core": core}).to_parquet(
        OUT / "grace_valley_series.parquet")

    summary = {
        "n_land_mascons": int(len(mascons)),
        "n_months_present": int(len(monthly)),
        "n_months_absent": int(len(missing)),
        "months_absent": [str(d.date()) for d in missing],
        "mascon_area_km2_median": float(mascons["area_km2"].median()),
        "noise_floor_per_mascon_mm_median": float(nf_per.median()),
        "noise_floor_per_mascon_mm_min": float(nf_per.min()),
        "noise_floor_per_mascon_mm_max": float(nf_per.max()),
        "noise_floor_valley_mean_mm": nf_valley,
        "noise_floor_core_mm": nf_core,
        "dsdt_sigma_valley_mm_per_month": dsdt_sigma_valley,
        "dsdt_sigma_core_mm_per_month": dsdt_sigma_core,
        "dsdt_std_measured_valley": float(gap_aware_dsdt(valley.to_frame()).std().iloc[0]),
        "dsdt_std_measured_core": float(gap_aware_dsdt(core.to_frame()).std().iloc[0]),
        "reported_noise_1sigma_mm_mean": noise1_mm,
        "trend_valley_no_step_mm_yr": tr_no, "trend_valley_no_step_se": se_no,
        "trend_valley_with_step_mm_yr": tr_st, "trend_valley_with_step_se": se_st,
        "intermission_step_mm": step,
        "trend_core_no_step_mm_yr": ctr_no, "trend_core_no_step_se": cse_no,
        "trend_core_with_step_mm_yr": ctr_st, "trend_core_with_step_se": cse_st,
        "intermission_step_core_mm": cstep,
        "lag1_autocorr_valley": r1_no, "n_eff_valley": neff_no,
        "fit_trend_package_mm_yr": pkg_trend,
        "core_mascon_ids": core_ids,
        "csr_crosscheck": csr_res,
        "oregon_dsdt_sigma_mm_per_month": 10.46,
    }
    (INV / "grace_signal_quality.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
