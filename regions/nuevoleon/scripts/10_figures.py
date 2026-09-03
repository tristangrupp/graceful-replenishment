"""Figures. House style inherited from E:\\Water\\_shared\\region_figure.py.

Colour jobs, kept separate on purpose:
  * magnitude (reservoir capacity, always positive)  -> one hue, light->dark
  * polarity  (storage trend, signed)                -> two hues + neutral grey
  * identity  (a handful of named series)            -> fixed categorical order
No panel carries two y-scales.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap, Normalize, TwoSlopeNorm  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

sys.path.insert(0, r"E:\Water\_shared")
from region_figure import INK, INK2, MUTED, GRID, AXIS, SURFACE, titleblock  # noqa: E402

ROOT = Path(r"E:\Water\NuevoLeon")
SIG, TR, INV = ROOT / "signals", ROOT / "trends", ROOT / "inventory"
FIG = TR / "figures"
DROUGHT = (pd.Timestamp("2022-07-01"), pd.Timestamp("2023-04-30"))

# identity: fixed order, never cycled
C_TWS, C_RES, C_RESID, C_CSR = "#184f95", "#c07a2b", "#2f7d5c", "#8c4f8f"
SEQ = LinearSegmentedColormap.from_list("seq", ["#eef3fa", "#86b6ef", "#3987e5", "#184f95",
                                               "#0b2e5c"])
DIV = LinearSegmentedColormap.from_list("div", ["#8c3a1e", "#c98f6a", "#e8e6e0",
                                               "#7fa8dd", "#184f95"])

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
})


def nl_outline(ax):
    try:
        import geopandas as gpd
        nl = gpd.read_file(r"H:\water intelligence\soilmoisture\data\nuevo_leon.geojson")
        nl.boundary.plot(ax=ax, color=INK, lw=1.3, zorder=6)
    except Exception:
        pass


def border(ax, g):
    """Draw the GSFC basin-code boundary (which follows the Rio Grande here)."""
    us = g[g["country"] == "United States"]
    for _, r in us.iterrows():
        ax.add_patch(Rectangle((r.lon_min, r.lat_min), r.lon_max - r.lon_min,
                               r.lat_max - r.lat_min, fill=False, ec="#8c3a1e",
                               lw=1.6, ls=(0, (4, 2)), zorder=7))


def cells(ax, g, values, cmap, norm, label):
    for (_, r), v in zip(g.iterrows(), values):
        ax.add_patch(Rectangle((r.lon_min, r.lat_min), r.lon_max - r.lon_min,
                               r.lat_max - r.lat_min,
                               facecolor=cmap(norm(v)) if np.isfinite(v) else "#f0efe9",
                               edgecolor=SURFACE, lw=1.2, zorder=2))
    ax.set_xlim(g.lon_min.min() - 0.15, g.lon_max.max() + 0.15)
    ax.set_ylim(g.lat_min.min() - 0.15, g.lat_max.max() + 0.15)
    ax.set_aspect(1 / np.cos(np.radians(25.5)))
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    cb = ax.figure.colorbar(sm, ax=ax, fraction=0.042, pad=0.02)
    cb.set_label(label, fontsize=9, color=INK2)
    cb.outline.set_visible(False)
    cb.ax.tick_params(labelsize=8.5, color=AXIS)
    ax.set_xlabel("longitude", fontsize=9)
    ax.set_ylabel("latitude", fontsize=9)
    ax.grid(False)


def gapped(s):
    """Reindex to a complete monthly axis so missing GRACE months break the line.

    Dropping NaNs and plotting would draw a straight segment across the
    2017-07..2018-05 mission gap, which is not data.
    """
    s = s.dropna()
    idx = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    return s.reindex(idx)


def smooth(s, w=13):
    return s.rolling(w, center=True, min_periods=w // 2 + 1).mean()


def shade_drought(ax, label=True):
    ax.axvspan(*DROUGHT, color="#c98f6a", alpha=0.18, lw=0, zorder=0)
    if label:
        ax.annotate("SPI-12 drought\n2022-07 – 2023-04", xy=(DROUGHT[0], 1.0),
                    xycoords=("data", "axes fraction"), xytext=(4, -6),
                    textcoords="offset points", fontsize=8.5, color="#8c3a1e",
                    va="top", ha="left")


def load():
    g = pd.read_csv(TR / "post2020_gradient.csv")
    mas = pd.read_csv(SIG / "mascon_metadata.csv")
    g = g.merge(mas[["mascon_id", "lat_min", "lat_max", "lon_min", "lon_max"]], on="mascon_id")
    dams = pd.read_csv(INV / "dams_in_region.csv")
    per = pd.read_csv(INV / "reservoir_per_mascon.csv")
    ser = pd.read_csv(SIG / "nuevo_leon_series.csv", index_col=0, parse_dates=True)
    head = json.loads((TR / "nuevo_leon_headline.json").read_text())
    mag = json.loads((INV / "reservoir_magnitude.json").read_text())
    return g, dams, per, ser, head, mag


# ------------------------------------------------------------------ figure 1
def fig1(g, dams, per, mag):
    fig = plt.figure(figsize=(14.8, 11.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.22, 1], width_ratios=[1.0, 1.0],
                          hspace=0.34, wspace=0.46)

    ax = fig.add_subplot(gs[0, 0])
    v = per.set_index("mascon_id")["namo_mm"].reindex(g["mascon_id"]).fillna(0).to_numpy()
    cells(ax, g, v, SEQ, Normalize(0, np.nanmax(v)),
          "reservoir capacity (NAMO)\nas mm over the mascon")
    nl_outline(ax)
    big = dams.nlargest(8, "namo_hm3")
    ax.scatter(big["lon"], big["lat"], s=np.sqrt(big["namo_hm3"]) * 3.0, facecolor="none",
               edgecolor="#8c3a1e", lw=1.4, zorder=8)
    offs = {3152: (8, 8), 3153: (8, -14), 3154: (8, -14), 3150: (8, 6),
            3145: (-10, 8), 3140: (8, 5), 3242: (8, 5), 3149: (-10, 6)}
    for _, r in big.iterrows():
        nm = str(r["name"]).split(",")[0]
        dx, dy = offs.get(int(r["mascon_id"]), (8, 6))
        ax.annotate(nm, (r["lon"], r["lat"]), xytext=(dx, dy), textcoords="offset points",
                    fontsize=8.5, color=INK, zorder=9,
                    ha="left" if dx > 0 else "right",
                    bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.8))
    ax.set_title("A · Reservoir capacity per GRACE mascon", fontsize=11.5,
                 fontweight="bold", color=INK, loc="left", pad=8)

    ax = fig.add_subplot(gs[0, 1])
    top = dams.nlargest(8, "namo_mm").sort_values("namo_mm")
    rows = [(str(r["name"]).split(",")[0], float(r["namo_mm"])) for _, r in top.iterrows()]
    y = np.arange(len(rows))
    ax.barh(y, [r[1] for r in rows], color="#3987e5", height=0.62, zorder=3)
    ax.set_yticks(y, [r[0] for r in rows], fontsize=9)
    noise = mag["median_grace_noise_2sigma_mm"]
    ax.axvline(noise, color="#8c3a1e", lw=1.8, zorder=4)
    ax.annotate(f"GRACE 2σ noise floor\n{noise:.1f} mm", xy=(noise, len(rows) - 0.4),
                xytext=(8, 0), textcoords="offset points", fontsize=9, color="#8c3a1e",
                va="center")
    for yi, (_, val) in zip(y, rows):
        ax.annotate(f"{val:.0f}", (val, yi), xytext=(4, 0), textcoords="offset points",
                    fontsize=8.5, color=INK2, va="center")
    ax.set_xlim(0, max(r[1] for r in rows) * 1.20)
    ax.set_xlabel("mm equivalent water height, each over its own ~12,400 km² mascon")
    ax.grid(axis="y", visible=False)
    ax.set_title("B · Every large reservoir clears the noise floor", fontsize=11.5,
                 fontweight="bold", color=INK, loc="left", pad=8)

    ax = fig.add_subplot(gs[1, :])
    mty = pd.read_csv(SIG / "monterrey_system_storage_hm3.csv", index_col=0, parse_dates=True)
    s = gapped(mty.iloc[:, 0])
    ax.plot(s.index, s, color=C_RES, lw=2.0, zorder=4, label="El Cuchillo + Cerro Prieto + La Boca")
    ax.axhline(mag["monterrey_system_namo_hm3"], color=MUTED, lw=1.2, ls=":", zorder=3)
    ax.annotate(f"combined NAMO capacity {mag['monterrey_system_namo_hm3']:,.0f} hm³"
                f"  =  {mag['monterrey_system_mm_over_one_median_mascon']:.0f} mm if it sat in a single mascon",
                xy=(0.012, 0.055), xycoords="axes fraction", fontsize=9, color=INK2,
                va="bottom")
    shade_drought(ax)
    lo = s.loc["2022-01":"2023-06"].idxmin()
    ax.annotate(f"{s.loc[lo]:,.0f} hm³\n{lo:%b %Y}", (lo, s.loc[lo]), xytext=(10, 26),
                textcoords="offset points", fontsize=9, color="#8c3a1e",
                arrowprops=dict(arrowstyle="-", color="#8c3a1e", lw=1))
    ax.set_ylim(0, float(s.max()) * 1.15)
    ax.set_ylabel("storage (hm³)")
    ax.legend(frameon=False, loc="lower right", fontsize=9)
    ax.set_title("C · The Monterrey supply system, CONAGUA SINA daily monitoring",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)

    titleblock(
        fig,
        "Phase 1 · Reservoirs are 7× the GRACE noise floor, so they must be removed first",
        "The Monterrey system (El Cuchillo, Cerro Prieto, La Boca) holds 1,458 hm³ at full "
        "conservation level.\nSpread over one 12,400 km² GSFC mascon that is 118 mm of "
        "equivalent water height, against a 16.7 mm 2σ noise floor;\nits observed 2002–2026 "
        "range, 1,848 hm³, is 149 mm. Reservoirs are the largest identifiable term in "
        "several mascons.",
        axes_title_pt=11.5)
    p = FIG / "fig1_reservoir_magnitude.png"
    fig.savefig(p, dpi=165, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return p


# ------------------------------------------------------------------ figure 2
def fig2(g, ser, head):
    fig = plt.figure(figsize=(13.4, 10.2))
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1], hspace=0.34)

    ax = fig.add_subplot(gs[0])
    for k, c, lab in ((("gsfc_tws"), C_TWS, "GRACE total water storage (GSFC)"),
                      ("reservoir", C_RES, "reservoir component (CONAGUA + TWDB)"),
                      ("gsfc_minus_res", C_RESID, "residual: TWS − reservoirs")):
        s = gapped(ser[k])
        ax.plot(s.index, s, color=c, lw=0.9, alpha=0.35, zorder=3)
        ax.plot(s.index, smooth(s), color=c, lw=2.2, label=lab, zorder=4)
    ax.axhline(0, color=AXIS, lw=1)
    shade_drought(ax)
    ax.set_ylabel("mm equivalent water height")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.34 * (hi - lo))
    ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=3, columnspacing=1.6)
    ax.annotate(
        f"trend  TWS {head['trend_gsfc_tws_paired_mm_yr']:+.2f} mm/yr "
        f"(p = {head['p_gsfc_tws_paired']:.2f})"
        f"   ·   reservoirs {head['trend_reservoir_mm_yr']:+.2f}"
        f"   ·   residual {head['trend_gsfc_minus_res_mm_yr']:+.2f} "
        f"(p = {head['p_gsfc_minus_res']:.2f})"
        f"   ·   GSFC leakage-trend uncertainty "
        f"±{head['nl_weighted_leakage_trend_mm_yr']:.2f}",
        xy=(0.012, 0.80), xycoords="axes fraction", fontsize=9.5, color=INK2, va="top")
    ax.set_title("A · Nuevo León, area-weighted by each mascon's share of the state",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)

    ax = fig.add_subplot(gs[1])
    nl = g[g["nl_area_frac"] > 0.05].sort_values("tws_trend_paired_mm_yr")
    y = np.arange(len(nl))
    h = 0.26
    ax.barh(y + h, nl["tws_trend_paired_mm_yr"], height=h * 0.92, color=C_TWS,
            label="TWS", zorder=3)
    ax.barh(y, nl["res_trend_mm_yr"], height=h * 0.92, color=C_RES,
            label="reservoir component", zorder=3)
    ax.barh(y - h, nl["minus_res_trend_mm_yr"], height=h * 0.92, color=C_RESID,
            label="residual", zorder=3)
    # Without the leakage band drawn, every bar reads as a measured difference.
    # Most of these sit inside GSFC's own systematic trend uncertainty, which no
    # amount of record length removes, so the band has to be visible.
    lk = head["nl_weighted_leakage_trend_mm_yr"]
    ax.axvspan(-lk, lk, color="#eb6834", alpha=0.12, lw=0, zorder=0)
    for edge in (-lk, lk):
        ax.axvline(edge, color="#eb6834", ls="--", lw=1.4, zorder=2)

    lbl = [f"{int(r.mascon_id)}  ({r.lat_center:.0f}°N {abs(r.lon_180):.1f}°W)"
           f"   {r.nl_area_frac * 100:.0f}% in NL" for _, r in nl.iterrows()]
    ax.set_yticks(y, lbl, fontsize=8.5)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_xlabel("storage trend over the reservoir-covered months, "
                  "2002-04 to 2025-04 (mm/yr)")
    ax.grid(axis="y", visible=False)
    ax.legend(frameon=False, loc="lower right", fontsize=9, ncol=1)

    n_resid_out = int((nl["minus_res_trend_mm_yr"].abs() > lk).sum())
    ax.set_title(f"B · Per mascon: only {n_resid_out} of {len(nl)} residuals escape the "
                 f"±{lk:.2f} mm/yr leakage band",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)
    ax.annotate(f"Shaded band = GSFC's own leakage-trend uncertainty. Bars inside it are "
                f"indistinguishable from processing error.",
                xy=(0.0, -0.135), xycoords="axes fraction", fontsize=8.5, color=INK2, va="top")

    titleblock(
        fig,
        "Phase 3 · Removing the reservoirs removes two-thirds of the Nuevo León trend, "
        "and what is left is not resolved",
        f"Over the {head['n_months_gsfc_paired']} months where the reservoir record exists "
        f"(2002-04 .. {head['reservoir_record_last_month'][:7]}), GSFC total water storage over "
        f"Nuevo León falls at {head['trend_gsfc_tws_paired_mm_yr']:.2f} mm/yr "
        f"(p = {head['p_gsfc_tws_paired']:.2f}).\nThe measured reservoir component accounts for "
        f"{head['reservoir_share_of_gsfc_trend'] * 100:.0f}% of it. The residual, "
        f"{head['trend_gsfc_minus_res_mm_yr']:.2f} mm/yr (p = {head['p_gsfc_minus_res']:.2f}), is "
        f"not significant and is five times smaller than GSFC's own\nleakage-trend uncertainty "
        f"for these footprints ({head['nl_weighted_leakage_trend_mm_yr']:.2f} mm/yr). The residual "
        "is a residual: it still contains soil moisture and unmonitored small storage.",
        axes_title_pt=11.5)
    p = FIG / "fig2_decomposition.png"
    fig.savefig(p, dpi=165, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return p


# ------------------------------------------------------------------ figure 3
def fig3(g):
    fig = plt.figure(figsize=(13.4, 10.4))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.25, 1], hspace=0.30, wspace=0.24)
    lim = np.nanmax(np.abs(np.r_[g["post2020_tws_mm"], g["post2020_csr_mm"]]))
    norm = TwoSlopeNorm(vmin=-lim, vcenter=0, vmax=lim)

    for j, (col, name) in enumerate([("post2020_tws_mm", "GSFC RL06v2.0"),
                                     ("post2020_csr_mm", "CSR RL06.3")]):
        ax = fig.add_subplot(gs[0, j])
        cells(ax, g, g[col].to_numpy(), DIV, norm,
              "mean 2020–2026 storage anomaly (mm)")
        nl_outline(ax)
        border(ax, g)
        ax.set_title(f"{'AB'[j]} · {name}", fontsize=11.5, fontweight="bold",
                     color=INK, loc="left", pad=8)

    ax = fig.add_subplot(gs[1, 0])
    for cty, c, m in (("Mexico", C_TWS, "o"), ("United States", "#8c3a1e", "s")):
        s = g[g["country"] == cty]
        ax.scatter(s["tws_trend_mm_yr"], s["csr_trend_mm_yr"], s=52, marker=m,
                   facecolor=c, edgecolor=SURFACE, lw=1.2, zorder=4,
                   label=f"{cty} side of the Rio Grande (n = {len(s)})")
    lo = min(g["tws_trend_mm_yr"].min(), g["csr_trend_mm_yr"].min()) - 1
    hi = max(g["tws_trend_mm_yr"].max(), g["csr_trend_mm_yr"].max()) + 1
    ax.plot([lo, hi], [lo, hi], color=MUTED, lw=1.2, ls="--", zorder=2)
    ax.annotate("1 : 1", xy=(hi, hi), xytext=(-34, -18), textcoords="offset points",
                fontsize=9, color=MUTED)
    ax.set_xlim(lo, hi)
    ax.set_ylim(lo, hi)
    ax.set_xlabel("GSFC trend (mm/yr)")
    ax.set_ylabel("CSR trend (mm/yr)")
    ax.legend(frameon=False, loc="upper left", fontsize=9)
    ax.set_title("C · The two solutions agree over Mexico and not over Texas",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)

    ax = fig.add_subplot(gs[1, 1])
    ax.scatter(g["lat_center"] + np.random.RandomState(0).uniform(-.12, .12, len(g)),
               g["csr_r"], s=46, facecolor="#3987e5", edgecolor=SURFACE, lw=1.1, zorder=4)
    for _, r in g.nsmallest(4, "csr_r").iterrows():
        ax.annotate(f"mascon {int(r.mascon_id)}", (r.lat_center, r.csr_r), xytext=(9, -3),
                    textcoords="offset points", fontsize=8.5, color=INK2)
    ax.set_xlabel("mascon centre latitude (°N)")
    ax.set_ylabel("GSFC vs CSR series correlation")
    ax.set_ylim(0, 1)
    ax.set_title("D · Agreement per mascon", fontsize=11.5, fontweight="bold",
                 color=INK, loc="left", pad=8)

    titleblock(
        fig,
        "Phase 4 · The post-2020 gradient is real over Mexico and unconfirmed over Texas",
        "GSFC puts the strongest post-2020 drying in south Texas (mean −171 mm, trends to "
        "−14.3 mm/yr); CSR, sampled on the identical mascon\nfootprints with a Gulf land mask, "
        "puts it at −48 mm and −0.3 to −4.8 mm/yr. The dashed outline is GSFC's own "
        "`basin` region boundary,\nwhich follows the Rio Grande: the contrast lands on a change "
        "in GSFC's regularization region, and CSR does not reproduce it.",
        axes_title_pt=11.5)
    p = FIG / "fig3_gsfc_vs_csr.png"
    fig.savefig(p, dpi=165, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return p


# ------------------------------------------------------------------ figure 4
def fig4(ser, head):
    fig = plt.figure(figsize=(13.4, 10.4))
    gs = fig.add_gridspec(3, 1, hspace=0.40)

    ax = fig.add_subplot(gs[0])
    for k, c, lab in (("gsfc_tws", C_TWS, "GSFC total water storage"),
                      ("csr_tws", C_CSR, "CSR total water storage"),
                      ("gsfc_minus_res", C_RESID, "GSFC minus reservoirs")):
        s = gapped(ser[k])
        ax.plot(s.index, s, color=c, lw=0.9, alpha=0.32, zorder=3)
        ax.plot(s.index, smooth(s), color=c, lw=2.2, label=lab, zorder=4)
    ax.axhline(0, color=AXIS, lw=1)
    shade_drought(ax)
    ax.set_ylabel("mm")
    lo, hi = ax.get_ylim()
    ax.set_ylim(lo, hi + 0.30 * (hi - lo))
    ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=3, columnspacing=1.6)
    ax.set_title("A · Two independent GRACE solutions over Nuevo León",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)

    ax = fig.add_subplot(gs[1])
    dm = pd.read_parquet(SIG / "reservoir_absolute_mm.parquet")
    raw = pd.read_csv(INV / "dams_in_region.csv")
    import json as _json
    snap = sorted((ROOT / "raw" / "conagua_presas").glob("*.json"))
    keys = {"25.71_-99.28": ("El Cuchillo", "#184f95"),
            "24.94_-99.4": ("Cerro Prieto", "#c07a2b"),
            "25.43_-100.13": ("La Boca", "#2f7d5c")}
    rec = {k: {} for k in keys}
    for f in snap:
        j = _json.loads(f.read_text(encoding="utf-8"))
        for x in j:
            try:
                k = f"{round(float(x['latitud']), 2)}_{round(float(x['longitud']), 2)}"
            except (TypeError, ValueError):
                continue
            if k in keys:
                rec[k][pd.Timestamp(f.stem)] = float(x["almacenaactual"])
    for k, (lab, c) in keys.items():
        s = pd.Series(rec[k]).sort_index()
        s.index = s.index.to_period("M").to_timestamp()   # snapshots are day-15
        s = gapped(s)
        cap = float(raw.loc[raw["key"] == k, "namo_hm3"].iloc[0])
        ax.plot(s.index, s / cap * 100, color=c, lw=2.0, label=f"{lab} ({cap:,.0f} hm³)",
                zorder=4)
    shade_drought(ax, label=False)
    ax.set_ylabel("percent of NAMO capacity")
    ax.set_ylim(0, 175)
    ax.legend(frameon=False, loc="upper left", fontsize=9, ncol=3, columnspacing=1.6)
    ax.set_title("B · The three Monterrey reservoirs, as a fraction of their own capacity",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)

    ax = fig.add_subplot(gs[2])
    s = gapped(ser["chirps_cum_cm"])
    ax.fill_between(s.index, 0, s, color="#86b6ef", alpha=0.55, lw=0, zorder=3)
    ax.plot(s.index, s, color=C_TWS, lw=1.8, zorder=4,
            label="cumulative CHIRPS precipitation anomaly")
    ax.axhline(0, color=AXIS, lw=1)
    shade_drought(ax, label=False)
    ax.set_ylabel("cm")
    ax.legend(frameon=False, loc="lower left", fontsize=9)
    ax.set_title("C · Accumulated rainfall surplus or deficit over the same footprints",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)

    titleblock(
        fig,
        "Phase 4 · Timing against the 2022-07 – 2023-04 drought window",
        f"Storage bottoms out in {head['gsfc_minimum_month'][:7]} (GSFC, "
        f"{head['gsfc_minimum_mm']:.0f} mm) and {head['csr_minimum_month'][:7]} (CSR, "
        f"{head['csr_minimum_mm']:.0f} mm), after the SPI-12 window closes — storage integrates "
        "the deficit.\nAgainst a 2015–2019 reference, Nuevo León lost "
        f"{-head['drought_drawdown_gsfc_tws_mm']:.0f} mm (GSFC) during the window, of which "
        f"{-head['drought_drawdown_reservoir_mm']:.0f} mm is measured reservoir drawdown.\n"
        "The drought window itself is not computed here: it comes from the independent "
        "SMAP/SPI-12 study in H:\\water intelligence\\soilmoisture.",
        axes_title_pt=11.5)
    p = FIG / "fig4_drought_timing.png"
    fig.savefig(p, dpi=165, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)
    return p


if __name__ == "__main__":
    FIG.mkdir(parents=True, exist_ok=True)
    g, dams, per, ser, head, mag = load()
    for f in (fig1(g, dams, per, mag), fig2(g, ser, head), fig3(g), fig4(ser, head)):
        print("wrote", f)
