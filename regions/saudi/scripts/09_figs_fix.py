from pathlib import Path
import numpy as np, pandas as pd, xarray as xr
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from matplotlib.colors import Normalize, LogNorm
import cartopy.crs as ccrs, cartopy.feature as cfeature

ROOT = Path(r"E:\Water\Saudi"); PROC, SIG, TR = ROOT/"processed", ROOT/"signals", ROOT/"trends"
FIG = TR/"figures"
LAT0, LAT1, LON0, LON1 = 12.0, 32.0, 34.0, 60.0
d = pd.read_csv(TR/"all_mascons_flags.csv")
d2 = pd.read_csv(TR/"mascon_trends_and_quality.csv")
d["lat_span_deg"] = d2.lat_span_deg; d["lon_span_deg"] = d2.lon_span_deg
d["on_arabian_peninsula"] = d2.on_arabian_peninsula

def basemap(ax):
    ax.set_extent([LON0, LON1, LAT0, LAT1], ccrs.PlateCarree())
    ax.add_feature(cfeature.OCEAN.with_scale("50m"), fc="#dbe7f3", zorder=0)
    ax.add_feature(cfeature.LAND.with_scale("50m"), fc="#f6f3ec", zorder=0)
    ax.add_feature(cfeature.COASTLINE.with_scale("50m"), lw=0.6, zorder=6)
    ax.add_feature(cfeature.BORDERS.with_scale("50m"), lw=0.45, ls=":", zorder=6)
    gl = ax.gridlines(draw_labels=True, lw=0.3, color="0.8"); gl.top_labels = gl.right_labels = False
    gl.xlabel_style = gl.ylabel_style = {"size": 7}

fig = plt.figure(figsize=(15.5, 7.2))
specs = [(0.045, "trend_cm_per_yr", "RdBu", Normalize(-2.2, 2.2),
          "TWS trend (cm EWH / yr), 2002-04 to 2026-03",
          "GSFC RL06v2.0 mascon trend\nblack outline = abstraction candidate"),
         (0.525, "variance_snr", "viridis", LogNorm(1, 500),
          "variance SNR  (signal variance / GSFC noise variance)",
          "Signal-to-noise: solution noise is not the limiting factor")]
for x0, col, cmap, norm, cbl, ttl in specs:
    ax = fig.add_axes([x0, 0.18, 0.43, 0.74], projection=ccrs.PlateCarree())
    basemap(ax)
    cm = plt.get_cmap(cmap)
    for _, r in d.iterrows():
        ax.add_patch(Rectangle((r.lon_center - r.lon_span_deg/2, r.lat_center - r.lat_span_deg/2),
                               r.lon_span_deg, r.lat_span_deg, fc=cm(norm(r[col])), ec="none",
                               alpha=0.92, transform=ccrs.PlateCarree(), zorder=2))
    if col == "trend_cm_per_yr":
        for _, r in d[d.is_candidate].iterrows():
            ax.add_patch(Rectangle((r.lon_center - r.lon_span_deg/2, r.lat_center - r.lat_span_deg/2),
                                   r.lon_span_deg, r.lat_span_deg, fc="none", ec="k", lw=0.4,
                                   transform=ccrs.PlateCarree(), zorder=5))
    ax.set_title(ttl, fontsize=10)
    cax = fig.add_axes([x0 + 0.05, 0.085, 0.33, 0.022])
    plt.colorbar(plt.cm.ScalarMappable(cmap=cmap, norm=norm), cax=cax,
                 orientation="horizontal", label=cbl)
    cax.tick_params(labelsize=8); cax.xaxis.label.set_size(8)
fig.text(0.5, 0.015, "Every coloured cell is one native GSFC 1-arc-degree equal-area mascon "
         "(~12,400 km2), land mascons only (GSFC location code 80). No gain/scale factor applied "
         "\u2014 GSFC does not distribute one, so basin amplitudes are biased low.",
         ha="center", fontsize=7.5)
fig.savefig(FIG/"fig1_trend_and_snr_map.png", dpi=145)
plt.close(fig)

# ---- fig2 with a smoothed flux panel
ds = xr.open_dataset(PROC/"arabia_mascons.nc")
x = ds["decimal_year"].values; DS = ds["dSdt"].values
reg = pd.read_csv(SIG/"regional_mean_series.csv")
y = reg.arabian_peninsula_lwe_cm.values; u = reg.arabian_peninsula_uncert95_cm.values
pen = d.on_arabian_peninsula.values
w = d2.area_km2.values[pen]; w = w/w.sum()
ds_reg = np.nansum(DS[pen]*w[:, None], axis=0)
ds_reg[np.all(~np.isfinite(DS[pen]), axis=0)] = np.nan
sm13 = pd.Series(ds_reg).rolling(13, center=True, min_periods=7).mean().to_numpy()

fig, axs = plt.subplots(2, 1, figsize=(12.5, 7.4), sharex=True, gridspec_kw=dict(height_ratios=[2, 1.15]))
axs[0].fill_between(x, y-u, y+u, color="C0", alpha=0.25, lw=0, label="GSFC 95% regional uncertainty")
axs[0].plot(x, y, ".-", color="C0", ms=3, lw=0.8, label="area-weighted mean, 222 peninsula mascons")
axs[0].axvspan(2017.44, 2018.46, color="0.85", zorder=0)
axs[0].text(2017.95, 4.6, "GRACE / GRACE-FO gap\n370 d, not interpolated", ha="center", va="top", fontsize=7)
sl = np.isfinite(y); c = np.polyfit(x[sl], y[sl], 1)
axs[0].plot(x, np.polyval(c, x), "k--", lw=1, label=f"OLS reference {c[0]:+.3f} cm/yr")
g = sl & (x < 2017.5); f_ = sl & (x > 2018.4)
cg, cf = np.polyfit(x[g], y[g], 1), np.polyfit(x[f_], y[f_], 1)
axs[0].plot(x[g], np.polyval(cg, x[g]), color="C1", lw=1.4, label=f"GRACE era {cg[0]:+.3f} cm/yr")
axs[0].plot(x[f_], np.polyval(cf, x[f_]), color="C3", lw=1.4, label=f"GRACE-FO era {cf[0]:+.3f} cm/yr")
axs[0].set_ylabel("TWS anomaly (cm EWH)\nbaseline 2004.0\u20132010.0")
axs[0].legend(fontsize=8, ncol=2); axs[0].grid(alpha=0.3)
axs[0].set_title("Arabian Peninsula total water storage \u2014 GSFC RL06v2.0 native mascons, 222 land mascons", fontsize=11)
axs[1].axhline(0, color="k", lw=0.6)
axs[1].plot(x, ds_reg, ".", color="0.65", ms=3, label="monthly dS/dt (centred difference)")
axs[1].plot(x, sm13, "-", color="C3", lw=1.8, label="13-month centred mean")
axs[1].axvspan(2017.44, 2018.46, color="0.85", zorder=0)
axs[1].set_ylabel("dS/dt (cm/yr)"); axs[1].set_xlabel("year"); axs[1].grid(alpha=0.3)
axs[1].legend(fontsize=8, ncol=2)
axs[1].set_title("Flux form. Month-to-month differencing amplifies noise ~40x relative to the trend; "
                 "the smoothed curve is the interpretable one. NaN across every gap.", fontsize=8.5)
fig.tight_layout(); fig.savefig(FIG/"fig2_peninsula_series_and_flux.png", dpi=145); plt.close(fig)
print("ok", np.nanmean(sm13[x < 2017.5]), np.nanmean(sm13[x > 2018.4]))
