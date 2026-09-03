import io
p = r"E:\Water\NuevoLeon\scripts\10_figures.py"
s = io.open(p, encoding="utf-8").read()

old_annot = s[s.index('    ax.annotate(\n        f"trend  TWS'):s.index('    ax.set_title("A \u00b7 Nuevo Le\u00f3n')]
new_annot = '''    ax.annotate(
        f"trend  TWS {head['trend_gsfc_tws_paired_mm_yr']:+.2f} mm/yr "
        f"(p = {head['p_gsfc_tws_paired']:.2f})"
        f"   \u00b7   reservoirs {head['trend_reservoir_mm_yr']:+.2f}"
        f"   \u00b7   residual {head['trend_gsfc_minus_res_mm_yr']:+.2f} "
        f"(p = {head['p_gsfc_minus_res']:.2f})"
        f"   \u00b7   GSFC leakage-trend uncertainty "
        f"\u00b1{head['nl_weighted_leakage_trend_mm_yr']:.2f}",
        xy=(0.012, 0.80), xycoords="axes fraction", fontsize=9.5, color=INK2, va="top")
'''
s = s.replace(old_annot, new_annot)

old_tb = s[s.index('    titleblock(\n        fig,\n        "Phase 3'):s.index('    p = FIG / "fig2_decomposition.png"')]
new_tb = '''    titleblock(
        fig,
        "Phase 3 \u00b7 Removing the reservoirs removes two-thirds of the Nuevo Le\u00f3n trend, "
        "and what is left is not resolved",
        f"Over the {head['n_months_gsfc_paired']} months where the reservoir record exists "
        f"(2002-04 .. {head['reservoir_record_last_month'][:7]}), GSFC total water storage over "
        f"Nuevo Le\u00f3n falls at {head['trend_gsfc_tws_paired_mm_yr']:.2f} mm/yr "
        f"(p = {head['p_gsfc_tws_paired']:.2f}).\\nThe measured reservoir component accounts for "
        f"{head['reservoir_share_of_gsfc_trend'] * 100:.0f}% of it. The residual, "
        f"{head['trend_gsfc_minus_res_mm_yr']:.2f} mm/yr (p = {head['p_gsfc_minus_res']:.2f}), is "
        f"not significant and is five times smaller than GSFC's own\\nleakage-trend uncertainty "
        f"for these footprints ({head['nl_weighted_leakage_trend_mm_yr']:.2f} mm/yr). The residual "
        "is a residual: it still contains soil moisture and unmonitored small storage.",
        axes_title_pt=11.5)
'''
s = s.replace(old_tb, new_tb)
io.open(p, "w", encoding="utf-8").write(s)
print("ok")
