"""Per-mascon storage series with the seasonal and precipitation terms removed.

GLDAS is unreachable on this machine (no Earthdata credentials), so the
GRACE-minus-land-surface-model subtraction the dark-water package performs
cannot be run here. What this does instead, per mascon:

    corrected(t) = TWS(t) - [annual + semi-annual harmonics] - beta * cumulative
                   CHIRPS precipitation anomaly

fitted jointly, so the slope of `corrected` is exactly the
`precip_adjusted_trend_cm_per_yr` already in mascon_trends_and_quality.csv.

The harmonics carry the soil-moisture, vegetation and shallow-store cycle that
GLDAS would otherwise supply; the precipitation term removes the part of the
multi-year drift that the weather accounts for. Over the Arabian Peninsula
there is no snowpack and negligible surface water, so what is left is close to
groundwater -- close, not equal, and the figures say so.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"E:\Water\_shared")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D
from matplotlib.colors import TwoSlopeNorm, LinearSegmentedColormap
from region_figure import titleblock, SURFACE, INK, INK2, MUTED, AXIS

ROOT = Path(r"E:\Water\Saudi")
PROC, SIG, TR = ROOT / "processed", ROOT / "signals", ROOT / "trends"
FIG = TR / "figures"
FIG.mkdir(parents=True, exist_ok=True)

SEED = 20260807
N_SAMPLE = 30

# --------------------------------------------------------------- load GRACE
ds = xr.open_dataset(PROC / "arabia_mascons.nc")
meta = pd.read_csv(SIG / "mascon_metadata.csv")
obs = ds["observed"].values.astype(bool)
mid_all = pd.to_datetime(ds["solution_mid_date"].values)
mid = mid_all[obs]
cm = ds["lwe_thickness"].values[:, obs]  # (mascon, t) cm equivalent water height
mascon_id = ds["mascon"].values
n_mas, nt = cm.shape

# --------------------------------------------------------------- CHIRPS
ch = xr.open_dataset(ROOT / "raw" / "chirps_v2p0_monthly_arabia_0p5deg.nc", decode_times=False)
cper = pd.PeriodIndex([pd.Period("1960-01", "M") + int(np.floor(x)) for x in ch["T"].values], freq="M")
pr = ch["precipitation"].values / 10.0  # mm/month -> cm/month
cy, cx = ch["Y"].values, ch["X"].values

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

# Accumulate on the complete monthly axis -- storage integrates flux, so the
# running sum must not skip GRACE's missing months -- then sample at the
# observed GRACE solutions.
span = (cper >= pd.Period("2002-04", "M")) & (cper <= pd.Period("2026-03", "M"))
cper_s, prm_s = cper[span], prm[:, span]
ok_p = np.isfinite(prm_s).all(axis=1) & (ncell > 0)

anom = prm_s - prm_s.mean(axis=1, keepdims=True)
cum = np.cumsum(anom, axis=1)
cum = cum - cum.mean(axis=1, keepdims=True)
pos = {p: k for k, p in enumerate(cper_s)}
take = np.array([pos[p] for p in pd.PeriodIndex(mid, freq="M")])
cum_at_grace = cum[:, take]  # (mascon, t)

# --------------------------------------------------------------- joint fit
SECONDS_PER_YEAR = 365.25 * 24 * 3600
sec = mid.values.astype("datetime64[s]").astype("float64")
years = sec / SECONDS_PER_YEAR
years = years - years.mean()

base = [np.ones_like(years), years]
for period in (1.0, 0.5):
    w = 2 * np.pi / period
    base += [np.cos(w * years), np.sin(w * years)]
base = np.stack(base, axis=1)  # (t, 6): [const, trend, cos_a, sin_a, cos_s, sin_s]

corrected = np.full((n_mas, nt), np.nan)
slope = np.full(n_mas, np.nan)
for i in range(n_mas):
    if not ok_p[i]:
        continue
    X = np.column_stack([base, cum_at_grace[i]])
    c, *_ = np.linalg.lstsq(X, cm[i], rcond=None)
    # keep the intercept, the trend and the residual; drop harmonics + precip
    corrected[i] = cm[i] - X[:, 2:] @ c[2:]
    slope[i] = c[1]

pen = meta.on_arabian_peninsula.values.astype(bool)
use = pen & ok_p
print(f"{n_mas} mascons; on peninsula {pen.sum()}; with complete CHIRPS {ok_p.sum()}; plotted {use.sum()}")

# cross-check against the trend table written by 07_quality_trend_precip.py
tq = pd.read_csv(TR / "mascon_trends_and_quality.csv").set_index("mascon_id")
ref = tq.loc[mascon_id[use], "precip_adjusted_trend_cm_per_yr"].values
d = np.nanmax(np.abs(ref - slope[use]))
print(f"max |slope - precip_adjusted_trend| = {d:.2e} cm/yr")

# ---------------------------------------------------------------- write out
full = pd.DataFrame(np.nan, index=pd.PeriodIndex(mid_all, freq="M").astype(str),
                    columns=[f"m{m}" for m in mascon_id[use]])
full.loc[pd.PeriodIndex(mid, freq="M").astype(str), :] = corrected[use].T
full.index.name = "month"
full.to_csv(SIG / "peninsula_corrected_series_cmwe.csv")
print("wrote", SIG / "peninsula_corrected_series_cmwe.csv")

# -------------------------------------------------------------------- plot
# Trend has a real, meaningful zero (storage gained vs lost), so the color job
# is polarity: a diverging pair with a neutral midpoint, not a rainbow and not
# a single ramp that would hide the sign.
DIVERGING = LinearSegmentedColormap.from_list(
    "loss_gain", ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"])
tvals = slope[use]
lim = np.nanpercentile(np.abs(tvals), 98)
norm = TwoSlopeNorm(vmin=-lim, vcenter=0.0, vmax=lim)

t = mid.to_numpy()
gap = (pd.PeriodIndex(mid, freq="M")[1:] - pd.PeriodIndex(mid, freq="M")[:-1]).map(lambda x: x.n)
break_at = np.where(np.asarray(gap) > 1)[0]  # GRACE / GRACE-FO intermission


def segments(y):
    """Split a series at the mission gap so nothing is drawn across it."""
    idx = np.split(np.arange(len(t)), break_at + 1)
    return [np.column_stack([t[k].astype("datetime64[s]").astype("float64"), y[k]])
            for k in idx if len(k) > 1]


def spaghetti(ax, rows, lw, alpha):
    segs, cols = [], []
    for i in rows:
        s = segments(corrected[i])
        segs += s
        cols += [DIVERGING(norm(slope[i]))] * len(s)
    lc = LineCollection(segs, colors=cols, linewidths=lw, alpha=alpha)
    ax.add_collection(lc)
    ax.set_xlim(t[0].astype("datetime64[s]").astype("float64"),
                t[-1].astype("datetime64[s]").astype("float64"))


def date_axis(ax):
    ticks = pd.to_datetime([f"{y}-01-01" for y in range(2004, 2027, 4)])
    ax.set_xticks(ticks.values.astype("datetime64[s]").astype("float64"))
    ax.set_xticklabels([str(y) for y in range(2004, 2027, 4)])


def colorbar(fig, ax, label):
    sm = plt.cm.ScalarMappable(cmap=DIVERGING, norm=norm)
    cb = fig.colorbar(sm, ax=ax, pad=0.015, fraction=0.03)
    cb.set_label(label, color=INK2, fontsize=9)
    cb.outline.set_edgecolor(AXIS)
    cb.ax.tick_params(color=MUTED, labelcolor=MUTED, labelsize=8.5)
    return cb


rows_all = np.where(use)[0]
med = np.nanmedian(slope[use])
n_dec = int(((tq.loc[mascon_id[use], "precip_adjusted_trend_cm_per_yr"] < 0)
             & (tq.loc[mascon_id[use], "precip_adjusted_p_value"] < 0.05)).sum())

# ---- figure 1: every mascon
# 221 wiggling monthly series on one axes is mud, so the monthly data sits
# behind in near-transparent grey and the straight fitted line each mascon
# carries is drawn on top -- that line is the trend being asked for, one per
# mascon, and the grey is the record it was fitted to.
fig, ax = plt.subplots(figsize=(11.5, 6.2))
grey_segs = []
for i in rows_all:
    grey_segs += segments(corrected[i])
ax.add_collection(LineCollection(grey_segs, colors=[MUTED], linewidths=0.35, alpha=0.10))

x0, x1 = t[0].astype("datetime64[s]").astype("float64"), t[-1].astype("datetime64[s]").astype("float64")
yr0, yr1 = years[0], years[-1]
fit_lines, fit_cols = [], []
for i in rows_all:
    c0 = np.nanmean(corrected[i])
    fit_lines.append(np.array([[x0, c0 + slope[i] * yr0], [x1, c0 + slope[i] * yr1]]))
    fit_cols.append(DIVERGING(norm(slope[i])))
ax.add_collection(LineCollection(fit_lines, colors=fit_cols, linewidths=1.1, alpha=0.9, zorder=3))

band = np.nanmedian(corrected[use], axis=0)
for s in segments(band):
    ax.plot(s[:, 0], s[:, 1], color=SURFACE, lw=4.0, zorder=4)
    ax.plot(s[:, 0], s[:, 1], color=INK, lw=2.0, zorder=5)
ax.set_xlim(x0, x1)
ax.set_ylim(np.nanpercentile(corrected[use], 1.0), np.nanpercentile(corrected[use], 99.5))
ax.axhline(0, color=AXIS, lw=1.0)
ax.set_ylabel("corrected storage anomaly (cm equivalent water height)")
date_axis(ax)
handles = [Line2D([], [], color="#c86a2c", lw=1.6, label="one mascon's fitted trend"),
           Line2D([], [], color=MUTED, lw=1.0, alpha=0.5, label="the monthly series behind it"),
           Line2D([], [], color=INK, lw=2.0, label="median of all mascons")]
leg = ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True,
                facecolor=SURFACE, edgecolor=AXIS)
leg.get_frame().set_linewidth(0.8)
colorbar(fig, ax, "fitted trend (cm/yr)")
titleblock(
    fig,
    f"All {len(rows_all)} Arabian Peninsula mascons after removing season and precipitation",
    "One straight line per GSFC mascon: the trend left after subtracting that mascon's annual and semi-annual\n"
    "harmonics and its CHIRPS cumulative-precipitation term. Grey behind each is the corrected monthly series\n"
    f"the line was fitted to. Median trend {med:+.2f} cm/yr; {n_dec} of {len(rows_all)} decline significantly at 5%.\n"
    "The 2017-2018 break is the GRACE / GRACE-FO intermission, left open rather than interpolated.",
    title_size=14.5)
fig.savefig(FIG / "fig5_all_corrected_mascon_series.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

# ---- figure 2: random 30
rng = np.random.default_rng(SEED)
pick = rng.choice(rows_all, size=N_SAMPLE, replace=False)
pick = pick[np.argsort(slope[pick])]

fig, ax = plt.subplots(figsize=(11.5, 6.2))
spaghetti(ax, pick, lw=1.4, alpha=0.95)
ax.axhline(0, color=AXIS, lw=1.0)
ax.set_ylim(np.nanpercentile(corrected[pick], 0.2) - 2, np.nanpercentile(corrected[pick], 99.8) + 2)
ax.set_ylabel("corrected storage anomaly (cm equivalent water height)")
date_axis(ax)
colorbar(fig, ax, "fitted trend (cm/yr)")
smed = np.nanmedian(slope[pick])
titleblock(
    fig,
    f"A random {N_SAMPLE} of them, drawn one line at a time",
    f"Same correction, same colour scale. Sampled without replacement from the {len(rows_all)} peninsula mascons\n"
    f"with seed {SEED}; median trend of this draw {smed:+.2f} cm/yr against {med:+.2f} for the full set. Neighbouring\n"
    "mascons are not independent, so a sample of 30 is not 30 independent measurements of the peninsula.",
    title_size=14.5)
fig.savefig(FIG / "fig6_sample30_corrected_mascon_series.png", dpi=170, facecolor=SURFACE)
plt.close(fig)

cols = ["lat_center", "lon_center", "country_of_center", "trend_cm_per_yr",
        "precip_adjusted_trend_cm_per_yr", "precip_adjusted_p_value",
        "fraction_unexplained_by_precip", "leakage_trend_uncert_cm_per_yr"]
tq.loc[mascon_id[pick], cols].to_csv(TR / "sample30_mascons.csv")
print("wrote", FIG / "fig5_all_corrected_mascon_series.png")
print("wrote", FIG / "fig6_sample30_corrected_mascon_series.png")
print("wrote", TR / "sample30_mascons.csv")
print(tq.loc[mascon_id[pick], ["country_of_center", "precip_adjusted_trend_cm_per_yr",
                               "precip_adjusted_p_value"]].to_string())
