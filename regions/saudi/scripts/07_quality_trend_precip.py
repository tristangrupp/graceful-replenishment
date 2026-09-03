"""Signal quality, trend, inter-mission offset, and the CHIRPS precipitation control."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats
from shapely.geometry import box as shp_box

from dark_water.depletion_watchlist.depletion import trend as T
from dark_water.depletion_watchlist.depletion import precipitation as P

ROOT = Path(r"E:\Water\Saudi")
PROC, SIG, TR = ROOT / "processed", ROOT / "signals", ROOT / "trends"
TR.mkdir(parents=True, exist_ok=True)

ds = xr.open_dataset(PROC / "arabia_mascons.nc")
meta = pd.read_csv(SIG / "mascon_metadata.csv")
obs = ds["observed"].values.astype(bool)
mid = pd.to_datetime(ds["solution_mid_date"].values)[obs]
mission = ds["mission"].values.astype(str)[obs]
cm = ds["lwe_thickness"].values[:, obs]                 # (mascon, t)
nz = ds["noise_2sigma"].values[:, obs]
mid_all = pd.to_datetime(ds["solution_mid_date"].values)
mascon_id = ds["mascon"].values
n_mas, nt = cm.shape
print(f"{n_mas} mascons x {nt} observed months")

# ------------------------------------------------------------- trend (repo)
da = xr.DataArray(cm.T, dims=("time", "mascon"),
                  coords={"time": mid.to_numpy(), "mascon": mascon_id})
fit = T.fit_trend(da, dim="time", alpha=0.05)
trend = fit["trend"].values
pval = fit["p_value"].values

# ------------------------------------------- residual / noise consistency
years = T._decimal_years(da["time"])
X = T._design_matrix(years)
coef, *_ = np.linalg.lstsq(X, cm.T, rcond=None)
resid = cm.T - X @ coef                                  # (t, mascon)
resid_sd = resid.std(axis=0)
noise_sd = np.nanmean(nz, axis=1) / 2.0
amp_ann = np.hypot(coef[2], coef[3])
amp_semi = np.hypot(coef[4], coef[5])
r1 = ((resid[1:] * resid[:-1]).sum(0) / (resid[:-1] ** 2).sum(0))

# --------------------------------------------------- inter-mission offset
# Same model plus a GRACE-FO indicator. Reported, not applied: with an
# 11-month gap the step and the trend are partly collinear, so a fitted step
# is not proof of a genuine instrument bias.
step_col = (mission == "GRACE-FO").astype(float)
Xs = np.column_stack([X, step_col - step_col.mean()])
cs, *_ = np.linalg.lstsq(Xs, cm.T, rcond=None)
res_s = cm.T - Xs @ cs
dof = nt - Xs.shape[1]
sig2 = (res_s ** 2).sum(0) / dof
xtxi = np.linalg.inv(Xs.T @ Xs)
step = cs[-1]
step_se = np.sqrt(sig2 * xtxi[-1, -1])
step_p = 2 * stats.t.sf(np.abs(step / step_se), df=dof)
trend_with_step = cs[1]

# ---------------------------------------------- per-mission separate trends
def seg_trend(sel):
    d = xr.DataArray(cm[:, sel].T, dims=("time", "mascon"),
                     coords={"time": mid[sel].to_numpy(), "mascon": mascon_id})
    f = T.fit_trend(d, dim="time")
    return f["trend"].values, f["p_value"].values
tr_g, p_g = seg_trend(mission == "GRACE")
tr_f, p_f = seg_trend(mission == "GRACE-FO")

# ---------------------------------------------------------- CHIRPS control
ch = xr.open_dataset(ROOT / "raw" / "chirps_v2p0_monthly_arabia_0p5deg.nc", decode_times=False)
cper = pd.PeriodIndex([pd.Period("1960-01", "M") + int(np.floor(x)) for x in ch["T"].values], freq="M")
pr = ch["precipitation"].values / 10.0                    # mm/month -> cm/month
cy, cx = ch["Y"].values, ch["X"].values
valid_month = np.isfinite(pr).any(axis=(1, 2))
print(f"CHIRPS months {cper[0]}..{cper[-1]}; fully-empty months: {(~valid_month).sum()} "
      f"({[str(p) for p in cper[~valid_month]]})")

# mascon-mean precipitation: average CHIRPS cells whose centre lies in the mascon box
prm = np.full((n_mas, len(cper)), np.nan)
ncell = np.zeros(n_mas, int)
for i in range(n_mas):
    la, lo = meta.lat_center[i], meta.lon_center[i]
    hy, hx = meta.lat_span_deg[i] / 2, meta.lon_span_deg[i] / 2
    my = (cy >= la - hy) & (cy < la + hy)
    mx = (cx >= lo - hx) & (cx < lo + hx)
    if my.sum() and mx.sum():
        blk = pr[:, my, :][:, :, mx]
        ncell[i] = int(np.isfinite(blk[0]).sum())
        with np.errstate(invalid="ignore"):
            prm[i] = np.nanmean(blk, axis=(1, 2))
print(f"mascons with >=1 CHIRPS land cell: {(ncell > 0).sum()} / {n_mas}")

# Restrict CHIRPS to the GRACE span and accumulate on the COMPLETE monthly
# axis (storage integrates flux continuously; skipping GRACE's missing months
# would corrupt the running sum), then sample at the observed GRACE months.
span = (cper >= pd.Period("2002-04", "M")) & (cper <= pd.Period("2026-03", "M"))
cper_s, prm_s = cper[span], prm[:, span]
ok_p = np.isfinite(prm_s).all(axis=1) & (ncell > 0)
print(f"mascons with a complete CHIRPS series over 2002-04..2026-03: {ok_p.sum()}")

precip_da = xr.DataArray(
    prm_s.T, dims=("time", "mascon"),
    coords={"time": cper_s.to_timestamp(how="start").to_numpy(), "mascon": mascon_id})
cum = P.cumulative_anomaly(precip_da, dim="time")
# sample the running sum at the calendar month of each GRACE solution
gm = pd.PeriodIndex(mid, freq="M")
pos = {p: k for k, p in enumerate(cper_s)}
take = np.array([pos[p] for p in gm])
cum_at_grace = xr.DataArray(
    cum.values[take], dims=("time", "mascon"),
    coords={"time": mid.to_numpy(), "mascon": mascon_id})

adj = P.adjusted_trend(da.where(xr.DataArray(ok_p, dims="mascon")), cum_at_grace, dim="time")
print("precip-adjusted trend computed for", int(np.isfinite(adj['trend'].values).sum()), "mascons")

mean_ann_precip = np.nanmean(prm_s, axis=1) * 12 * 10     # cm/month -> mm/yr
precip_cv = np.nanstd(prm_s.reshape(n_mas, -1)[:, : (prm_s.shape[1] // 12) * 12]
                      .reshape(n_mas, -1, 12).sum(axis=2), axis=1) / \
            np.nanmean(prm_s.reshape(n_mas, -1)[:, : (prm_s.shape[1] // 12) * 12]
                       .reshape(n_mas, -1, 12).sum(axis=2), axis=1)

# ------------------------------------------------------------------ assemble
out = meta.copy()
out["trend_cm_per_yr"] = trend
out["trend_p_value"] = pval
out["significant_decline"] = (trend < 0) & (pval < 0.05)
out["trend_leakage_uncert_cm_per_yr"] = np.abs(out["leakage_trend_uncert_cm_per_yr"])
out["trend_grace_only_cm_per_yr"] = tr_g
out["trend_gracefo_only_cm_per_yr"] = tr_f
out["p_grace_only"] = p_g
out["p_gracefo_only"] = p_f
out["intermission_step_cm"] = step
out["intermission_step_se_cm"] = step_se
out["intermission_step_p"] = step_p
out["trend_with_step_term_cm_per_yr"] = trend_with_step
out["annual_amplitude_cm"] = amp_ann
out["semiannual_amplitude_cm"] = amp_semi
out["residual_sd_cm"] = resid_sd
out["noise_sd_cm"] = noise_sd
out["residual_over_noise_sd"] = resid_sd / noise_sd
out["residual_lag1_autocorr"] = r1
out["chirps_mean_annual_precip_mm"] = mean_ann_precip
out["chirps_annual_cv"] = precip_cv
out["chirps_cells"] = ncell
out["precip_adjusted_trend_cm_per_yr"] = adj["trend"].values
out["precip_adjusted_p_value"] = adj["p_value"].values
out["fraction_unexplained_by_precip"] = adj["fraction_unexplained"].values
out["precip_explained_trend_cm_per_yr"] = adj["precip_explained_trend"].values
out.to_csv(TR / "mascon_trends_and_quality.csv", index=False)

pen = out[out.on_arabian_peninsula]
print("\n--- Arabian Peninsula mascons (n=%d) ---" % len(pen))
print("trend cm/yr: median %.3f, min %.3f, max %.3f" % (pen.trend_cm_per_yr.median(),
      pen.trend_cm_per_yr.min(), pen.trend_cm_per_yr.max()))
print("significant declines: %d" % pen.significant_decline.sum())
print("residual/noise sd: median %.2f (>1 => residual exceeds reported noise)" % pen.residual_over_noise_sd.median())
print("residual lag-1 autocorr: median %.2f" % pen.residual_lag1_autocorr.median())
print("|inter-mission step|: median %.2f cm; significant at 5%%: %d/%d" % (
      pen.intermission_step_cm.abs().median(), (pen.intermission_step_p < 0.05).sum(), len(pen)))
print("annual amplitude: median %.2f cm" % pen.annual_amplitude_cm.median())
print("CHIRPS mean annual precip: median %.0f mm/yr, range %.0f-%.0f" % (
      pen.chirps_mean_annual_precip_mm.median(), pen.chirps_mean_annual_precip_mm.min(),
      pen.chirps_mean_annual_precip_mm.max()))
print("fraction unexplained by precip: median %.2f" % pen.fraction_unexplained_by_precip.median())

json.dump({
    "n_mascons": int(n_mas), "n_observed_months": int(nt),
    "peninsula": {
        "n": int(len(pen)),
        "median_trend_cm_per_yr": float(pen.trend_cm_per_yr.median()),
        "n_significant_decline": int(pen.significant_decline.sum()),
        "median_residual_over_noise": float(pen.residual_over_noise_sd.median()),
        "median_lag1_autocorr": float(pen.residual_lag1_autocorr.median()),
        "median_abs_intermission_step_cm": float(pen.intermission_step_cm.abs().median()),
        "n_significant_intermission_step": int((pen.intermission_step_p < 0.05).sum()),
        "median_fraction_unexplained_by_precip": float(pen.fraction_unexplained_by_precip.median()),
    },
}, open(TR / "summary_stats.json", "w"), indent=2)
print("\nwrote", TR / "mascon_trends_and_quality.csv")
