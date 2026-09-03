"""Figure: what remains of the Nuevo Leon signal once reservoirs and soil moisture go.

Written to avoid three ways this could mislead:

1. The residual is a drought excursion that has largely recovered, not a steady
   decline. A linear trend through it is dominated by the 2022-2024 dip, so the
   fitted line is drawn explicitly and the recovery is marked, rather than a
   slope being quoted as though the series were monotonic.
2. A p-value against zero ignores GSFC's systematic leakage-trend uncertainty,
   which is a floor no amount of record length removes. It is drawn on every
   panel where a trend is quoted.
3. Mascons barely inside Nuevo Leon were shown alongside ones almost entirely
   inside it. State fraction is now encoded, not just written in the label.
"""

import json
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
from region_figure import AXIS, GRID, INK, INK2, MUTED, SURFACE, titleblock  # noqa: E402

NL = Path(r"E:\Water\NuevoLeon")
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
DROUGHT = (pd.Timestamp("2022-07-01"), pd.Timestamp("2023-04-30"))
PRE = ("2016-01", "2021-12")
POST = "2025-01"

plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Segoe UI", "DejaVu Sans"],
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
})


def smooth(s, w=7):
    return s.rolling(w, center=True, min_periods=w // 2 + 1).mean()


def main():
    reg = pd.read_csv(NL / "signals" / "smap_decomposition_series.csv",
                      index_col=0, parse_dates=True)
    s = json.loads((NL / "trends" / "smap_decomposition_summary.json").read_text())
    per = pd.read_csv(NL / "trends" / "smap_per_mascon.csv")
    leak = json.loads((NL / "trends" / "nuevo_leon_headline.json").read_text())
    lk = leak["nl_weighted_leakage_trend_mm_yr"]

    resid = reg["residual"].dropna()
    pre = resid[PRE[0]:PRE[1]].mean()
    trough_t, trough = resid.idxmin(), resid.min()
    post = resid[POST:].mean()
    recovered = 100 * (post - trough) / (pre - trough)

    fig = plt.figure(figsize=(12.6, 11.2))
    gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 1.15, 1], hspace=0.34)
    ax_a, ax_b, ax_c = (fig.add_subplot(gs[0]), None, None)
    ax_b = fig.add_subplot(gs[1], sharex=ax_a)
    ax_c = fig.add_subplot(gs[2])

    # ---- A: the measured components ------------------------------------
    ax = ax_a
    ax.axhline(0, color=AXIS, lw=1)
    for col, c, lab in [("tws", INK, "GRACE total water storage (all water)"),
                        ("reservoir", BLUE, "reservoirs — CONAGUA/TWDB gauge volumes"),
                        ("soil_moisture", AQUA, "soil moisture — SMAP L4, top 1 m")]:
        ax.plot(reg.index, smooth(reg[col]), color=c, lw=2.0, label=lab)
    ax.axvspan(*DROUGHT, color=GRID, alpha=0.85, lw=0, zorder=0)
    ax.annotate("2022 drought", xy=(DROUGHT[0], 0.03), xycoords=("data", "axes fraction"),
                xytext=(4, 0), textcoords="offset points", fontsize=8.5, color=MUTED)
    ax.set_ylabel("mm equivalent\nwater height")
    ax.set_title("A · The three measured components, seasonal cycle removed",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)
    ax.legend(frameon=False, fontsize=9, loc="lower left", ncol=1)
    ax.set_title("A · The three measured components, seasonal cycle removed"
                 "      (gaps in black are GRACE's own missing months, never interpolated)",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)

    # ---- B: the residual, with the fitted line made visible -------------
    ax = ax_b
    ax.axhline(0, color=AXIS, lw=1)
    ax.axvspan(*DROUGHT, color=GRID, alpha=0.85, lw=0, zorder=0)
    ax.plot(reg.index, smooth(reg["tws_minus_reservoir_only"]), color=ORANGE, lw=1.6,
            alpha=0.75, label="reservoirs removed")
    ax.plot(reg.index, smooth(reg["residual"]), color=YELLOW, lw=2.6,
            label="reservoirs + soil moisture removed")

    # The straight line that "-4.40 mm/yr" actually refers to.
    t = (resid.index - resid.index[0]).days / 365.25
    fitline = np.polyval(np.polyfit(t, resid.values, 1), t)
    ax.plot(resid.index, fitline, color=INK, ls="--", lw=1.6,
            label=f"linear fit, {s['trend_residual_mm_yr']:+.2f} mm/yr — "
                  f"a poor model for this shape")

    for y, lab in [(pre, f"pre-drought mean {pre:+.0f}"), (post, f"2025 mean {post:+.0f}")]:
        ax.axhline(y, color=MUTED, ls=":", lw=1.1)
        ax.annotate(lab, xy=(0.995, y), xycoords=("axes fraction", "data"),
                    xytext=(0, 3), textcoords="offset points", ha="right",
                    fontsize=8.5, color=MUTED)
    ax.annotate(f"trough {trough:+.0f} mm\n{trough_t:%Y-%m}",
                xy=(trough_t, trough), xytext=(8, -4), textcoords="offset points",
                fontsize=8.5, color=INK2)

    ax.set_ylabel("mm equivalent\nwater height")
    ax.set_title(f"B · The residual falls and then recovers {recovered:.0f}% of the drop",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)
    ax.legend(frameon=False, fontsize=9, loc="lower left")

    # ---- C: per-mascon residual against the leakage floor ---------------
    ax = ax_c
    keep = per[per["nl_frac"] > 0.05].sort_values("residual_trend")
    y = np.arange(len(keep))
    for i, r in enumerate(keep.itertuples()):
        beats = abs(r.residual_trend) > lk
        mostly_in = r.nl_frac >= 0.30
        ax.barh(i, r.residual_trend, height=0.62,
                color=YELLOW if beats else MUTED,
                alpha=1.0 if mostly_in else 0.45,
                hatch=None if mostly_in else "///", edgecolor=SURFACE)
    ax.axvspan(-lk, lk, color=ORANGE, alpha=0.13, lw=0, zorder=0)
    ax.axvline(-lk, color=ORANGE, ls="--", lw=1.6)
    ax.axvline(0, color=AXIS, lw=1)
    ax.set_yticks(y)
    ax.set_yticklabels([f"{int(r.mascon_id)}  {r.lat:.0f}°N {abs(r.lon):.1f}°W"
                        f"  ({100 * r.nl_frac:.0f}% in NL)" for r in keep.itertuples()],
                       fontsize=8.5)
    n_clear = int((keep["residual_trend"].abs() > lk).sum())
    n_clear_in = int(((keep["residual_trend"].abs() > lk) & (keep["nl_frac"] >= 0.30)).sum())
    ax.set_xlabel("residual trend, 2016–2025 (mm/yr).  Negative = storage loss.", labelpad=8)
    ax.set_title(f"C · {n_clear} of {len(keep)} mascons clear GSFC's own leakage uncertainty "
                 f"({n_clear_in} of them mostly inside the state)",
                 fontsize=11.5, fontweight="bold", color=INK, loc="left", pad=8)
    ax.grid(axis="y", visible=False)
    ax.set_ylim(-0.9, len(keep) - 0.3)
    ax.annotate(f"Shaded band = ±{lk:.2f} mm/yr GSFC leakage-trend uncertainty. A bar inside it is "
                f"indistinguishable from processing error,\nhowever small its p-value against zero. "
                f"Hatched bars are mascons less than 30% inside Nuevo León.",
                xy=(0.0, -0.22), xycoords="axes fraction", fontsize=8.5, color=INK2, va="top")

    titleblock(
        fig,
        "Nuevo León: a drought excursion that has largely recovered, not a steady decline",
        f"GRACE weighs all water at once, so reservoirs and soil moisture are subtracted using "
        f"independent measurements to see what is left.\nReservoirs are CONAGUA and TWDB gauge "
        f"volumes (1 hm³ = 0.081 mm over a 12,400 km² mascon); soil moisture is SMAP L4 root-zone\n"
        f"water content × 1000 mm. Soil moisture's own trend is not significant "
        f"(p = {s['p_soil_moisture']:.2f}) and removing it barely moves the residual.\n"
        f"{s['n_months']} months {s['window'][0]}–{s['window'][1]}, {s['n_mascons']} mascons "
        f"weighted by area inside the state. This 10-year window is dominated by one drought, so "
        f"no slope\nfitted across it should be read as a long-term rate.",
        axes_title_pt=11.5,
    )
    out = NL / "trends" / "figures" / "fig5_smap_decomposition.png"
    fig.savefig(out, dpi=170, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)

    stats = {"pre_drought_mean_mm": float(pre), "trough_mm": float(trough),
             "trough_month": f"{trough_t:%Y-%m}", "post_2025_mean_mm": float(post),
             "pct_of_drop_recovered": float(recovered),
             "linear_trend_mm_yr": s["trend_residual_mm_yr"],
             "leakage_trend_uncertainty_mm_yr": lk,
             "caution": ("The linear trend is dominated by a single drought excursion that has "
                         "since largely recovered; it is not a secular depletion rate.")}
    (NL / "trends" / "smap_recovery_stats.json").write_text(json.dumps(stats, indent=2))
    print("wrote", out)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
