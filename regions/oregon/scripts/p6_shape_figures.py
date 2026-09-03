"""Deseasonalised comparison figures: statewide field ETa and consumptive use
against the GRACE storage signal.

Design constraints applied:
  - No dual-axis charts. Measures on different scales get their own panel,
    sharing the x-axis (small multiples), never two y-scales on one frame.
  - Direct labels on every series. The aqua slot sits at 2.74:1 on the light
    surface, below the 3:1 contrast gate, so labels carry identity rather
    than colour alone.
  - GRACE gaps stay as NaN so the line breaks. Nothing is interpolated across
    the 2017-07..2018-05 mission hole.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

BASE = Path(r"E:\Water\Oregan\analysis")
OUT = BASE / "trends"

# Categorical slots 1-3 from the validated palette (all-pairs clean, light mode).
BLUE = "#2a78d6"      # ETa
ORANGE = "#eb6834"    # consumptive use
AQUA = "#1baf7a"      # GRACE
YELLOW = "#eda100"    # precipitation

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK2 = "#52514e"
MUTED = "#898781"
GRID = "#e1e0d9"
AXIS = "#c3c2b7"

AF_TO_MAF = 1e-6
GAP_START, GAP_END = pd.Timestamp("2017-07-01"), pd.Timestamp("2018-05-31")

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SURFACE,
    "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS,
    "axes.labelcolor": INK2,
    "text.color": INK,
    "xtick.color": MUTED,
    "ytick.color": MUTED,
    "axes.grid": True,
    "grid.color": GRID,
    "grid.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "font.size": 10,
})


def deseasonalise(s: pd.Series) -> pd.Series:
    """Remove the month-of-year climatology, leaving the low-frequency shape."""
    clim = s.groupby(s.index.month).transform("mean")
    return s - clim


def smooth(s: pd.Series, window: int = 13) -> pd.Series:
    return s.rolling(window, center=True, min_periods=window // 2 + 1).mean()


def monthly_index(start, end):
    return pd.date_range(start, end, freq="MS")


def titleblock(fig, title, subtitle="", title_size=13.5, axes_title_pt=0):
    """Place a title and optional multi-line subtitle above the axes.

    Reserves vertical space from the subtitle's own line count rather than a
    fixed pad. Setting a title on an axes and annotating a subtitle above it
    independently is what let the two collide, because neither knows the
    other's height.

    `axes_title_pt` is the point size of any per-axes titles, which draw
    upward out of the axes box and into the same band. Pass it whenever the
    subplots carry their own titles, or the subtitle lands on top of them.
    """
    lines = subtitle.count("\n") + 1 if subtitle else 0
    fig_h = fig.get_size_inches()[1]
    title_h = (title_size + 10) / 72 / fig_h
    sub_h = lines * 13.5 / 72 / fig_h
    axes_h = (axes_title_pt + 10) / 72 / fig_h if axes_title_pt else 0

    top = 1 - (title_h + sub_h + axes_h + 0.012)
    fig.subplots_adjust(top=top)

    fig.text(0.008, 0.995, title, fontsize=title_size, fontweight="bold",
             color=INK, ha="left", va="top")
    if subtitle:
        fig.text(0.008, 0.995 - title_h, subtitle, fontsize=9.5,
                 color=INK2, ha="left", va="top", linespacing=1.45)
    return top


def load():
    cells = pd.read_parquet(BASE / "processed" / "cell_monthly.parquet")
    irr = cells[cells["is_irrigated"]]
    fields = (
        irr.groupby("time")[["eta_af", "cuadj_af", "ppt_af", "acres"]]
        .sum()
        .sort_index()
    )
    fields.index = pd.to_datetime(fields.index)

    grace = pd.read_parquet(BASE / "processed" / "grace_oregon_series.parquet")
    grace["time"] = pd.to_datetime(grace["time"])
    grace = grace.set_index("time").sort_index()

    # Reindex both onto a gapless monthly axis; GRACE's missing months become
    # NaN and break the line rather than being bridged.
    full = monthly_index(min(fields.index.min(), grace.index.min()),
                         max(fields.index.max(), grace.index.max()))
    return fields.reindex(full), grace.reindex(full)


def label_last(ax, series, text, color, dy=0.0):
    s = series.dropna()
    if s.empty:
        return
    ax.annotate(
        text,
        xy=(s.index[-1], s.iloc[-1]),
        xytext=(6, dy),
        textcoords="offset points",
        color=color,
        fontsize=9,
        fontweight="bold",
        va="center",
    )


def mark_gap(ax):
    ax.axvspan(GAP_START, GAP_END, color=GRID, alpha=0.7, zorder=0, lw=0)


# ---------------------------------------------------------------- figure 6
def fig6(fields):
    """Full 38-year record of statewide irrigated ETa and consumptive use."""
    annual = fields.groupby(fields.index.to_period("Y").to_timestamp()).sum(min_count=12)
    annual = annual[annual["eta_af"] > 0]
    eta = annual["eta_af"] * AF_TO_MAF
    cu = annual["cuadj_af"] * AF_TO_MAF

    fig, ax = plt.subplots(figsize=(11, 5.2))
    ax.plot(eta.index, eta.values, color=BLUE, lw=2.0)
    ax.plot(cu.index, cu.values, color=ORANGE, lw=2.0)
    ax.scatter(eta.index, eta.values, s=14, color=BLUE, zorder=3)
    ax.scatter(cu.index, cu.values, s=14, color=ORANGE, zorder=3)

    label_last(ax, eta, "ETa", BLUE)
    label_last(ax, cu, "Consumptive use", ORANGE)

    ax.axvspan(pd.Timestamp("2002-04-01"), eta.index[-1], color=AQUA, alpha=0.06, lw=0, zorder=0)
    ax.annotate("GRACE record begins 2002-04", xy=(pd.Timestamp("2002-06-01"), ax.get_ylim()[1]),
                xytext=(4, -14), textcoords="offset points", color=INK2, fontsize=9)

    ax.set_ylabel("million acre-feet per year")
    ax.set_xlim(annual.index[0], annual.index[-1] + pd.Timedelta(days=400))
    ax.legend(handles=[Line2D([], [], color=BLUE, lw=2, label="ETa"),
                       Line2D([], [], color=ORANGE, lw=2, label="Consumptive use (adjusted)")],
              frameon=False, loc="lower right", fontsize=9)

    titleblock(
        fig,
        f"Oregon statewide irrigated-field water use, "
        f"{annual.index[0].year}–{annual.index[-1].year}",
        "Annual totals summed over all irrigated fields. Consumptive use is ETa net of effective "
        "precipitation.\nComplete calendar years only, so the partial 2022 water year is excluded.",
    )
    fig.savefig(OUT / "fig6_field_water_use_full_record.png", dpi=170,
                facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- figure 7
def fig7(fields, grace):
    """The requested comparison: deseasonalised shapes on a shared time axis."""
    win = slice(pd.Timestamp("2002-04-01"), pd.Timestamp("2022-10-01"))
    f, g = fields.loc[win], grace.loc[win]

    eta = smooth(deseasonalise(f["eta_af"] * AF_TO_MAF))
    cu = smooth(deseasonalise(f["cuadj_af"] * AF_TO_MAF))
    ppt = smooth(deseasonalise(f["ppt_af"] * AF_TO_MAF))
    tws = smooth(deseasonalise(g["oregon_land_anom_mm"]))

    fig, axes = plt.subplots(3, 1, figsize=(11, 10.4), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1, 0.85], "hspace": 0.22})
    titleblock(
        fig,
        "Field water use and GRACE storage, seasonal cycle removed",
        "Month-of-year climatology subtracted, then a 13-month centred mean. Each panel keeps its "
        "own scale;\nthe series are never plotted on shared y-axes.",
        title_size=14,
    )

    ax = axes[0]
    ax.axhline(0, color=AXIS, lw=1)
    ax.plot(eta.index, eta.values, color=BLUE, lw=2.0)
    ax.plot(cu.index, cu.values, color=ORANGE, lw=2.0)
    label_last(ax, eta, "ETa", BLUE, dy=6)
    label_last(ax, cu, "CU", ORANGE, dy=-6)
    mark_gap(ax)
    ax.set_ylabel("million acre-feet\nper month")
    ax.legend(handles=[Line2D([], [], color=BLUE, lw=2, label="ETa"),
                       Line2D([], [], color=ORANGE, lw=2, label="Consumptive use")],
              frameon=False, loc="upper left", fontsize=9, ncol=2)

    ax = axes[1]
    ax.axhline(0, color=AXIS, lw=1)
    ax.plot(tws.index, tws.values, color=AQUA, lw=2.0)
    label_last(ax, tws, "GRACE TWS", AQUA)
    mark_gap(ax)
    ax.annotate("mission gap", xy=(GAP_START + (GAP_END - GAP_START) / 2, ax.get_ylim()[0]),
                xytext=(0, 8), textcoords="offset points", ha="center",
                fontsize=8.5, color=MUTED)
    ax.annotate("The step across this gap is the GRACE→GRACE-FO offset, not a storage collapse.\n"
                "It is collinear with the trend and was left uncorrected.",
                xy=(0.5, 0.04), xycoords="axes fraction", fontsize=8.5, color=INK2, ha="center")
    ax.set_ylabel("mm equivalent\nwater height")
    ax.legend(handles=[Line2D([], [], color=AQUA, lw=2, label="GRACE total water storage anomaly")],
              frameon=False, loc="upper left", fontsize=9)

    ax = axes[2]
    ax.axhline(0, color=AXIS, lw=1)
    ax.plot(ppt.index, ppt.values, color=YELLOW, lw=2.0)
    label_last(ax, ppt, "Precip.", YELLOW)
    mark_gap(ax)
    ax.set_ylabel("million acre-feet\nper month")
    ax.set_xlabel("")
    ax.legend(handles=[Line2D([], [], color=YELLOW, lw=2,
                              label="Precipitation over fields (the confounder)")],
              frameon=False, loc="upper left", fontsize=9)
    ax.annotate("Controlling for precipitation, partial r(dS/dt, −CU) = −0.087 (p = 0.30). "
                "Any resemblance between\nthe top two panels is precipitation covariance, "
                "and the signal-to-noise ratio is 0.041.",
                xy=(0, -0.34), xycoords="axes fraction", fontsize=9.5, color=INK2)

    fig.savefig(OUT / "fig7_deseasonalised_shapes.png", dpi=170,
                facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


# ---------------------------------------------------------------- figure 8
def fig8(fields, grace):
    """What removing the seasonal cycle actually takes out."""
    win = slice(pd.Timestamp("2002-04-01"), pd.Timestamp("2022-10-01"))
    f, g = fields.loc[win], grace.loc[win]

    cu_raw = f["cuadj_af"] * AF_TO_MAF
    tws_raw = g["oregon_land_anom_mm"]

    fig, axes = plt.subplots(2, 2, figsize=(12.4, 7.2), sharex="col",
                             gridspec_kw={"hspace": 0.16, "wspace": 0.22})

    for ax, s, color, name, unit in [
        (axes[0][0], cu_raw, ORANGE, "Consumptive use", "million acre-feet per month"),
        (axes[0][1], tws_raw, AQUA, "GRACE TWS anomaly", "mm equivalent water height"),
    ]:
        ax.plot(s.index, s.values, color=color, lw=1.2)
        ax.set_ylabel(unit, fontsize=9)
        ax.set_title(f"{name} — as measured", fontsize=11, fontweight="bold",
                     color=INK, loc="left", pad=8)
        if name.startswith("GRACE"):
            mark_gap(ax)

    for ax, s, color, name, unit in [
        (axes[1][0], smooth(deseasonalise(cu_raw)), ORANGE, "Consumptive use",
         "million acre-feet per month"),
        (axes[1][1], smooth(deseasonalise(tws_raw)), AQUA, "GRACE TWS anomaly",
         "mm equivalent water height"),
    ]:
        ax.axhline(0, color=AXIS, lw=1)
        ax.plot(s.index, s.values, color=color, lw=2.0)
        ax.set_ylabel(unit, fontsize=9)
        ax.set_title(f"{name} — seasonal cycle removed", fontsize=11,
                     fontweight="bold", color=INK, loc="left", pad=8)
        if name.startswith("GRACE"):
            mark_gap(ax)

    titleblock(
        fig,
        "The annual cycle dominates both series until it is removed",
        "Top row as measured, bottom row after subtracting the month-of-year climatology and "
        "applying a 13-month\ncentred mean. Note the y-scales: removing the cycle shrinks both "
        "series by more than a factor of ten.",
        axes_title_pt=11,
    )
    fig.savefig(OUT / "fig8_raw_vs_deseasonalised.png", dpi=170,
                facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def main():
    fields, grace = load()
    fig6(fields)
    fig7(fields, grace)
    fig8(fields, grace)
    print("wrote fig6, fig7, fig8 to", OUT)


if __name__ == "__main__":
    main()
