"""Red experiment figures: the map, the area dependence, and the ranking check.

The map has three states and the fourth is deliberately missing. Red marks a
specific reason not to treat the basin as independently resolved. Grey marks a
basin the tests could not reach. Everything else is left uncoloured and labelled
"not flagged", never "validated". The tests detect named failure modes, so a
basin surviving them is the absence of a finding, not a finding of skill.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
import red_grid as rg  # noqa: E402
from region_figure import AXIS, INK2, MUTED, SURFACE, titleblock  # noqa: E402

RED = rg.RED
FIG = rg.ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
ROBIN = "+proj=robin +lon_0=0 +datum=WGS84 +units=m +no_defs"

RED_FILL = "#b5341c"
GREY_FILL = "#c9c9c2"
PLAIN_FILL = "#f0efe9"

flags = pd.read_parquet(RED / "level6_red_flags.parquet")
summ = json.load(open(RED / "level6_red_summary.json"))
basins = rg.load_basins("06")
g = basins.merge(flags.drop(columns=[c for c in flags.columns if c in basins.columns
                                     and c != "HYBAS_ID"]), on="HYBAS_ID", how="left")
g = gpd.GeoDataFrame(g, geometry="geometry", crs="EPSG:4326")
# The same table as the parquet, with the polygons attached, for GIS.
gpkg = RED / "level6_red_flags.gpkg"
g.to_file(gpkg, driver="GPKG")
print("wrote", gpkg)
g = g.to_crs(ROBIN)

lines = [f"LINESTRING({','.join(f'{x} {lat}' for x in np.linspace(-180, 180, 181))})"
         for lat in range(-60, 90, 30)]
lines += [f"LINESTRING({','.join(f'{lon} {y}' for y in np.linspace(-90, 90, 181))})"
          for lon in range(-180, 181, 60)]
GRAT = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt(lines), crs="EPSG:4326").to_crs(ROBIN)

cp = summ["common_period"]
tested = g["usable"].fillna(False).to_numpy().astype(bool)
red = g["RED_ANY"].fillna(False).to_numpy().astype(bool) & tested


def map_figure(mask, title, subtitle, outfile, note):
    fig, ax = plt.subplots(figsize=(13.5, 7.4))
    GRAT.plot(ax=ax, color=AXIS, linewidth=0.4, zorder=1)
    g[~tested].plot(ax=ax, color=GREY_FILL, linewidth=0, zorder=2)
    g[tested & ~mask].plot(ax=ax, color=PLAIN_FILL, edgecolor=AXIS, linewidth=0.05, zorder=3)
    g[tested & mask].plot(ax=ax, color=RED_FILL, linewidth=0, zorder=4)
    ax.set_axis_off()
    ax.set_aspect("equal")
    handles = [Patch(facecolor=RED_FILL, label="flagged: a specific reason not to treat it as resolved"),
               Patch(facecolor=PLAIN_FILL, edgecolor=AXIS, label="not flagged"),
               Patch(facecolor=GREY_FILL, label="not tested")]
    ax.legend(handles=handles, loc="lower left", frameon=False, fontsize=8.5,
              labelcolor=INK2, bbox_to_anchor=(0.02, 0.02))
    titleblock(fig, title, subtitle)
    fig.text(0.02, 0.02, note, fontsize=7.5, color=MUTED, va="bottom")
    fig.savefig(FIG / outfile, dpi=190, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("wrote", outfile)


n_red, n_tested = int(red.sum()), int(tested.sum())
share = summ["flags"]["RED_ANY"]["area_share_of_tested"]
map_figure(
    red,
    "Where downscaled GRACE is not independently resolved at HydroBASINS level 6",
    f"{n_red:,} of {n_tested:,} tested basins fail at least one test, "
    f"{share*100:.0f} percent of the tested land area. Common window {cp[0]} to {cp[1]}.",
    "fig_red_level6.png",
    "A basin that is not red has not been shown to be trustworthy. It has only survived tests\n"
    "designed to catch obvious failure. Showing that a value is right needs wells, evapotranspiration\n"
    "or InSAR, and that is a different experiment.")

for flag, label in [("RED_GEOMETRY", "the basin is not nominally resolved"),
                    ("RED_NO_INDEPENDENT_DEPARTURE", "the product reproduces coarse GRACE at basin scale"),
                    ("RED_PREDICTOR_DERIVED", "predictor fields explain the departure"),
                    ("RED_DISAGREEMENT", "the basin-scale result is method dependent"),
                    ("RED_RANK_UNSTABLE", "the ranking is not stable between products")]:
    if flag not in g.columns:
        continue
    m = g[flag].fillna(False).to_numpy().astype(bool) & tested
    if not m.any():
        continue
    c = summ["flags"][flag]
    map_figure(m, f"Level 6 basins where {label}",
               f"{c['n']:,} basins, {c['area_share_of_tested']*100:.0f} percent of tested land area. "
               f"Flag {flag}.",
               f"fig_red_{flag.lower()}.png",
               "One test only. Passing this test says nothing about the others.")

# ------------------------------------------------------------ area dependence
area = g["SUB_AREA"].to_numpy()
fig, ax = plt.subplots(figsize=(8.2, 4.6))
bins = np.logspace(np.log10(max(area[tested].min(), 1)), np.log10(area[tested].max()), 40)
ax.hist(area[tested & ~red], bins=bins, color=PLAIN_FILL, edgecolor=AXIS, linewidth=0.5,
        label="not flagged")
ax.hist(area[red], bins=bins, color=RED_FILL, alpha=0.85, label="flagged red")
ax.axvline(63000, color=INK2, linestyle="--", linewidth=1)
ax.text(63000 * 1.06, ax.get_ylim()[1] * 0.92, "63,000 km$^2$\nreliable unit", fontsize=7.5,
        color=INK2, va="top")
ax.set_xscale("log")
ax.set_xlabel("basin area, km$^2$", fontsize=9, color=INK2)
ax.set_ylabel("basins", fontsize=9, color=INK2)
ax.legend(frameon=False, fontsize=8.5, labelcolor=INK2)
ax.tick_params(labelsize=8, colors=MUTED)
for s in ax.spines.values():
    s.set_color(AXIS)
titleblock(fig, "Red flags follow basin size",
           "Level 6 basins by area. The reliable-unit threshold is from Vishwakarma, Devaraju "
           "and Sneeuw (2018).")
fig.savefig(FIG / "fig_red_area.png", dpi=190, facecolor=SURFACE, bbox_inches="tight")
plt.close(fig)
print("wrote fig_red_area.png")

# -------------------------------------------------------------- ranking check
sp = summ.get("spearman", {})
pairs = [("rank_coarse", "rank_G", "GRACE-SeDA", sp.get("G_vs_coarse")),
         ("rank_coarse", "rank_L", "Li and Kusche", sp.get("L_vs_coarse"))]
pairs = [p for p in pairs if p[3] is not None and g[p[1]].notna().any()]
if pairs:
    fig, axes = plt.subplots(1, len(pairs), figsize=(5.4 * len(pairs), 5.0), squeeze=False)
    for ax, (xc, yc, name, rho) in zip(axes[0], pairs):
        ax.plot([0, 100], [0, 100], color=AXIS, linewidth=0.8, zorder=1)
        ax.scatter(g[xc], g[yc], s=1.4, color=RED_FILL, alpha=0.25, linewidths=0, zorder=2)
        ax.set_xlabel("percentile rank, coarse GRACE", fontsize=9, color=INK2)
        ax.set_ylabel(f"percentile rank, {name}", fontsize=9, color=INK2)
        ax.set_title(f"Spearman {rho:.3f}", fontsize=9, color=INK2)
        ax.tick_params(labelsize=8, colors=MUTED)
        for s in ax.spines.values():
            s.set_color(AXIS)
    titleblock(fig, "Downscaling changed the resolution without reordering the priority list",
               "Level 6 basins ranked by depletion trend. Rank 0 is the most depleting basin.")
    fig.savefig(FIG / "fig_red_ranks.png", dpi=190, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("wrote fig_red_ranks.png")
