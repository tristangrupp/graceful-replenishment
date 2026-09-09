"""Green experiment figures: where the wells are, and what they say.

Three figures, in the order the argument runs. Where the open well data is, and
therefore what the green half can and cannot speak for. Whether a downscaled
product tracks a well better than the coarse solution behind it. Whether GRACE
adds anything at a well that precipitation and soil moisture do not.
"""

import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import red_grid as rg  # noqa: E402
from region_figure import AXIS, INK, INK2, MUTED, SURFACE, titleblock  # noqa: E402

GREEN = rg.ROOT / "green"
FIG = rg.ROOT / "figures"
ROBIN = "+proj=robin +lon_0=0 +datum=WGS84 +units=m +no_defs"
WARM, COOL, NEUTRAL = "#b5341c", "#2a78d6", "#c9c9c2"

s = json.load(open(GREEN / "green_summary.json"))
t = pd.read_parquet(GREEN / "well_scores.parquet")
blk = pd.read_parquet(GREEN / "mascon_oos_r2.parquet")

land = rg.load_basins("03").to_crs(ROBIN)
pts = gpd.GeoDataFrame(t.reset_index(),
                       geometry=gpd.points_from_xy(t.lon, t.lat),
                       crs="EPSG:4326").to_crs(ROBIN)

lines = [f"LINESTRING({','.join(f'{x} {lat}' for x in np.linspace(-180, 180, 181))})"
         for lat in range(-60, 90, 30)]
lines += [f"LINESTRING({','.join(f'{lon} {y}' for y in np.linspace(-90, 90, 181))})"
          for lon in range(-180, 181, 60)]
GRAT = gpd.GeoDataFrame(geometry=gpd.GeoSeries.from_wkt(lines), crs="EPSG:4326").to_crs(ROBIN)

# ------------------------------------------------------- 1. where the wells are
fig, ax = plt.subplots(figsize=(13.5, 7.0))
GRAT.plot(ax=ax, color=AXIS, linewidth=0.4, zorder=1)
land.plot(ax=ax, color="#f0efe9", edgecolor=AXIS, linewidth=0.2, zorder=2)
ok = pts["r_jpl"].notna()
pts[~ok].plot(ax=ax, color=NEUTRAL, markersize=0.5, zorder=3)
pts[ok].plot(ax=ax, color=WARM, markersize=0.6, alpha=0.5, zorder=4)
ax.set_axis_off()
ax.set_aspect("equal")
n_ok = int(ok.sum())
src = json.load(open(GREEN / "wells_sources.json"))
by_src = ", ".join(f"{k} {v:,}" for k, v in src["wells_by_source"].items())
titleblock(fig, "Where the open well records are",
           f"{len(t):,} wells with at least 10 annual values between 2002 and 2022, "
           f"{n_ok:,} of them scored against GRACE. By source: {by_src}.\n"
           "Jasechko et al. (2024), the subset posted with permission, plus CONAGUA's "
           "national piezometric network for Mexico.\nAsia is still almost absent, so "
           "nothing here speaks for North India, the North China Plain, Iran or the "
           "Arabian Peninsula,\nwhich is where the red half found the most.")
fig.savefig(FIG / "fig_green_wells.png", dpi=190, facecolor=SURFACE, bbox_inches="tight")
plt.close(fig)
print("wrote fig_green_wells.png")

# ------------------------------------------- 2. does downscaling help at a well?
fig, axes = plt.subplots(1, 2, figsize=(11.0, 4.4))
for ax, key, name, parent in ((axes[0], "dr_seda", "GRACE-SeDA", "RL06.1"),
                              (axes[1], "dr_liku", "Li and Kusche", "RL06.3")):
    d = t[key].dropna()
    ax.hist(d, bins=np.linspace(-0.6, 0.6, 61), color=NEUTRAL, edgecolor=AXIS,
            linewidth=0.4)
    ax.axvline(0, color=INK, linewidth=1)
    ax.axvline(d.median(), color=WARM, linewidth=1.4)
    sg = s["paired_against_parent"][key.split("_")[1]]
    ax.set_title(f"{name} against coarse {parent}\nmedian {d.median():+.3f}, "
                 f"{sg['mascons_improved']}/{sg['n_mascons']} mascons better, "
                 f"sign test p {sg['p_value_by_mascon']:.2f}",
                 fontsize=9, color=INK2)
    ax.set_xlabel("change in correlation with the well", fontsize=9, color=INK2)
    ax.tick_params(labelsize=8, colors=MUTED)
    for sp in ax.spines.values():
        sp.set_color(AXIS)
