"""Phase 6 - figures.

Static PNGs for a markdown report, so they deliberately commit to the light
surface only. Palette taken from the validated reference instance and checked
with scripts/validate_palette.js: slots 1-3 (#2a78d6 blue, #eb6834 orange,
#1baf7a aqua) pass all-pairs CVD and normal-vision floors on the light surface;
aqua carries a contrast WARN, so it is used only for a line that also carries a
legend entry and a direct label (the relief rule). Red #e34948 is the reserved
status colour and is used only for threshold lines, never as a data series.
One y-axis per panel. Sequential magnitude uses a single blue ramp.
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
from matplotlib.patches import Rectangle

sys.path.insert(0, r"E:\Water\_shared")
from region_figure import titleblock, SURFACE, INK, INK2, MUTED, GRID, AXIS, RAMP

OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")
SIG = Path(r"E:\Water\CentralValley\signals")
FIG = Path(r"E:\Water\CentralValley\trends")
FIG.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA, RED = "#2a78d6", "#eb6834", "#1baf7a", "#e34948"
NE_LAND = Path(r"C:\Users\grupp\.local\share\cartopy\shapefiles\natural_earth"
               r"\physical\ne_10m_land.shp")

OREGON = {"snr_300km": 0.041, "snr_best": 0.150,
          "D_300km": 17.7, "D_best": 79.2,
          "irr_300km": 3.27, "irr_best": 14.5,
          "b_CU": 3.112, "se_CU": 3.550}


# ---------------------------------------------------------------- figure 1
def fig_coverage():
    cov = pd.read_csv(OUT / "mascon_coverage.csv")
    geo = pd.read_csv(OUT / "mascon_geometry.csv")
    g = geo.set_index("mascon_id")

    fig, ax = plt.subplots(figsize=(7.4, 8.2))
    try:
        import geopandas as gpd
        from shapely.geometry import box as sbox
        land = gpd.read_file(NE_LAND)
        land = land[land.geometry.intersects(sbox(-126, 32, -114, 43))]
        land.boundary.plot(ax=ax, color=AXIS, linewidth=0.7, zorder=1)
    except Exception as e:
        print("  (coastline skipped:", e, ")")

    vmax = float(cov["irr_frac_pct"].max())
    cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
        "irr", ["#f2f1ea"] + RAMP)
    norm = matplotlib.colors.Normalize(0, vmax)

    for _, r in cov.iterrows():
        gg = g.loc[r["mascon_id"]]
        ax.add_patch(Rectangle(
            (gg["lon_min"], gg["lat_min"]),
            gg["lon_max"] - gg["lon_min"], gg["lat_max"] - gg["lat_min"],
            facecolor=cmap(norm(r["irr_frac_pct"])), edgecolor=SURFACE,
            linewidth=1.6, zorder=2))
        if r["irr_frac_pct"] >= 10:
            ax.text(gg["lon_180"], gg["lat_center"],
                    f"{r['irr_frac_pct']:.0f}%",
                    ha="center", va="center", fontsize=9.5, zorder=4,
                    color="#ffffff" if r["irr_frac_pct"] > 30 else INK,
                    fontweight="bold")

    best = g.loc[1850]
    ax.add_patch(Rectangle((best["lon_min"], best["lat_min"]),
                           best["lon_max"] - best["lon_min"],
                           best["lat_max"] - best["lat_min"],
                           facecolor="none", edgecolor=RED, linewidth=2.4, zorder=5))
    ax.annotate("mascon 1850 — 52.1% irrigated,\n318 mm/yr consumptive use",
                xy=(best["lon_180"], best["lat_min"]),
                xytext=(-117.9, 34.2), fontsize=9.5, color=INK,
                ha="left", va="center",
                arrowprops=dict(arrowstyle="-", color=RED, linewidth=1.4))

    ax.set_xlim(-125.0, -116.6)
    ax.set_ylim(33.0, 43.2)
    ax.set_xlabel("longitude")
    ax.set_ylabel("latitude")
    ax.set_aspect(1 / np.cos(np.radians(37)))
    ax.grid(False)

    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = fig.colorbar(sm, ax=ax, fraction=0.033, pad=0.02)
    cb.set_label("irrigable land, % of mascon area", color=INK2)
    cb.outline.set_edgecolor(AXIS)

    titleblock(fig, "Central Valley irrigated coverage of native GSFC mascons",
               "Mean over the seven DWR i15 survey years that carry irrigation status (2016–2023).\n"
               "40 land mascons, ~12,390 km² each. Labels shown for mascons above 10%.\n"
               "Oregon's best mascon reached 14.5%; eight Central Valley mascons beat it.")
    fig.savefig(FIG / "fig1_coverage.png", dpi=170, bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- figure 2
def fig_threshold():
    th = json.loads((INV / "detection_threshold.json").read_text())
    fp = pd.read_csv(OUT / "threshold_footprints.csv")
    per = pd.read_csv(OUT / "threshold_per_mascon.csv")
    snr_need = th["threshold"]["required_snr_2sigma"]
    D_need = th["threshold"]["required_cu_depth_over_footprint_mm_yr"]
    gamma = th["gamma_sigma_cu_over_mean_cu"]["used_for_threshold"]
    noise = th["dsdt_noise_mm_per_month"]["central_valley_single_mascon_median"]

    fig, axes = plt.subplots(1, 2, figsize=(12.6, 5.5))

    # ---- panel A: SNR vs consumptive-use depth over the footprint
    ax = axes[0]
    sub = per[per["cu_mm_yr"] > 2]
    ax.scatter(sub["cu_mm_yr"], sub["snr_vs_noisefloor"], s=42, color=BLUE,
               alpha=0.45, edgecolor=SURFACE, linewidth=0.8, zorder=3,
               label="Central Valley, single mascons (40)")
    ax.scatter(fp["cu_mm_yr"], fp["snr_vs_noisefloor"], s=125, color=BLUE,
               marker="s", edgecolor=SURFACE, linewidth=1.4, zorder=4,
               label="Central Valley, aggregated footprints")
    ax.scatter([OREGON["D_300km"], OREGON["D_best"]],
               [OREGON["snr_300km"], OREGON["snr_best"]], s=125, color=ORANGE,
               marker="D", edgecolor=SURFACE, linewidth=1.4, zorder=4,
               label="Oregon (independent basin)")

    xs = np.logspace(0.6, 2.75, 60)
    ax.plot(xs, gamma * xs / 12.0 / noise, color=MUTED, linewidth=1.6,
            linestyle="-", zorder=2, label=f"σ(CU′) = {gamma:.2f}·CU/12 ÷ {noise:.0f} mm")
    ax.axhline(snr_need, color=RED, linewidth=1.8, linestyle="--", zorder=5)
    ax.text(4.0, snr_need * 1.16, f"2σ detection threshold, SNR = {snr_need:.2f}",
            color=RED, fontsize=9.5, va="bottom")
    ax.axvline(D_need, color=RED, linewidth=1.0, linestyle=":", zorder=5)

    offs = {"best native mascon (1850, Tulare)": ("mascon 1850", (10, -4), "left"),
            "300 km footprint around 1850": ("300 km", (-10, 9), "right"),
            "irrigated core (8 mascons >=10% irr)": ("core (8)", (10, 2), "left"),
            "all 40 land mascons": ("all 40", (10, -4), "left")}
    for _, r in fp.iterrows():
        lab, off, ha = offs[r["footprint"]]
        ax.annotate(lab, (r["cu_mm_yr"], r["snr_vs_noisefloor"]),
                    textcoords="offset points", xytext=off,
                    fontsize=9, color=INK, ha=ha)
    ax.annotate("OR best mascon\n(14.5% irrigated)", (OREGON["D_best"], OREGON["snr_best"]),
                textcoords="offset points", xytext=(10, -24), fontsize=9, color=ORANGE)
    ax.annotate("OR 300 km", (OREGON["D_300km"], OREGON["snr_300km"]),
                textcoords="offset points", xytext=(10, -13), fontsize=9, color=ORANGE)

    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlim(3.5, 620); ax.set_ylim(0.02, 1.4)
    ax.set_xlabel("consumptive-use depth over the footprint  D = f$_{irr}$ × CU$_{irr}$   (mm/yr)")
    ax.set_ylabel("SNR  =  σ(CU′) / σ(dS/dt noise)")
    ax.set_title("A. signal-to-noise scales with consumptive-use depth",
                 fontsize=10.5, color=INK, loc="left", pad=8)
    ax.legend(frameon=False, fontsize=9, loc="lower right")

    # ---- panel B: the usable nomogram
    ax = axes[1]
    cu_irr = np.linspace(250, 1250, 200)
    ax.plot(cu_irr, 100 * D_need / cu_irr, color=RED, linewidth=2.2, zorder=4)
    ax.fill_between(cu_irr, 100 * D_need / cu_irr, 100, color=BLUE, alpha=0.10, zorder=1)
    ax.fill_between(cu_irr, 0, 100 * D_need / cu_irr, color="#f2f1ea", zorder=1)
    ax.text(1180, 46, "DETECTABLE", color=BLUE, fontsize=11, fontweight="bold",
            ha="right", va="center")
    ax.text(1180, 6.5, "not detectable at 2σ", color=MUTED, fontsize=10,
            ha="right", va="center")

    pts = [(1045, 52.1, "CV mascon 1850", BLUE, (-10, 4)),
           (569, 19.5, "CV 300 km", BLUE, (12, 9)),
           (553, 29.0, "CV core", BLUE, (10, 3)),
           (639, 7.0, "CV all 40", BLUE, (10, 3)),
           (623, 14.5, "OR best mascon", ORANGE, (10, -12)),
           (541, 3.3, "OR 300 km", ORANGE, (-10, 0))]
    for x, y, lab, c, off in pts:
        ax.scatter([x], [y], s=115, color=c, edgecolor=SURFACE, linewidth=1.4,
                   zorder=5, marker="s" if c == BLUE else "D")
        ax.annotate(lab, (x, y), textcoords="offset points", xytext=off,
                    fontsize=9, color=c,
                    ha="right" if off[0] < 0 else "left")

    ax.set_xlim(250, 1250); ax.set_ylim(0, 60)
    ax.set_xlabel("consumptive use over irrigated land, CU$_{irr}$  (mm/yr)")
    ax.set_ylabel("irrigated fraction of the footprint, f$_{irr}$  (%)")
    ax.set_title("B. what a new basin needs, from coverage statistics alone",
                 fontsize=10.5, color=INK, loc="left", pad=8)

    titleblock(fig, "A calibrated detection threshold for agricultural consumptive use in GRACE",
               f"Threshold: f$_{{irr}}$ × CU$_{{irr}}$ ≥ {D_need:.0f} mm/yr for a 2σ constraint on the consumptive-use "
               f"coefficient over ~20 years of GRACE.\n"
               f"Calibrated on two independent basins. Curve in A is σ(CU′) = {gamma:.2f}·CU/12 against a "
               f"{noise:.1f} mm/month dS/dt noise floor — not fitted to the points, derived from them.",
               axes_title_pt=11)
    fig.savefig(FIG / "fig2_threshold.png", dpi=170, bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- figure 3
def fig_series():
    s = pd.read_parquet(SIG / "flux_series.parquet")
    key = [k for k in s.index.get_level_values(0).unique() if "best" in k][0]
    d = s.loc[key].copy()
    d.index = pd.to_datetime(d.index)

    fig, axes = plt.subplots(2, 1, figsize=(11.4, 6.8), sharex=True,
                             height_ratios=[1.25, 1])

    ax = axes[0]
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.axvspan(pd.Timestamp("2017-07-01"), pd.Timestamp("2018-06-01"),
               color="#f2f1ea", zorder=0)
    ax.text(pd.Timestamp("2017-12-15"), 46, "GRACE / GRACE-FO gap\n(never differenced across)",
            ha="center", va="top", fontsize=8.5, color=MUTED)
    ax.plot(d.index, d["dsdt_ds"], color=BLUE, linewidth=1.7, zorder=3)
    ax.set_ylabel("dS/dt′   (mm/month)")
    ax.set_ylim(-72, 52)
    ax.set_title("A. deseasonalised storage change at mascon 1850 (52% irrigated)",
                 fontsize=10.5, color=INK, loc="left", pad=8)
    ax.legend([Line2D([], [], color=BLUE, lw=2)],
              ["GRACE GSFC dS/dt′"], frameon=False, fontsize=9, loc="upper left")

    ax = axes[1]
    ax.axhline(0, color=AXIS, linewidth=1)
    ax.axvspan(pd.Timestamp("2017-07-01"), pd.Timestamp("2018-06-01"),
               color="#f2f1ea", zorder=0)
    ax.plot(d.index, -d["cu_ds"], color=ORANGE, linewidth=1.9, zorder=4)
    ax.plot(d.index, d["ppt_ds"], color=AQUA, linewidth=1.3, alpha=0.85, zorder=3)
    ax.set_ylabel("mm/month")
    ax.set_xlabel("")
    ax.set_ylim(-105, 105)
    ax.set_title("B. the two candidate drivers, same scale as each other",
                 fontsize=10.5, color=INK, loc="left", pad=8)
    ax.legend([Line2D([], [], color=ORANGE, lw=2), Line2D([], [], color=AQUA, lw=2)],
              ["−CU′ (consumptive use, DWR ETAW)", "P′ (PRISM precipitation)"],
              frameon=False, fontsize=9, loc="upper left", ncol=2)
    # direct labels satisfy the relief rule for the aqua slot
    lo = d["ppt_ds"].abs().idxmax()
    ax.annotate("P′", (lo, d.loc[lo, "ppt_ds"]), color=AQUA, fontsize=10,
                fontweight="bold", xytext=(7, -2), textcoords="offset points")
    hi = d["cu_ds"].abs().idxmax()
    ax.annotate("−CU′", (hi, -d.loc[hi, "cu_ds"]), color=ORANGE, fontsize=10,
                fontweight="bold", xytext=(7, 3), textcoords="offset points")

    fp = pd.read_csv(OUT / "flux_results_footprints.csv")
    r = fp[fp["footprint"].str.contains("best")].iloc[0]
    titleblock(fig, "Consumptive use is large and well measured here — and still does not explain dS/dt",
               f"σ(CU′) = {r['cu_ds_std_mm']:.2f} mm/month against a {r['dsdt_noise_mm']:.2f} mm/month noise floor: "
               f"SNR {r['snr_vs_noisefloor']:.2f}, 16× Oregon's best mascon.\n"
               f"Raw r(dS/dt, −CU) = {r['r_raw']:+.2f} is shared seasonality. Deseasonalised it falls to "
               f"{r['r_deseason']:+.2f}, of which {r['induced_via_P']:+.2f} is induced through precipitation;\n"
               f"the partial correlation is {r['partial_r']:+.3f} (p = {r['partial_p']:.2f}).",
               axes_title_pt=11)
    fig.savefig(FIG / "fig3_series.png", dpi=170, bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)


# ---------------------------------------------------------------- figure 4
def fig_coeff():
    both = pd.read_csv(OUT / "flux_results_gsfc_vs_csr.csv")
    order = ["best native mascon (1850)", "300 km footprint",
             "irrigated core", "all 40 mascons"]
    labels = ["mascon 1850\n52% irrigated", "300 km footprint\n19.5%",
              "irrigated core\n29%", "all 40 mascons\n7%"]

    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    ax.axvspan(-1.15, -0.85, color="#f2f1ea", zorder=0)
    ax.axvline(-1, color=RED, linewidth=1.8, linestyle="--", zorder=2)
    ax.axvline(0, color=AXIS, linewidth=1.4, zorder=2)
    ax.text(-3.05, 5.32, "b = −1  consumptive use comes straight out of storage",
            color=RED, fontsize=9, ha="left", va="center")
    ax.text(-3.05, 5.02, "b =  0  no storage response", color=INK2,
            fontsize=9, ha="left", va="center")

    for i, fpname in enumerate(order):
        for j, (sol, col, mk) in enumerate([("GSFC", BLUE, "s"), ("CSR", ORANGE, "D")]):
            r = both[(both["fp"] == fpname) & (both["solution"] == sol)]
            if r.empty:
                continue
            r = r.iloc[0]
            y = i + (0.16 if j == 0 else -0.16)
            ax.errorbar(r["b_CU"], y, xerr=2 * r["se_CU"], fmt=mk, color=col,
                        markersize=8, capsize=4, linewidth=1.9,
                        markeredgecolor=SURFACE, markeredgewidth=1.1, zorder=4)

    y = len(order) + 0.35
    ax.errorbar(OREGON["b_CU"], y, xerr=2 * OREGON["se_CU"], fmt="o",
                color=MUTED, markersize=8, capsize=4, linewidth=1.9,
                markeredgecolor=SURFACE, markeredgewidth=1.1, zorder=4)
    ax.text(OREGON["b_CU"] + 2 * OREGON["se_CU"] + 0.3, y,
            "Oregon: interval spans 0 and −1 — no power", color=MUTED,
            fontsize=9, va="center")

    ax.set_yticks(list(range(len(order))) + [y])
    ax.set_yticklabels(labels + ["Oregon 300 km\n3.3% irrigated"], fontsize=9.5)
    ax.set_ylim(-0.6, y + 1.5)
    ax.set_xlim(-3.2, 11)
    ax.set_xlabel("b$_{CU}$ — regression coefficient of dS/dt′ on CU′  (±2σ)")
    ax.legend([Line2D([], [], color=BLUE, marker="s", lw=2, markeredgecolor=SURFACE),
               Line2D([], [], color=ORANGE, marker="D", lw=2, markeredgecolor=SURFACE)],
              ["GSFC RL06v2.0", "CSR RL06.3 (independent)"],
              frameon=False, fontsize=9.5, loc="lower right")
    ax.grid(axis="y", visible=False)

    # The 4.1σ exclusion holds in GSFC only. CSR's interval still contains −1,
    # so a title claiming the test "has power" without naming the solution
    # overstates a result that one of the two processing centres does not support.
    titleblock(fig, "The Central Valley test has power in GSFC; Oregon's had none in either solution",
               "Oregon's coefficient was +3.11 ± 3.55 — an interval containing both 0 and −1, so the null was uninterpretable.\n"
               "GSFC at mascon 1850 gives −0.035 ± 0.236, which excludes −1 at 4.1σ: consumptive use does NOT come 1:1 out of storage.\n"
               "CSR agrees on sign but has a noise floor twice as high, so its intervals still contain −1 at every footprint.\n"
               "The 4.1σ figure is therefore a GSFC result, not a GRACE result. Read the blue and orange bars together, not the blue alone.",
               axes_title_pt=0)
    fig.savefig(FIG / "fig4_coefficient.png", dpi=170, bbox_inches="tight",
                facecolor=SURFACE)
    plt.close(fig)


if __name__ == "__main__":
    fig_coverage(); print("fig1 done")
    fig_threshold(); print("fig2 done")
    fig_series(); print("fig3 done")
    fig_coeff(); print("fig4 done")
