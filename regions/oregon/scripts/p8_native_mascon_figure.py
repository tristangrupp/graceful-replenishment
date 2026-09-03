"""Coverage on the mascons the GSFC solution actually solves for."""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

import sys

sys.path.insert(0, str(Path(__file__).parent))
from p6_shape_figures import (AXIS, BLUE, GRID, INK, INK2, MUTED, ORANGE,  # noqa: E402
                              SURFACE, titleblock)

BASE = Path(r"E:\Water\Oregan\analysis")
OUT = BASE / "trends"

plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
})


def main():
    cov = pd.read_csv(BASE / "processed" / "native_mascon_coverage.csv")
    top = cov[cov["irr_km2"] > 0].nlargest(10, "irr_frac_pct").iloc[::-1]

    fig, axes = plt.subplots(1, 2, figsize=(13.2, 6.4),
                             gridspec_kw={"width_ratios": [1, 1.35], "wspace": 0.28})

    # -- left: the three scales, which are routinely conflated -------------
    ax = axes[0]
    scales = ["0.5° pixel\n2,157 km²\n(interpolated,\nnot a solve element)",
              "native mascon\n12,390 km²\n(what GSFC solves)",
              "300 km footprint\n66,860 km²\n(what GRACE resolves)"]
    vals = [24.6, cov["irr_frac_pct"].max(), 3.3]
    bars = ax.bar(range(3), vals, color=[MUTED, BLUE, MUTED], width=0.62)
    bars[1].set_zorder(3)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.6, f"{v:.1f}%", ha="center", fontsize=11,
                fontweight="bold", color=INK)
    ax.set_xticks(range(3))
    ax.set_xticklabels(scales, fontsize=8.5)
    ax.set_ylabel("best irrigated share of footprint (%)")
    ax.set_ylim(0, 29)
    ax.set_title("Three scales, three answers", fontsize=11.5,
                 fontweight="bold", color=INK, loc="left", pad=8)

    # -- right: coverage per native mascon ---------------------------------
    ax = axes[1]
    y = np.arange(len(top))
    ax.barh(y + 0.19, top["all_field_frac_pct"], height=0.36, color=ORANGE)
    ax.barh(y - 0.19, top["irr_frac_pct"], height=0.36, color=BLUE)

    labels = []
    for _, r in top.iterrows():
        star = " *" if r["crosses_border"] else ""
        labels.append(f"{r['lat_center']:.0f}°N {abs(r['lon_180']):.1f}°W{star}")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("share of the mascon (%)", labelpad=8)
    ax.set_xlim(0, 48)
    for i, (_, r) in enumerate(top.iterrows()):
        ax.text(r["all_field_frac_pct"] + 0.7, i + 0.19, f"{r['all_field_frac_pct']:.1f}",
                va="center", fontsize=8.5, color=INK2)
        ax.text(r["irr_frac_pct"] + 0.7, i - 0.19, f"{r['irr_frac_pct']:.1f}",
                va="center", fontsize=8.5, color=INK2)
    ax.legend(handles=[Patch(color=ORANGE, label="all field boundaries"),
                       Patch(color=BLUE, label="irrigated")],
              frameon=False, loc="lower right", fontsize=9)
    ax.set_title("Top native mascons over Oregon", fontsize=11.5,
                 fontweight="bold", color=INK, loc="left", pad=8)
    ax.annotate("*  mascon extends past the Oregon border, so the inventory cannot see all of its "
                "farmland",
                xy=(0, -0.155), xycoords="axes fraction", fontsize=8.5, color=INK2)

    titleblock(
        fig,
        "Oregon farmland fills 43% of a mascon; irrigated land reaches 15%",
        "Coverage measured on the native ~1° equal-area mascons the GSFC solution solves for, not "
        "the interpolated\nhalf-degree grid. A mascon averages 12,390 km², which is 43% larger than "
        "the 1° block used earlier.",
        axes_title_pt=11.5,
    )
    fig.savefig(OUT / "fig9_native_mascon_coverage.png", dpi=170,
                facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("wrote fig9 to", OUT)


if __name__ == "__main__":
    main()
