"""Clipped/masked half-degree field, abstraction-candidate table, and figures."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import cartopy.crs as ccrs
import cartopy.feature as cfeature

ROOT = Path(r"E:\Water\Saudi")
PROC, SIG, TR = ROOT / "processed", ROOT / "signals", ROOT / "trends"
FIG = TR / "figures"; FIG.mkdir(parents=True, exist_ok=True)
LAT0, LAT1, LON0, LON1 = 12.0, 32.0, 34.0, 60.0

# ---------------------------------------------------- 1. gridded half-degree
nc = xr.open_dataset(ROOT / "raw" / "gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd_halfdegree.nc")
sub = nc.sel(lat=slice(LAT0, LAT1), lon=slice(LON0, LON1))
lwe = sub["lwe_thickness"].where(sub["land_mask"] == 1)
grid = xr.Dataset(
    {"lwe_thickness": lwe, "land_mask": sub["land_mask"]},
    attrs=dict(
        title="GSFC RL06v2.0 half-degree LWE, Arabian box, ocean masked",
        units="cm equivalent water height",
        note=("SECONDARY PRODUCT. Every land cell here carries a unique time series, i.e. the "
              "half-degree grid is INTERPOLATED from the 1-arc-degree mascons and does not "
              "preserve mascon identity. Effective resolution is ~1 arc-degree "
              "(~12,400 km2). Use processed/arabia_mascons.nc for quantitative work."),
        land_mask_source="land_mask variable inside the GSFC file itself (not JPL's)",
        baseline="mean over 2004.0-2010.0 removed by GSFC",
        scale_factor="none applied; GSFC distributes no gain factor",
    ),
)
grid.to_netcdf(PROC / "arabia_halfdegree_landmasked.nc")
print("wrote", PROC / "arabia_halfdegree_landmasked.nc")

# ------------------------------------------------------- 2. candidate table
d = pd.read_csv(TR / "mascon_trends_and_quality.csv")
d["trend_exceeds_leakage_uncert"] = d.trend_cm_per_yr.abs() > d.trend_leakage_uncert_cm_per_yr
d["precip_control_passed"] = d.fraction_unexplained_by_precip > 0.5
d["is_candidate"] = (
    d.on_arabian_peninsula & d.significant_decline
    & d.trend_exceeds_leakage_uncert & d.precip_control_passed
)
cols = ["mascon_id", "lat_center", "lon_center", "country_of_center", "area_km2",
        "frac_area_arabian_peninsula", "trend_cm_per_yr", "trend_p_value",
        "trend_leakage_uncert_cm_per_yr", "leakage_2sigma_cm", "noise_sd_cm",
        "trend_grace_only_cm_per_yr", "trend_gracefo_only_cm_per_yr",
        "intermission_step_cm", "intermission_step_p",
        "chirps_mean_annual_precip_mm", "chirps_annual_cv",
        "precip_adjusted_trend_cm_per_yr", "fraction_unexplained_by_precip",
        "variance_snr", "residual_over_noise_sd", "residual_lag1_autocorr",
        "annual_amplitude_cm", "n_months_observed",
        "significant_decline", "trend_exceeds_leakage_uncert", "precip_control_passed",
        "is_candidate"]
cand = d[d.is_candidate].sort_values("trend_cm_per_yr")[cols]
cand["depletion_2002_2026_cm"] = cand.trend_cm_per_yr * 23.92
cand["volume_km3_per_yr"] = cand.trend_cm_per_yr / 100 * cand.area_km2 * 1e6 / 1e9
cand.to_csv(TR / "abstraction_candidates.csv", index=False)
d[cols].to_csv(TR / "all_mascons_flags.csv", index=False)
print(f"candidates: {len(cand)} of {int(d.on_arabian_peninsula.sum())} peninsula mascons; "
      f"total {cand.volume_km3_per_yr.sum():.2f} km3/yr")

# -------------------------------------------------------------- 3. figures
ds = xr.open_dataset(PROC / "arabia_mascons.nc")
months = pd.PeriodIndex(ds["month"].values, freq="M")
mid = pd.to_datetime(ds["solution_mid_date"].values)
obs = ds["observed"].values.astype(bool)
xax = np.where(obs, ds["decimal_year"].values, ds["decimal_year"].values)
CM = ds["lwe_thickness"].values
DS = ds["dSdt"].values
ids = ds["mascon"].values

def basemap(ax):
    ax.set_extent([LON0, LON1, LAT0, LAT1], ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), fc="#dce8f2", zorder=0)
    ax.add_feature(cfeature.LAND.with_scale("50m"), fc="#f7f4ee", zorder=0)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), lw=0.5, zorder=5)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), lw=0.4, ls=":", zorder=5)
    gl = ax.gridlines(draw_labels=True, lw=0.3, color="0.8"); gl.top_labels = gl.right_labels = False

# Fig 1: trend map (all box mascons) + candidate outlines
fig, axs = plt.subplots(1, 2, figsize=(15, 6.4), subplot_kw=dict(projection=ccrs.PlateCarree()))
for ax, (col, ttl, cmap, vmax) in zip(axs, [
        ("trend_cm_per_yr", "GSFC mascon TWS trend 2002-04 to 2026-03", "RdBu", 2.2),
        ("variance_snr", "variance SNR (signal/noise)", "viridis", None)]):
    basemap(ax)
    for _, r in d.iterrows():
        v = r[col]
        if col == "trend_cm_per_yr":
            c = plt.cm.RdBu((v + vmax) / (2 * vmax))
        else:
            c = plt.cm.viridis(min(np.log10(max(v, 1)) / 2.7, 1))
        ax.add_patch(Rectangle((r.lon_center - r.lon_span_deg / 2, r.lat_center - r.lat_span_deg / 2),
                               r.lon_span_deg, r.lat_span_deg, fc=c, ec="none", alpha=0.9,
                               transform=ccrs.PlateCarree(), zorder=2))
    if col == "trend_cm_per_yr":
        for _, r in d[d.is_candidate].iterrows():
            ax.add_patch(Rectangle((r.lon_center - r.lon_span_deg / 2, r.lat_center - r.lat_span_deg / 2),
                                   r.lon_span_deg, r.lat_span_deg, fc="none", ec="k", lw=0.35,
                                   transform=ccrs.PlateCarree(), zorder=4))
        sm = plt.cm.ScalarMappable(cmap="RdBu", norm=plt.Normalize(-vmax, vmax))
        plt.colorbar(sm, ax=ax, orientation="horizontal", pad=0.06, shrink=0.85,
                     label="trend (cm equivalent water height / yr)")
    else:
        sm = plt.cm.ScalarMappable(cmap="viridis", norm=matplotlib.colors.LogNorm(1, 500))
        plt.colorbar(sm, ax=ax, orientation="horizontal", pad=0.06, shrink=0.85,
                     label="variance SNR (signal var / noise var)")
    ax.set_title(ttl, fontsize=10)
axs[0].text(0.01, -0.16, "black outline = abstraction candidate (peninsula, significant, "
            "> leakage uncert, precip control passed)", transform=axs[0].transAxes, fontsize=7)
fig.savefig(FIG / "fig1_trend_and_snr_map.png", dpi=145, bbox_inches="tight")
plt.close(fig)

# Fig 2: peninsula regional series + uncertainty + gap + dS/dt
reg = pd.read_csv(SIG / "regional_mean_series.csv")
fig, axs = plt.subplots(2, 1, figsize=(12, 7), sharex=True,
                        gridspec_kw=dict(height_ratios=[2, 1]))
x = reg.decimal_year.values
y = reg.arabian_peninsula_lwe_cm.values
u = reg.arabian_peninsula_uncert95_cm.values
axs[0].fill_between(x, y - u, y + u, color="C0", alpha=0.25, lw=0, label="GSFC 95% regional uncertainty")
axs[0].plot(x, y, ".-", color="C0", ms=3, lw=0.8, label="area-weighted mean, 222 peninsula mascons")
axs[0].axvspan(2017.44, 2018.46, color="0.85", zorder=0)
axs[0].text(2017.95, axs[0].get_ylim()[1], "GRACE / GRACE-FO gap\n(370 d, not interpolated)",
            ha="center", va="top", fontsize=7)
sl = np.isfinite(y)
c = np.polyfit(x[sl], y[sl], 1)
axs[0].plot(x, np.polyval(c, x), "k--", lw=1,
            label=f"OLS reference line {c[0]:+.3f} cm/yr")
axs[0].set_ylabel("TWS anomaly (cm EWH)\nbaseline 2004.0-2010.0")
axs[0].legend(fontsize=8); axs[0].grid(alpha=0.3)
axs[0].set_title("Arabian Peninsula GRACE/GRACE-FO total water storage, GSFC RL06v2.0 mascons", fontsize=11)

pen_mask = d.on_arabian_peninsula.values
w = d.area_km2.values[pen_mask]; w = w / w.sum()
ds_reg = np.nansum(DS[pen_mask] * w[:, None], axis=0)
ds_reg[np.all(~np.isfinite(DS[pen_mask]), axis=0)] = np.nan
axs[1].axhline(0, color="k", lw=0.6)
axs[1].plot(x, ds_reg, ".-", color="C3", ms=3, lw=0.7)
axs[1].axvspan(2017.44, 2018.46, color="0.85", zorder=0)
axs[1].set_ylabel("dS/dt (cm/yr)"); axs[1].set_xlabel("year"); axs[1].grid(alpha=0.3)
axs[1].set_title("flux form: centred difference of the storage anomaly "
                 "(NaN across every gap, never interpolated)", fontsize=9)
fig.tight_layout(); fig.savefig(FIG / "fig2_peninsula_series_and_flux.png", dpi=145)
plt.close(fig)

# Fig 3: top mascon hydrographs + CHIRPS
top = cand.head(4)
fig, axs = plt.subplots(4, 1, figsize=(12, 11), sharex=True)
ch = xr.open_dataset(ROOT / "raw" / "chirps_v2p0_monthly_arabia_0p5deg.nc", decode_times=False)
cper = pd.PeriodIndex([pd.Period("1960-01", "M") + int(np.floor(v)) for v in ch["T"].values], freq="M")
pr = ch["precipitation"].values / 10.0
cy, cx = ch["Y"].values, ch["X"].values
for ax, (_, r) in zip(axs, top.iterrows()):
    k = int(np.where(ids == r.mascon_id)[0][0])
    ax.plot(x, CM[k], ".-", ms=3, lw=0.8, color="C0")
    n = ds["noise_2sigma"].values[k]
    ax.fill_between(x, CM[k] - n / 2, CM[k] + n / 2, color="C0", alpha=0.2, lw=0)
    ax.axvspan(2017.44, 2018.46, color="0.85", zorder=0)
    sl = np.isfinite(CM[k]); cc = np.polyfit(x[sl], CM[k][sl], 1)
    ax.plot(x, np.polyval(cc, x), "k--", lw=1)
    ax2 = ax.twinx()
    my = (cy >= r.lat_center - 0.5) & (cy < r.lat_center + 0.5)
    mx = (cx >= r.lon_center - 0.55) & (cx < r.lon_center + 0.55)
    p = np.nanmean(pr[:, my, :][:, :, mx], axis=(1, 2))
    span = (cper >= pd.Period("2002-04", "M")) & (cper <= pd.Period("2026-03", "M"))
    ps = p[span]; cum = np.cumsum(ps - np.nanmean(ps))
    cxax = np.array([q.year + (q.month - 0.5) / 12 for q in cper[span]])
    ax2.plot(cxax, cum, color="C2", lw=1.2, alpha=0.8)
    ax2.set_ylabel("CHIRPS cumulative\nprecip anomaly (cm)", color="C2", fontsize=8)
    ax2.tick_params(axis="y", colors="C2", labelsize=7)
    ax.set_ylabel("cm EWH", fontsize=9)
    ax.grid(alpha=0.3)
    ax.set_title(f"mascon {int(r.mascon_id)}  {r.lat_center:.0f}N {r.lon_center:.2f}E  "
                 f"{r.country_of_center}  |  trend {r.trend_cm_per_yr:+.2f} cm/yr "
                 f"(GSFC leakage trend uncert +/-{r.trend_leakage_uncert_cm_per_yr:.2f}), "
                 f"CHIRPS {r.chirps_mean_annual_precip_mm:.0f} mm/yr, "
                 f"unexplained by precip {r.fraction_unexplained_by_precip:.2f}", fontsize=8.5)
axs[-1].set_xlabel("year")
fig.suptitle("Four strongest abstraction candidates: storage (blue, +/-1sigma noise) vs "
             "CHIRPS cumulative precipitation anomaly (green)", fontsize=11)
fig.tight_layout(rect=[0, 0, 1, 0.975])
fig.savefig(FIG / "fig3_top_candidate_hydrographs.png", dpi=145)
plt.close(fig)

# Fig 4: signal-quality diagnostics
fig, axs = plt.subplots(1, 3, figsize=(15, 4.3))
pen = d[d.on_arabian_peninsula]
axs[0].scatter(pen.noise_sd_cm, pen.residual_sd_cm, s=12, c=pen.trend_cm_per_yr,
               cmap="RdBu", vmin=-2.2, vmax=2.2, ec="k", lw=0.2)
lim = [0, max(pen.residual_sd_cm.max(), pen.noise_sd_cm.max()) * 1.1]
axs[0].plot(lim, lim, "k--", lw=1, label="1:1")
axs[0].set_xlabel("GSFC noise sigma (cm)"); axs[0].set_ylabel("residual sd after trend+harmonics (cm)")
axs[0].set_title("residual vs reported solution noise", fontsize=9); axs[0].legend(fontsize=8)
axs[1].hist(pen.residual_lag1_autocorr, bins=30, color="C0")
axs[1].set_xlabel("residual lag-1 autocorrelation"); axs[1].set_ylabel("mascons")
axs[1].set_title("serial correlation (drives the Dawdy-Matalas p-value correction)", fontsize=9)
axs[2].scatter(pen.chirps_mean_annual_precip_mm, pen.trend_cm_per_yr, s=12,
               c=pen.fraction_unexplained_by_precip, cmap="magma_r", vmin=0, vmax=1.2, ec="k", lw=0.2)
axs[2].axhline(0, color="k", lw=0.6)
axs[2].set_xlabel("CHIRPS mean annual precipitation (mm/yr)"); axs[2].set_ylabel("trend (cm/yr)")
axs[2].set_title("trend vs aridity; colour = fraction unexplained by precip", fontsize=9)
plt.colorbar(axs[2].collections[0], ax=axs[2], label="fraction unexplained")
for a in axs: a.grid(alpha=0.3)
fig.tight_layout(); fig.savefig(FIG / "fig4_signal_quality.png", dpi=145)
plt.close(fig)

print("figures:", [p.name for p in sorted(FIG.glob('*.png'))])
json.dump({"n_candidates": int(len(cand)),
           "candidate_volume_km3_per_yr": float(cand.volume_km3_per_yr.sum()),
           "candidate_area_km2": float(cand.area_km2.sum())},
          open(TR / "candidate_summary.json", "w"), indent=2)
