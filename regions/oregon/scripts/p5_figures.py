"""Phase 5: figures.

Palette: dataviz reference categorical slots 1-3 (blue/orange/aqua), validated
all-pairs light mode (worst CVD dE 9.2, normal-vision 24.0). Aqua carries a
contrast WARN vs the light surface, so every series is direct-labelled or
legended rather than identified by colour alone. One y-axis per panel; where
two measures of different scale are shown they become separate panels, never a
dual axis.
"""
import sys
import numpy as np
import pandas as pd
import xarray as xr
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion.trend import _decimal_years, _design_matrix

P = r"E:\Water\Oregan\analysis\processed"
S = r"E:\Water\Oregan\analysis\signals"
T = r"E:\Water\Oregan\analysis\trends"
NC = r"E:\Water\Oregan\analysis\raw\gsfc_mascons_halfdegree.nc"

C1, C2, C3 = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8a8880"
SURF = "#fcfcfb"
OR_BOX = dict(lon0=-124.6, lon1=-116.4, lat0=41.9, lat1=46.3)

plt.rcParams.update({
    "figure.facecolor": SURF, "axes.facecolor": SURF, "savefig.facecolor": SURF,
    "axes.edgecolor": MUTED, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": INK2, "ytick.color": INK2, "font.size": 9,
    "axes.grid": True, "grid.color": "#e6e5e1", "grid.linewidth": 0.6,
    "axes.spines.top": False, "axes.spines.right": False,
    "legend.frameon": False, "figure.dpi": 140,
})


def tidy(ax):
    ax.set_axisbelow(True)
    ax.tick_params(length=3, width=0.6)


