"""The two global maps at a given HydroBASINS level.

    python 03_maps.py 03      # or 04

Same window, same estimator, same colour scale on both maps and across both
levels, so all four can be read against each other. Version 1 is GRACE total
water storage; version 2 subtracts GLDAS soil moisture, snow and canopy, which
is the part of a storage change the land surface accounts for without touching
an aquifer.

Colour is diverging: water lost and water gained are opposite states with a
meaningful zero between them, so it takes two hues and a neutral grey midpoint,
never a single ramp and never a rainbow. The scale is symmetric and clipped at a
round number, with the saturating basins counted on the figure rather than left
for the reader to notice.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np

sys.path.insert(0, r"E:\Water\_shared")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, TwoSlopeNorm  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from region_figure import AXIS, INK2, MUTED, SURFACE, titleblock  # noqa: E402

ROOT = Path(r"E:\Water\Global")
FIG = ROOT / "figures"
FIG.mkdir(parents=True, exist_ok=True)
ROBIN = "+proj=robin +lon_0=0 +datum=WGS84 +units=m +no_defs"
CLIP = 30.0
LEVEL = sys.argv[1] if len(sys.argv) > 1 else "03"

DIVERGING = LinearSegmentedColormap.from_list(
    "loss_gain", ["#8a3b12", "#c86a2c", "#e3a869", "#d9d7cf", "#7fb3d5", "#2a78d6", "#104281"])
norm = TwoSlopeNorm(vmin=-CLIP, vcenter=0.0, vmax=CLIP)

g = gpd.read_file(ROOT / "trends" / f"basins_lev{LEVEL}_trends.gpkg").to_crs(ROBIN)
summ = json.load(open(ROOT / "trends" / f"basins_lev{LEVEL}_summary.json"))
mas = json.load(open(ROOT / "trends" / "mascon_trends_summary.json"))
w0, w1 = mas["window"]
EDGE = 0.3 if LEVEL == "03" else 0.15

lines = [f"LINESTRING({','.join(f'{x} {lat}' for x in np.linspace(-180, 180, 181))})"
         for lat in range(-60, 90, 30)]
lines += [f"LINESTRING({','.join(f'{lon} {y}' for y in np.linspace(-90, 90, 181))})"
          for lon in range(-180, 181, 60)]
GRAT = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt(lines), crs="EPSG:4326").to_crs(ROBIN)


def draw(column, pcol, title, subtitle, outfile):
    fig, ax = plt.subplots(figsize=(13.5, 7.4))
    GRAT.plot(ax=ax, color=AXIS, linewidth=0.4, zorder=1)

    missing = g[g[column].isna()]
    if len(missing):
        missing.plot(ax=ax, color="#e8e7e2", edgecolor=SURFACE, linewidth=EDGE, zorder=2)
    have = g[g[column].notna()]
    have.plot(ax=ax, column=column, cmap=DIVERGING, norm=norm,
              edgecolor=SURFACE, linewidth=EDGE, zorder=3)

    # Secondary encoding rather than colour: a basin whose trend cannot be
    # separated from zero is hatched, so a saturated hue never reads as a
    # strong result on its own.
    ns = have[have[pcol] >= 0.05]
    if len(ns):
        ns.plot(ax=ax, facecolor="none", edgecolor="#5f5e5a", linewidth=0.0,
                hatch="////", zorder=4)

    ax.set_axis_off()
    ax.set_frame_on(False)

    cb = fig.colorbar(plt.cm.ScalarMappable(cmap=DIVERGING, norm=norm), ax=ax,
                      orientation="horizontal", fraction=0.036, pad=0.02,
                      aspect=44, extend="both")
    cb.set_label(f"storage trend, {w0} to {w1} (mm/yr equivalent water height)",
                 color=INK2, fontsize=9.5)
    cb.outline.set_edgecolor(AXIS)
    cb.ax.tick_params(color=MUTED, labelcolor=MUTED, labelsize=9)

    handles = [Patch(facecolor="white", edgecolor="#5f5e5a", hatch="////",
                     label="trend not separable from zero (p >= 0.05)")]
    if len(missing):
        handles.append(Patch(facecolor="#e8e7e2", edgecolor=SURFACE, label="no value"))
    leg = ax.legend(handles=handles, loc="lower left", fontsize=9, frameon=True,
                    facecolor=SURFACE, edgecolor=AXIS, bbox_to_anchor=(0.0, -0.02))
    leg.get_frame().set_linewidth(0.8)

    titleblock(fig, title, subtitle, title_size=15)
    fig.savefig(outfile, dpi=170, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    print("wrote", outfile)


n_sat_t = int((g["tws_trend_mm_yr"].abs() > CLIP).sum())
n_sat_g = int((g["gws_trend_mm_yr"].abs() > CLIP).sum())
mp = summ["mascons_per_basin"]
lvl = int(LEVEL)

draw("tws_trend_mm_yr", "tws_p",
     f"Where the Earth's water storage moved, {w0[:4]} to {w1[:4]}",
     f"GRACE-FO era total water storage trend on {summ['n_with_tws']} HydroSHEDS level-{lvl} basins, from GSFC RL06v2.0\n"
     f"mascons aggregated by area. Everything is in here: groundwater, soil moisture, snow, surface water and ice.\n"
     f"{summ['n_tws_significant']} basins have a trend separable from zero; the rest are hatched. {n_sat_t} run past the "
     f"+/-{CLIP:.0f} mm/yr scale and are\n"
     f"drawn at its end -- Greenland and the glaciated basins go far beyond it. "
     f"Median {mp['median']:.0f} mascons per basin.",
     FIG / f"fig1_global_tws_lev{LEVEL}.png")

draw("gws_trend_mm_yr", "gws_p",
     "The same map with the land surface subtracted",
     "GRACE-FO total water storage minus GLDAS soil moisture, snow water equivalent and canopy, averaged over\n"
     f"the NOAH, VIC and CLSM models, on HydroSHEDS level-{lvl} basins. What is left is closer to groundwater and\n"
     f"surface water than to weather. {summ['n_gws_significant']} of {summ['n_with_gws']} basins are separable from zero; {n_sat_g} run past the scale.\n"
     f"Grey basins are withheld: {summ['n_gws_dropped_ice']} are more than a fifth glacier or ice sheet, where subtracting modelled snow\n"
     f"from ice-sheet mass loss would not give groundwater, and {summ['n_gws_dropped_low_coverage']} had GLDAS over less than half their area.",
     FIG / f"fig2_global_gws_lev{LEVEL}.png")
