"""The Nuevo Leon decomposition with GLDAS, drawn so it cannot be misread.

The earlier SMAP figure had to claim a soil-moisture correction over ten years
and a residual whose fitted trend described a drought excursion rather than a
depletion rate. With GLDAS over the full record both problems are testable, and
the answer is a null: nothing here is a groundwater decline.

Panel A shows the four terms. Panel B shows the groundwater term alone, with
the three-model spread as a band and the leakage floor drawn -- because a
+0.48 mm/yr result inside a +/-3.27 mm/yr floor is not a small rise, it is no
measurement at all, and the figure should say so rather than let a line imply
otherwise.
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from region_figure import titleblock, SURFACE, INK, INK2, MUTED, AXIS, GRID

NL = Path(r"E:\Water\NuevoLeon")
SIG, TR = NL / "signals", NL / "trends"
FIG = TR / "figures"
FIG.mkdir(parents=True, exist_ok=True)

# dataviz categorical slots 1-4, validated for this surface: worst adjacent
# pair dE 9.1 protan / 22.9 normal. Contrast warns below 3:1, so every series
# is direct-labelled rather than relying on a legend swatch alone.
SERIES = {
    "tws": ("total water storage", "#2a78d6"),
    "reservoir": ("reservoirs", "#eb6834"),
    "soil_moisture": ("soil moisture, snow, canopy", "#1baf7a"),
    "groundwater": ("groundwater, what is left", "#eda100"),
}

s = pd.read_csv(SIG / "gldas_decomposition_series.csv", index_col=0, parse_dates=True)
bym = pd.read_csv(SIG / "gldas_groundwater_by_model.csv", index_col=0, parse_dates=True)
summ = json.load(open(TR / "gldas_decomposition_summary.json"))
fs, ex = summ["full_record"], summ["groundwater_excursion"]
floor = ex["leakage_trend_floor_mm_yr"]

fig, (ax, bx) = plt.subplots(2, 1, figsize=(11.5, 8.6), height_ratios=[1.15, 1])

# ------------------------------------------------------------------ panel A
for k, (label, col) in SERIES.items():
    ax.plot(s.index, s[k], color=col, lw=1.4, alpha=0.95)

# Direct labels sit in the margin beside the axes, not inside a padded x-range:
# extending the time axis past the last observation to make label room would
# draw four years of blank record that does not exist. Anchors are de-collided
# downward so no two overlap.
anchors = sorted(((s[k].iloc[-12:].mean(), k) for k in SERIES), reverse=True)
span = ax.get_ylim()
placed, min_gap = [], (span[1] - span[0]) * 0.145
for val, k in anchors:
    y = val if not placed else min(val, placed[-1] - min_gap)
    placed.append(y)
    label, col = SERIES[k]
    ax.annotate(f"{label}\n{fs[f'trend_{k}_mm_yr']:+.2f} mm/yr"
                + ("" if fs[f"p_{k}"] < 0.05 else "  (not significant)"),
                xy=(1.012, y), xycoords=("axes fraction", "data"),
                color=col, fontsize=9, va="center", ha="left", fontweight="bold",
                annotation_clip=False, linespacing=1.35)
ax.axhline(0, color=AXIS, lw=1.0)
ax.set_ylabel("deseasonalised anomaly (mm)")
ax.set_xlim(s.index[0], s.index[-1])
ax.set_title(f"A. Every term, {summ['window_full'][0]} to {summ['window_full'][1]}, "
             "weighted by each mascon's share of Nuevo Leon",
             loc="left", fontsize=10.5, color=INK2, pad=6)

# ------------------------------------------------------------------ panel B
lo, hi = bym.min(axis=1), bym.max(axis=1)
bx.fill_between(bym.index, lo, hi, color="#eda100", alpha=0.20, lw=0,
                label="range across NOAH, VIC and CLSM")
bx.plot(s.index, s["groundwater"], color="#eda100", lw=1.6)

pre, trough, post = ex["pre_2020_mean_mm"], ex["trough_mm"], ex["post_trough_mean_mm"]
tm = pd.Timestamp(ex["trough_month"])
for y, lab, x0, x1 in [
    (pre, f"pre-2020 mean {pre:+.1f} mm", s.index[0], pd.Timestamp("2019-12-31")),
    (post, f"since the trough ({ex['n_months_after_trough']} months) {post:+.1f} mm",
     tm + pd.Timedelta(days=30), s.index[-1]),
]:
    bx.plot([x0, x1], [y, y], color=INK, lw=1.8, zorder=6)
    bx.annotate(lab, xy=(x0 + (x1 - x0) / 2, y), xytext=(0, 7), textcoords="offset points",
                ha="center", fontsize=9, color=INK, fontweight="bold")
bx.plot([tm], [trough], marker="o", ms=7, color=INK, zorder=7)
bx.annotate(f"trough {trough:+.1f} mm, {tm:%Y-%m}\n{ex['pct_of_drop_recovered']:.0f}% of the drop already recovered",
            xy=(tm, trough), xytext=(-14, -4), textcoords="offset points",
            ha="right", va="top", fontsize=9, color=INK)

# the leakage floor, as a band around zero on the cumulative scale it implies
yrs = (s.index - s.index[0]).days / 365.25
bx.fill_between(s.index, -floor * yrs, floor * yrs, color=MUTED, alpha=0.11, lw=0)
k = int(len(s) * 0.42)
bx.annotate(f"what a trend of +/-{floor:.2f} mm/yr would look like:\nGSFC's own leakage floor for these mascons",
            xy=(s.index[k], floor * yrs[k]), xytext=(0, 10), textcoords="offset points",
            ha="center", fontsize=8.5, color=INK2)
bx.axhline(0, color=AXIS, lw=1.0)
bx.set_ylabel("groundwater anomaly (mm)")
bx.set_xlim(s.index[0], s.index[-1])
bx.legend(loc="lower left", fontsize=9, frameon=True, facecolor=SURFACE, edgecolor=AXIS)
bx.set_title(f"B. The groundwater term alone: {fs['trend_groundwater_mm_yr']:+.2f} mm/yr, p = {fs['p_groundwater']:.2f}",
             loc="left", fontsize=10.5, color=INK2, pad=6)

fig.subplots_adjust(hspace=0.30, right=0.735)
pm = summ["per_model_trends"]
titleblock(
    fig,
    "Nuevo Leon is not losing groundwater on this record",
    f"GRACE total water storage falls {abs(fs['trend_tws_mm_yr']):.2f} mm/yr over {summ['n_months_full']} months, "
    f"{summ['window_full'][0]} to {summ['window_full'][1]}. Reservoirs account for\n"
    f"{abs(fs['trend_reservoir_mm_yr']):.2f} of that and GLDAS soil moisture, snow and canopy for "
    f"{abs(fs['trend_soil_moisture_mm_yr']):.2f}. What is left is {fs['trend_groundwater_mm_yr']:+.2f} mm/yr with\n"
    f"p = {fs['p_groundwater']:.2f}, and the three models disagree on its sign "
    f"({pm['noah']['trend_groundwater_mm_yr']:+.2f} NOAH, {pm['vic']['trend_groundwater_mm_yr']:+.2f} VIC, "
    f"{pm['clsm']['trend_groundwater_mm_yr']:+.2f} CLSM). Every term here\n"
    f"is smaller than the {floor:.2f} mm/yr leakage floor. The 2022-2024 drop reached {trough:.0f} mm and has "
    f"recovered {ex['pct_of_drop_recovered']:.0f}% of itself since.",
    title_size=15, axes_title_pt=11)
fig.savefig(FIG / "fig6_gldas_decomposition.png", dpi=170, facecolor=SURFACE)
plt.close(fig)
print("wrote", FIG / "fig6_gldas_decomposition.png")
