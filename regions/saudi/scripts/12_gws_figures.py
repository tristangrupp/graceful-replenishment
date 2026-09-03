"""The two requested plots, redrawn on GRACE-minus-GLDAS groundwater storage.

Replaces fig5/fig6, which had to stand on a harmonics-and-CHIRPS substitute
because GLDAS was unreachable. Same layout, same colour scale, real
subtraction: soil moisture, snow water equivalent and canopy storage removed
per land-surface model and averaged across NOAH, VIC and CLSM.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
from matplotlib.lines import Line2D
from region_figure import titleblock, SURFACE, INK, INK2, MUTED, AXIS

ROOT = Path(r"E:\Water\Saudi")
SIG, TR = ROOT / "signals", ROOT / "trends"
FIG = TR / "figures"
SEED = 20260807
N_SAMPLE = 30

series = pd.read_csv(SIG / "peninsula_gws_ensemble_cmwe.csv", index_col=0)
tq = pd.read_csv(TR / "mascon_gws_gldas.csv").set_index("mascon_id")
ids = [int(c[1:]) for c in series.columns]
tq = tq.loc[ids]
slope = tq["gws_trend_cm_per_yr"].values
n_full = int((tq["n_models"] == 3).sum())

t = pd.PeriodIndex(series.index, freq="M").to_timestamp(how="start")
tnum = t.values.astype("datetime64[s]").astype("float64")
gapmo = np.diff(pd.PeriodIndex(series.index, freq="M").astype("int64"))
break_at = np.where(gapmo > 1)[0]
y = series.values.T  # (mascon, time)

years = tnum / (365.25 * 24 * 3600)
years = years - years.mean()

DIVERGING = LinearSegmentedColormap.from_list(
    "loss_gain", ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"])
lim = np.nanpercentile(np.abs(slope), 98)
norm = TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim)


def segments(row):
    return [np.column_stack([tnum[k], row[k]])
            for k in np.split(np.arange(len(tnum)), break_at + 1) if len(k) > 1]


def date_axis(ax):
    yrs = range(2004, 2027, 4)
    ax.set_xticks(pd.to_datetime([f"{v}-01-01" for v in yrs]).values
                  .astype("datetime64[s]").astype("float64"))
    ax.set_xticklabels([str(v) for v in yrs])
    ax.set_xlim(tnum[0], tnum[-1])


def colorbar(fig, ax):
    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=DIVERGING, norm=norm), ax=ax,
                      pad=0.015, fraction=0.03)
    cb.set_label("fitted groundwater trend (cm/yr)", color=INK2, fontsize=9)
    cb.outline.set_edgecolor(AXIS)
    cb.ax.tick_params(color=MUTED, labelcolor=MUTED, labelsize=8.5)


med = np.median(slope)
n_sig = int(tq["gws_significant_decline"].sum())
n_beats = int((np.abs(slope) > tq["gws_model_spread_cm_per_yr"].fillna(np.inf)).sum())

# ---------------------------------------------------------------- figure 1
fig, ax = plt.subplots(figsize=(11.5, 6.2))
grey = []
for i in range(len(y)):
    grey += segments(y[i])
ax.add_collection(LineCollection(grey, colors=[MUTED], linewidths=0.35, alpha=0.10))

lines, cols = [], []
for i in range(len(y)):
    c0 = np.nanmean(y[i])
    lines.append(np.array([[tnum[0], c0 + slope[i] * years[0]],
                           [tnum[-1], c0 + slope[i] * years[-1]]]))
    cols.append(DIVERGING(norm(slope[i])))
ax.add_collection(LineCollection(lines, colors=cols, linewidths=1.1, alpha=0.9, zorder=3))

band = np.nanmedian(y, axis=0)
for s in segments(band):
    ax.plot(s[:, 0], s[:, 1], color=SURFACE, lw=4.0, zorder=4)
    ax.plot(s[:, 0], s[:, 1], color=INK, lw=2.0, zorder=5)

ax.set_ylim(np.nanpercentile(y, 1.0), np.nanpercentile(y, 99.5))
ax.axhline(0, color=AXIS, lw=1.0)
ax.set_ylabel("groundwater storage anomaly (cm equivalent water height)")
date_axis(ax)
leg = ax.legend(handles=[
    Line2D([], [], color="#c86a2c", lw=1.6, label="one mascon's fitted trend"),
    Line2D([], [], color=MUTED, lw=1.0, alpha=0.5, label="the monthly series behind it"),
    Line2D([], [], color=INK, lw=2.0, label="median of all mascons")],
    loc="lower left", fontsize=9, frameon=True, facecolor=SURFACE, edgecolor=AXIS)
leg.get_frame().set_linewidth(0.8)
colorbar(fig, ax)
titleblock(
    fig,
    f"All {len(y)} Arabian Peninsula mascons, groundwater only",
    "GRACE total water storage minus GLDAS soil moisture, snow and canopy, averaged over the NOAH, VIC and\n"
    f"CLSM land-surface models. One straight line per mascon is its fitted trend. Median {med:+.2f} cm/yr;\n"
    f"{n_sig} of {len(y)} decline significantly at 5%, and {n_beats} have a trend larger than their own\n"
    f"three-model spread. {len(y) - n_full} coastal mascons have no VIC or CLSM land cell and rest on NOAH alone.",
    title_size=14.5)
fig.savefig(FIG / "fig7_all_gws_mascon_series.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# ---------------------------------------------------------------- figure 2
rng = np.random.default_rng(SEED)
pick = rng.choice(len(y), size=N_SAMPLE, replace=False)
pick = pick[np.argsort(slope[pick])]

fig, ax = plt.subplots(figsize=(11.5, 6.2))
segs, cols = [], []
for i in pick:
    s = segments(y[i])
    segs += s
    cols += [DIVERGING(norm(slope[i]))] * len(s)
ax.add_collection(LineCollection(segs, colors=cols, linewidths=1.4, alpha=0.95))
ax.axhline(0, color=AXIS, lw=1.0)
ax.set_ylim(np.nanpercentile(y[pick], 0.2) - 2, np.nanpercentile(y[pick], 99.8) + 2)
ax.set_ylabel("groundwater storage anomaly (cm equivalent water height)")
date_axis(ax)
colorbar(fig, ax)
titleblock(
    fig,
    f"A random {N_SAMPLE} of them, drawn one line at a time",
    f"Same subtraction, same colour scale. Sampled without replacement with seed {SEED}; median trend of this\n"
    f"draw {np.median(slope[pick]):+.2f} cm/yr against {med:+.2f} for all {len(y)}. Neighbouring mascons are not\n"
    "independent, so 30 lines is not 30 independent measurements of the peninsula.",
    title_size=14.5)
fig.savefig(FIG / "fig8_sample30_gws_mascon_series.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

tq.iloc[pick][["lat_center", "lon_center", "country_of_center", "tws_trend_cm_per_yr",
               "gws_trend_cm_per_yr", "gws_p_value", "gws_model_spread_cm_per_yr",
               "n_models"]].to_csv(TR / "sample30_gws.csv")
print("wrote", FIG / "fig7_all_gws_mascon_series.png")
print("wrote", FIG / "fig8_sample30_gws_mascon_series.png")
print("wrote", TR / "sample30_gws.csv")
