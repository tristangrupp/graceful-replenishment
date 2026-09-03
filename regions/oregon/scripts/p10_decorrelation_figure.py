"""How much of a mascon's signal belongs to its neighbours.

Three views of the same fact. Panel A is the correlation-versus-separation
curve on native mascons rather than interpolated pixels. Panel B overlays
the deseasonalised series of a reference mascon and its immediate
neighbours, which is the curve in panel A made visible. Panel C repeats
that against mascons at increasing distance, so the point at which the
curves stop tracking can be read directly.

Lines in panels B and C are coloured by distance from the reference, so the
ramp is sequential (one hue, light to dark) rather than categorical.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

sys.path.insert(0, str(Path(__file__).parent))
from p6_shape_figures import (AXIS, GRID, INK, INK2, MUTED, ORANGE, SURFACE,  # noqa: E402
                              smooth, titleblock)
from p9_native_mascon_analysis import haversine, load_region  # noqa: E402

BASE = Path(r"E:\Water\Oregan\analysis")
OUT = BASE / "trends"

# Sequential blue ramp, steps 250..650. Nearest-to-surface step kept at 250
# so the lightest line still clears the ordinal contrast floor.
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

REF_LAT, REF_LON = 45.0, -122.598   # best-covered mascon, Willamette Valley


def ramp_for(n):
    idx = np.linspace(0, len(RAMP) - 1, n).round().astype(int)
    return [RAMP[i] for i in idx]


def main():
    mascons, _, _ = load_region()
    ds = pd.read_parquet(BASE / "processed" / "native_mascon_tws_deseasonalised.parquet")
    ds.columns = ds.columns.astype(int)
    pairs = pd.read_parquet(BASE / "processed" / "native_mascon_pair_correlations.parquet")
    binned = pd.read_csv(BASE / "processed" / "native_mascon_decorrelation.csv")

    ref = int(((mascons["lat_center"] - REF_LAT).abs()
               + (mascons["lon_180"] - REF_LON).abs()).idxmin())
    dist = haversine(mascons.loc[ref, "lat_center"], mascons.loc[ref, "lon_180"],
                     mascons["lat_center"].to_numpy(), mascons["lon_180"].to_numpy())
    mascons = mascons.assign(dist_km=dist)

    usable = [c for c in ds.columns if ds[c].notna().sum() > 100]
    dsu = ds[usable]

    fig = plt.figure(figsize=(13.0, 11.4))
    gs = fig.add_gridspec(3, 1, height_ratios=[0.95, 1, 1], hspace=0.42)

    # ---------------- Panel A: correlation vs separation ------------------
    ax = fig.add_subplot(gs[0])
    ax.scatter(pairs["dist_km"], pairs["r"], s=9, color=MUTED, alpha=0.35,
               linewidths=0, zorder=1)
    ax.plot(binned["dist_mid"], binned["mean"], color=RAMP[5], lw=2.4, zorder=3)
    ax.scatter(binned["dist_mid"], binned["mean"], s=26, color=RAMP[5], zorder=4)
    ax.axhline(0.7, color=AXIS, ls=":", lw=1.2)
    ax.axhline(0.0, color=AXIS, lw=1)

    adj = pairs[pairs["dist_km"] < 130]["r"]
    ax.axvspan(0, 130, color=RAMP[0], alpha=0.22, lw=0, zorder=0)
    ax.set_xlim(-20, pairs["dist_km"].max() + 30)
    ax.set_ylim(-1.05, 1.28)
    ax.annotate(f"adjacent mascons (<130 km): mean r = {adj.mean():.2f}, n = {len(adj)}",
                xy=(0.30, 0.955), xycoords="axes fraction", fontsize=9,
                color=INK2, va="top")
    ax.annotate("r = 0.7", xy=(1.0, 0.7), xycoords=("axes fraction", "data"),
                xytext=(-4, 5), textcoords="offset points", ha="right",
                fontsize=8.5, color=MUTED)
    ax.set_xlabel("separation between mascon centres (km)")
    ax.set_ylabel("correlation of\ndeseasonalised TWS")
    ax.set_title("A · Every pair of land mascons in the region", fontsize=11.5,
                 fontweight="bold", color=INK, loc="left", pad=8)
    ax.legend(handles=[Line2D([], [], color=MUTED, marker="o", ls="", ms=5,
                              alpha=0.5, label="individual mascon pairs"),
                       Line2D([], [], color=RAMP[5], lw=2.4, label="mean per 50 km bin")],
              frameon=False, loc="lower left", fontsize=9, ncol=2)

    # ---------------- Panel B: neighbours overlaid ------------------------
    ax = fig.add_subplot(gs[1])
    near = (mascons[(mascons["dist_km"] < 175) & mascons.index.isin(usable)]
            .sort_values("dist_km"))
    colors = ramp_for(len(near))
    for color, (k, r) in zip(colors, near.iterrows()):
        ax.plot(dsu.index, smooth(dsu[k], 7), color=color, lw=1.8,
                label=f"{r['dist_km']:.0f} km")
    ax.axhline(0, color=AXIS, lw=1)

    # r against the reference specifically. Taking every pair among the seven
    # would mix in mascons up to 350 km from each other, which is not what
    # this panel is showing.
    with_ref = pairs[((pairs["a"] == ref) & pairs["b"].isin(near.index))
                     | ((pairs["b"] == ref) & pairs["a"].isin(near.index))]["r"]
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.42 * (hi - lo))
    ax.set_ylabel("mm equivalent\nwater height")
    ax.set_title(f"B · The reference mascon and its {len(near) - 1} nearest neighbours, "
                 f"seasonal cycle removed", fontsize=11.5, fontweight="bold",
                 color=INK, loc="left", pad=8)
    ax.annotate(f"All {len(near)} land mascons within 175 km of {REF_LAT:.0f}°N "
                f"{abs(REF_LON):.1f}°W.  Against the reference, r runs "
                f"{with_ref.min():.2f} to {with_ref.max():.2f}.",
                xy=(0.012, 0.955), xycoords="axes fraction", fontsize=9,
                color=INK2, va="top")
    ax.legend(frameon=False, ncol=min(len(near), 7), fontsize=8.5, loc="upper left",
              bbox_to_anchor=(0.0, 0.90), columnspacing=1.1, handlelength=1.4)

    # ---------------- Panel C: increasing separation ----------------------
    ax = fig.add_subplot(gs[2])
    targets = []
    for want in [0, 150, 300, 500, 700, 900]:
        cand = mascons[mascons.index.isin(usable)]
        k = int((cand["dist_km"] - want).abs().idxmin())
        if k not in [t[0] for t in targets]:
            targets.append((k, mascons.loc[k, "dist_km"]))
    colors = ramp_for(len(targets))
    for color, (k, d) in zip(colors, targets):
        r = pairs[((pairs["a"] == ref) & (pairs["b"] == k))
                  | ((pairs["b"] == ref) & (pairs["a"] == k))]["r"]
        rt = f", r = {r.iloc[0]:.2f}" if len(r) else " (reference)"
        ax.plot(dsu.index, smooth(dsu[k], 7), color=color, lw=1.8,
                label=f"{d:,.0f} km{rt}")
    ax.axhline(0, color=AXIS, lw=1)
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo - 0.32 * (hi - lo), hi + 0.34 * (hi - lo))
    ax.set_ylabel("mm equivalent\nwater height")
    ax.set_title("C · The same reference against land mascons at increasing distance",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)
    ax.legend(frameon=False, fontsize=8.5, loc="upper left", ncol=3,
              bbox_to_anchor=(0.0, 1.0), columnspacing=1.4, handlelength=1.6)
    ax.annotate("This reference decorrelates faster than panel A's average, because it sits west "
                "of the Cascade crest.\nEverything past 292 km is interior high desert, which is "
                "snow-driven where the Willamette is rain-driven.\nSeparation is not the only "
                "thing that decides whether two mascons share a signal.",
                xy=(0.012, 0.035), xycoords="axes fraction", fontsize=9, color=INK2)

    summary = json.loads((BASE / "processed" / "native_mascon_flux_summary.json").read_text())
    titleblock(
        fig,
        "A mascon carries little information its neighbours do not already have",
        "Native GSFC land mascons over the Oregon region, month-of-year climatology removed, "
        "7-month smoothing in panels B\nand C for legibility. Lines are coloured by distance from "
        f"the reference, light to dark. The {summary['n_mascons']} land mascons here carry "
        f"{summary['effective_dof']:.2f}\neffective degrees of freedom, so the region behaves as "
        f"roughly two numbers rather than {summary['n_mascons']}.",
        axes_title_pt=11.5,
    )
    fig.savefig(OUT / "fig10_native_mascon_decorrelation.png", dpi=170,
                facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("wrote fig10")


if __name__ == "__main__":
    main()