# ------------------------------------------------------------------ fig 1
def fig_dilution():
    d = pd.read_parquet(rf"{P}\dilution_chain.parquet")
    order = ["pixel_0.5deg", "block_1deg", "footprint_300km", "oregon_box"]
    lab = ["0.5° pixel\n2,157 km²", "1° block\n8,666 km²",
           "300 km footprint\n66,860 km²", "Oregon box\n305,643 km²"]
    d = d.set_index("footprint").loc[order].reset_index()
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6))
    x = np.arange(len(d))
    for ax, col, ttl, c, unit in [
            (axes[0], "irr_frac_pct", "Irrigated share of footprint", C1, "%"),
            (axes[1], "cu_mm_yr", "Consumptive use spread over footprint", C2, " mm/yr")]:
        ax.bar(x, d[col], width=0.6, color=c, zorder=3)
        for xi, v in zip(x, d[col]):
            ax.text(xi, v, f"{v:,.1f}{unit}", ha="center", va="bottom",
                    fontsize=8.5, color=INK)
        ax.set_xticks(x); ax.set_xticklabels(lab, fontsize=8)
        ax.set_title(ttl, color=INK, fontsize=10, loc="left")
        ax.set_ylim(0, d[col].max() * 1.22)
        tidy(ax)
    axes[0].set_ylabel("percent of footprint area")
    axes[1].set_ylabel("mm per year")
    fig.suptitle("Irrigation signal dilutes ~10× from a single pixel to GRACE's real footprint",
                 fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(rf"{T}\fig1_dilution_chain.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ fig 2
def fig_grace_series():
    g = pd.read_parquet(rf"{P}\grace_oregon_series.parquet")
    g["time"] = pd.to_datetime(g["time"])
    per = pd.PeriodIndex(g["time"], freq="M")
    full = pd.period_range(per.min(), per.max(), freq="M")
    gg = g.set_index(per).reindex(full)          # NaN in missing months = real gaps
    t = gg.index.to_timestamp()

    fig, axes = plt.subplots(2, 1, figsize=(9.6, 5.4), sharex=True)
    ax = axes[0]
    ax.plot(t, gg["oregon_land_mm"], color=C1, lw=1.6, label="Oregon land TWS")
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.axvspan(pd.Timestamp("2017-07-01"), pd.Timestamp("2018-06-01"),
               color="#efeeea", zorder=0)
    ax.annotate("GRACE → GRACE-FO\n11-month gap",
                xy=(pd.Timestamp("2017-12-15"), -150),
                xytext=(pd.Timestamp("2012-06-01"), -205),
                ha="center", fontsize=8, color=INK2,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))
    ax.set_ylabel("TWS anomaly (mm)")
    ax.set_title("GSFC mascon total water storage, Oregon land pixels "
                 "(baseline 2004–2009)", fontsize=10, color=INK, loc="left")
    tidy(ax)

    ax = axes[1]
    ax.plot(t, gg["oregon_land_mm"].pipe(lambda s: s.shift(-1) - s.shift(1)) / 2,
            color=C2, lw=1.3)
    ax.axhline(0, color=MUTED, lw=0.8)
    ax.axhspan(-10.46, 10.46, color="#f3ece8", zorder=0)
    ax.annotate("±1σ measurement noise (10.5 mm/mo)",
                xy=(t[30], -8), xytext=(t[26], -62), fontsize=8, color=INK2,
                arrowprops=dict(arrowstyle="->", color=MUTED, lw=0.8))
    ax.axvspan(pd.Timestamp("2017-07-01"), pd.Timestamp("2018-06-01"),
               color="#efeeea", zorder=0)
    ax.set_ylabel("dS/dt (mm/month)")
    ax.set_title("Storage flux dS/dt — gap-aware centred difference; "
                 "no value spans a missing month", fontsize=10, color=INK, loc="left")
    tidy(ax)
    fig.tight_layout()
    fig.savefig(rf"{T}\fig2_grace_series.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ fig 3
def fig_decorrelation():
    ds = xr.open_dataset(NC)
    lwe = ds["lwe_thickness"] * 10.0
    land = ds["land_mask"]
    lwe = lwe.assign_coords(lon=(((lwe.lon + 180) % 360) - 180)).sortby("lon")
    land = land.assign_coords(lon=(((land.lon + 180) % 360) - 180)).sortby("lon")
    b = dict(lon0=-127.6, lon1=-113.4, lat0=38.9, lat1=49.3)
    sub = lwe.sel(lon=slice(b["lon0"], b["lon1"]), lat=slice(b["lat0"], b["lat1"])).load()
    lnd = land.sel(lon=slice(b["lon0"], b["lon1"]),
                   lat=slice(b["lat0"], b["lat1"])).load().values > 0
    months = sub.time.values.astype("datetime64[M]").astype("datetime64[ns]")
    sub = sub.assign_coords(time=months).groupby("time").mean("time")
    x = _design_matrix(_decimal_years(sub.time))
    flat = sub.values.reshape(sub.shape[0], -1)
    cf, *_ = np.linalg.lstsq(x, flat, rcond=None)
    anom = (flat - x @ cf).reshape(sub.shape)
    latv, lonv = sub.lat.values, sub.lon.values
    li, lj = np.where(lnd)
    ser = anom[:, li, lj]; ser = ser - ser.mean(axis=0)
    sd = ser.std(axis=0)
    C = (ser.T @ ser) / sub.shape[0] / np.outer(sd, sd)
    la = np.radians(latv[li])
    dx = (lonv[lj][None, :] - lonv[lj][:, None]) * 111.0 * np.cos(la[:, None])
    dy = (latv[li][None, :] - latv[li][:, None]) * 111.0
    D = np.hypot(dx, dy)
    iu = np.triu_indices(len(li), k=1)
    dd, cc = D[iu], C[iu]
    edges = np.arange(0, 1050, 50)
    mid = 0.5 * (edges[:-1] + edges[1:])
    mean = [cc[(dd >= edges[k]) & (dd < edges[k + 1])].mean() for k in range(len(mid))]

    fig, ax = plt.subplots(figsize=(7.2, 4.0))
    ax.plot(mid, mean, color=C1, lw=2.0, marker="o", ms=4)
    for y, lb in [(0.7, "r = 0.7 at ~186 km"), (0.5, "r = 0.5 at ~281 km")]:
        ax.axhline(y, color=MUTED, lw=0.8, ls=":")
        ax.text(980, y + 0.015, lb, ha="right", fontsize=8, color=INK2)
    ax.axvspan(0, 55.7, color="#e8effa", zorder=0)
    ax.text(60, 0.12, "one 0.5° pixel\n(~50 km)", fontsize=8, color=INK2)
    ax.set_xlabel("separation between pixels (km)")
    ax.set_ylabel("mean correlation of TWS anomalies")
    ax.set_title("Neighbouring mascon pixels are not independent measurements",
                 fontsize=10.5, color=INK, loc="left")
    ax.set_xlim(0, 1000); ax.set_ylim(0, 1.02)
    tidy(ax)
    fig.tight_layout()
    fig.savefig(rf"{T}\fig3_decorrelation.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ fig 4
def fig_key_result():
    f = pd.read_parquet(rf"{S}\flux_series.parquet")
    m = f[f.footprint == "footprint_300km"].dropna(
        subset=["dSdt_ds", "cu_ds", "ppt_ds"])

    def resid(a, b):
        A = np.column_stack([np.ones(len(b)), b])
        c, *_ = np.linalg.lstsq(A, a, rcond=None)
        return a - A @ c

    rx = resid(m.dSdt_ds.values, m.ppt_ds.values)
    ry = resid(m.cu_ds.values, m.ppt_ds.values)
    r_raw = np.corrcoef(m.dSdt_ds, -m.cu_ds)[0, 1]
    r_par = np.corrcoef(rx, -ry)[0, 1]

    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.2))
    for ax, X, Y, ttl, sub_, r, c in [
        (axes[0], -m.cu_ds.values, m.dSdt_ds.values,
         "Before controlling for precipitation",
         f"r = {r_raw:+.3f},  p = 0.026", r_raw, C2),
        (axes[1], -ry, rx,
         "After removing the precipitation pathway",
         f"partial r = {r_par:+.3f},  p = 0.30", r_par, C1)]:
        ax.scatter(X, Y, s=16, color=c, alpha=0.65, linewidths=0, zorder=3)
        b1, b0 = np.polyfit(X, Y, 1)
        xs = np.linspace(X.min(), X.max(), 50)
        ax.plot(xs, b0 + b1 * xs, color=INK, lw=1.4, zorder=4)
        ax.axhline(0, color=MUTED, lw=0.7); ax.axvline(0, color=MUTED, lw=0.7)
        ax.set_xlabel("−CU anomaly (mm/month)")
        ax.set_title(ttl, fontsize=10, color=INK, loc="left")
        ax.text(0.03, 0.96, sub_, transform=ax.transAxes, va="top",
                fontsize=9, color=INK2)
        tidy(ax)
    axes[0].set_ylabel("dS/dt anomaly (mm/month)")
    axes[1].set_ylabel("dS/dt residual after removing P (mm/month)")
    fig.suptitle("The apparent consumptive-use signal is precipitation covariance, not abstraction",
                 fontsize=11, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.93])
    fig.savefig(rf"{T}\fig4_key_result.png", bbox_inches="tight")
    plt.close(fig)