axes[0].set_ylabel("wells", fontsize=9, color=INK2)
titleblock(fig, "Downscaling did not improve agreement with the wells",
           "Per well, the correlation of annual anomalies with the downscaled product minus "
           "the same correlation\nwith the coarse solution it was built from. The test counts "
           "mascons, not wells: wells inside one mascon\nshare a single gravimetric "
           "observation.")
fig.savefig(FIG / "fig_green_paired.png", dpi=190, facecolor=SURFACE, bbox_inches="tight")
plt.close(fig)
print("wrote fig_green_paired.png")

# -------------------------------------------------------------- 3. the ablation
lab = {"A_predictors_only": "A  weather only",
       "B_plus_coarse_RL0603": "B  A + coarse GRACE",
       "C_plus_seda": "C  A + GRACE-SeDA",
       "C_plus_liku": "C  A + Li and Kusche"}
fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.4),
                         gridspec_kw={"width_ratios": [1, 1.15]})
ax = axes[0]
keys = list(lab)
vals = [s["ablation"][k]["oos_r2"] for k in keys]
ax.barh(range(len(keys)), vals, color=[NEUTRAL, COOL, WARM, WARM], edgecolor=AXIS,
        linewidth=0.5)
ax.set_yticks(range(len(keys)))
ax.set_yticklabels([lab[k] for k in keys], fontsize=8.5, color=INK2)
ax.invert_yaxis()
for i, v in enumerate(vals):
    ax.text(v + 0.002, i, f"{v:.3f}", va="center", fontsize=8, color=INK2)
ax.set_xlabel("pooled out of sample R squared", fontsize=9, color=INK2)
ax.set_xlim(0, max(vals) * 1.25)
ax.tick_params(labelsize=8, colors=MUTED)
for sp in ax.spines.values():
    sp.set_color(AXIS)

ax = axes[1]
base = "B_plus_coarse_RL0603"
show = ["A_predictors_only", "C_plus_seda", "C_plus_liku"]
data = [(blk[k] - blk[base]).dropna().to_numpy() for k in show]
bp = ax.boxplot(data, vert=False, widths=0.6, showfliers=False, patch_artist=True)
for patch in bp["boxes"]:
    patch.set_facecolor(NEUTRAL)
    patch.set_edgecolor(AXIS)
for med in bp["medians"]:
    med.set_color(WARM)
    med.set_linewidth(1.6)
ax.axvline(0, color=INK, linewidth=1)
ax.set_yticklabels([lab[k].split("  ")[1] for k in show], fontsize=8.5, color=INK2)
ax.set_xlabel("R squared inside each held-out mascon, minus coarse GRACE",
              fontsize=9, color=INK2)
ax.tick_params(labelsize=8, colors=MUTED)
for sp in ax.spines.values():
    sp.set_color(AXIS)
titleblock(fig, "Gravimetry adds information at a well; the finer grid does not",
           "Leave one mascon out, never a random split: wells inside one mascon see the same "
           "measurement.\nLeft, skill pooled over 782,186 well-years. Right, the same "
           "comparison inside each of 133 mascons,\nwhich is the number of independent "
           "gravimetric observations the well network actually sees.")
fig.savefig(FIG / "fig_green_ablation.png", dpi=190, facecolor=SURFACE, bbox_inches="tight")
plt.close(fig)
print("wrote fig_green_ablation.png")
