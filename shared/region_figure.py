"""The three-panel decorrelation figure, for any region."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

from grace_region import haversine

SURFACE, INK, INK2, MUTED = "#fcfcfb", "#0b0b0b", "#52514e", "#898781"
GRID, AXIS = "#e1e0d9", "#c3c2b7"
RAMP = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf",
        "#1c5cab", "#184f95", "#104281"]

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
})


def titleblock(fig, title, subtitle="", title_size=13.5, axes_title_pt=0):
    lines = subtitle.count("\n") + 1 if subtitle else 0
    fig_h = fig.get_size_inches()[1]
    title_h = (title_size + 10) / 72 / fig_h
    sub_h = lines * 13.5 / 72 / fig_h
    axes_h = (axes_title_pt + 10) / 72 / fig_h if axes_title_pt else 0
    fig.subplots_adjust(top=1 - (title_h + sub_h + axes_h + 0.012))
    fig.text(0.008, 0.995, title, fontsize=title_size, fontweight="bold",
             color=INK, ha="left", va="top")
    if subtitle:
        fig.text(0.008, 0.995 - title_h, subtitle, fontsize=9.5, color=INK2,
                 ha="left", va="top", linespacing=1.45)


def smooth(s, window=7):
    return s.rolling(window, center=True, min_periods=window // 2 + 1).mean()


def ramp_for(n):
    return [RAMP[i] for i in np.linspace(0, len(RAMP) - 1, n).round().astype(int)]


def make_figure(name, out_dir, summary, mascons, ds, pairs, binned, note=""):
    out_dir = Path(out_dir)
    (out_dir / "trends").mkdir(parents=True, exist_ok=True)

    usable = [c for c in ds.columns if ds[c].notna().sum() > 100]
    dsu = ds[usable]

    # Reference = the land mascon closest to the region's own centroid, so the
    # panels below show a typical mascon rather than an edge case.
    clat = mascons.loc[usable, "lat_center"].mean()
    clon = mascons.loc[usable, "lon_180"].mean()
    ref = int(((mascons.loc[usable, "lat_center"] - clat).abs()
               + (mascons.loc[usable, "lon_180"] - clon).abs()).idxmin())
    dist = haversine(mascons.loc[ref, "lat_center"], mascons.loc[ref, "lon_180"],
                     mascons["lat_center"].to_numpy(), mascons["lon_180"].to_numpy())
    mascons = mascons.assign(dist_km=dist)

    fig = plt.figure(figsize=(13.0, 11.4))
    gs = fig.add_gridspec(3, 1, height_ratios=[0.95, 1, 1], hspace=0.42)

    # ---- A: correlation vs separation ---------------------------------
    ax = fig.add_subplot(gs[0])
    ax.scatter(pairs["dist_km"], pairs["r"], s=9, color=MUTED, alpha=0.35,
               linewidths=0, zorder=1)
    ax.plot(binned["dist_mid"], binned["mean"], color=RAMP[5], lw=2.4, zorder=3)
    ax.scatter(binned["dist_mid"], binned["mean"], s=26, color=RAMP[5], zorder=4)
    ax.axhline(0.7, color=AXIS, ls=":", lw=1.2)
    ax.axhline(0.0, color=AXIS, lw=1)
    ax.axvspan(0, summary["adjacent_km"], color=RAMP[0], alpha=0.22, lw=0, zorder=0)
    ax.set_xlim(-20, pairs["dist_km"].max() + 30)
    ax.set_ylim(-1.05, 1.28)
    ax.annotate(f"adjacent mascons (<{summary['adjacent_km']} km): "
                f"mean r = {summary['adjacent_r_mean']:.2f}, n = {summary['n_adjacent_pairs']}",
                xy=(0.30, 0.955), xycoords="axes fraction", fontsize=9, color=INK2, va="top")
    ax.annotate("r = 0.7", xy=(0.0, 0.7), xycoords=("axes fraction", "data"),
                xytext=(4, -13), textcoords="offset points", ha="left",
                fontsize=8.5, color=MUTED)
    ax.set_xlabel("separation between mascon centres (km)")
    ax.set_ylabel("correlation of\ndeseasonalised TWS")
    ax.set_title("A · Every pair of land mascons in the region", fontsize=11.5,
                 fontweight="bold", color=INK, loc="left", pad=8)
    ax.legend(handles=[Line2D([], [], color=MUTED, marker="o", ls="", ms=5,
                              alpha=0.5, label="individual mascon pairs"),
                       Line2D([], [], color=RAMP[5], lw=2.4, label="mean per 50 km bin")],
              frameon=False, loc="lower left", fontsize=9, ncol=2)

    # ---- B: nearest neighbours overlaid --------------------------------
    ax = fig.add_subplot(gs[1])
    near = (mascons[(mascons["dist_km"] < 175) & mascons.index.isin(usable)]
            .sort_values("dist_km"))
    for color, (k, r) in zip(ramp_for(len(near)), near.iterrows()):
        ax.plot(dsu.index, smooth(dsu[k]), color=color, lw=1.8, label=f"{r['dist_km']:.0f} km")
    ax.axhline(0, color=AXIS, lw=1)
    with_ref = pairs[((pairs["a"] == ref) & pairs["b"].isin(near.index))
                     | ((pairs["b"] == ref) & pairs["a"].isin(near.index))]["r"]
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.42 * (hi - lo))
    ax.set_ylabel("mm equivalent\nwater height")
    ax.set_title(f"B · The reference mascon and its {len(near) - 1} nearest neighbours, "
                 f"seasonal cycle removed",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)
    rng = (f"Against the reference, r runs {with_ref.min():.2f} to {with_ref.max():.2f}."
           if len(with_ref) else "")
    ax.annotate(f"All {len(near)} land mascons within 175 km of "
                f"{mascons.loc[ref, 'lat_center']:.0f}°N "
                f"{abs(mascons.loc[ref, 'lon_180']):.1f}°W.  {rng}",
                xy=(0.012, 0.955), xycoords="axes fraction", fontsize=9, color=INK2, va="top")
    ax.legend(frameon=False, ncol=min(len(near), 7), fontsize=8.5, loc="upper left",
              bbox_to_anchor=(0.0, 0.90), columnspacing=1.1, handlelength=1.4)

    # ---- C: increasing separation --------------------------------------
    ax = fig.add_subplot(gs[2])
    cand = mascons[mascons.index.isin(usable)]
    targets = []
    for want in [0, 150, 300, 500, 700, 900]:
        if want > cand["dist_km"].max():
            continue
        k = int((cand["dist_km"] - want).abs().idxmin())
        if k not in [t[0] for t in targets]:
            targets.append((k, mascons.loc[k, "dist_km"]))
    for color, (k, d) in zip(ramp_for(len(targets)), targets):
        r = pairs[((pairs["a"] == ref) & (pairs["b"] == k))
                  | ((pairs["b"] == ref) & (pairs["a"] == k))]["r"]
        rt = f", r = {r.iloc[0]:.2f}" if len(r) else " (reference)"
        ax.plot(dsu.index, smooth(dsu[k]), color=color, lw=1.8, label=f"{d:,.0f} km{rt}")
    ax.axhline(0, color=AXIS, lw=1)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo - (0.30 * (hi - lo) if note else 0), hi + 0.34 * (hi - lo))
    ax.set_ylabel("mm equivalent\nwater height")
    ax.set_title("C · The same reference against land mascons at increasing distance",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3,
              bbox_to_anchor=(0.0, 1.0), columnspacing=1.4, handlelength=1.6)
    if note:
        ax.annotate(note, xy=(0.012, 0.035), xycoords="axes fraction",
                    fontsize=9, color=INK2)

    r07 = summary["r07_km"]
    r07s = (f"the binned mean falls through 0.7 at {r07:,.0f} km"
            if np.isfinite(r07)
            else "the binned mean never falls through 0.7 anywhere in the region")
    titleblock(
        fig,
        f"{name}: {summary['n_usable']} land mascons, "
        f"{summary['effective_dof']:.2f} effective degrees of freedom",
        f"Native GSFC mascons, month-of-year climatology removed, 7-month smoothing in panels B "
        f"and C for legibility.\nAdjacent mascons correlate at r = {summary['adjacent_r_mean']:.2f} "
        f"on average, and {r07s}.\nThe region carries about one independent measurement per "
        f"{summary['mascons_per_effective_dof']:.0f} mascons.",
        axes_title_pt=11.5,
    )
    path = out_dir / "trends" / "decorrelation.png"
    fig.savefig(path, dpi=170, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return path