# ------------------------------------------------------------------ fig 5
def fig_seasonal():
    f = pd.read_parquet(rf"{S}\flux_series.parquet")
    m = f[f.footprint == "footprint_300km"].copy()
    m["mon"] = pd.DatetimeIndex(m["time"]).month
    cu = m.groupby("mon")["cu"].mean()
    ds = m.groupby("mon")["dSdt"].mean()
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.6), sharex=True)
    mn = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"]
    axes[0].bar(cu.index, cu.values, color=C2, width=0.62, zorder=3)
    axes[0].set_title("Consumptive use climatology", fontsize=10, color=INK, loc="left")
    axes[0].set_ylabel("mm/month")
    axes[1].bar(ds.index, ds.values, color=C1, width=0.62, zorder=3)
    axes[1].axhline(0, color=MUTED, lw=0.8)
    axes[1].set_title("GRACE dS/dt climatology", fontsize=10, color=INK, loc="left")
    axes[1].set_ylabel("mm/month")
    for ax in axes:
        ax.set_xticks(range(1, 13)); ax.set_xticklabels(mn)
        tidy(ax)
    fig.suptitle("CU peaks exactly when storage drains fastest — a shared seasonal cycle, "
                 "not a causal link (raw r = +0.85)",
                 fontsize=10.5, color=INK, x=0.01, ha="left")
    fig.tight_layout(rect=[0, 0, 1, 0.92])
    fig.savefig(rf"{T}\fig5_seasonality.png", bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    fig_dilution();      print("fig1 ok")
    fig_grace_series();  print("fig2 ok")
    fig_decorrelation(); print("fig3 ok")
    fig_key_result();    print("fig4 ok")
    fig_seasonal();      print("fig5 ok")
