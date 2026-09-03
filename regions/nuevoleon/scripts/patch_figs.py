import io
p = r"E:\Water\NuevoLeon\scripts\10_figures.py"
s = io.open(p, encoding="utf-8").read()

s = s.replace(
"def shade_drought(ax, label=True):",
'''def gapped(s):
    """Reindex to a complete monthly axis so missing GRACE months break the line.

    Dropping NaNs and plotting would draw a straight segment across the
    2017-07..2018-05 mission gap, which is not data.
    """
    s = s.dropna()
    idx = pd.date_range(s.index.min(), s.index.max(), freq="MS")
    return s.reindex(idx)


def smooth(s, w=13):
    return s.rolling(w, center=True, min_periods=w // 2 + 1).mean()


def shade_drought(ax, label=True):''', 1)

s = s.replace(
'''    fig = plt.figure(figsize=(13.4, 10.6))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.22, 1], width_ratios=[1.15, 1],
                          hspace=0.30, wspace=0.26)''',
'''    fig = plt.figure(figsize=(14.8, 11.2))
    gs = fig.add_gridspec(2, 2, height_ratios=[1.22, 1], width_ratios=[1.0, 1.0],
                          hspace=0.34, wspace=0.46)''')

s = s.replace(
'''    big = dams[dams["namo_hm3"] > 200]
    ax.scatter(big["lon"], big["lat"], s=np.sqrt(big["namo_hm3"]) * 3.2, facecolor="none",
               edgecolor="#8c3a1e", lw=1.4, zorder=8)
    for _, r in big.iterrows():
        nm = str(r["name"]).split(",")[0]
        ax.annotate(nm, (r["lon"], r["lat"]), xytext=(6, 5), textcoords="offset points",
                    fontsize=8, color=INK, zorder=9)''',
'''    big = dams.nlargest(8, "namo_hm3")
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
                    bbox=dict(boxstyle="round,pad=0.15", fc=SURFACE, ec="none", alpha=0.8))''')

s = s.replace(
'''    rows = [("Vicente Guerrero / Las Adjuntas", 316.1), ("Falc\u00f3n (whole lake)", 265.1),
            ("La Amistad (whole lake)", 324.5), ("El Cuchillo", 90.6),
            ("Don Mart\u00edn", 70.5), ("El Az\u00facar / Marte R. G\u00f3mez", 63.1),
            ("Cerro Prieto", 24.2), ("La Boca", 2.8)]
    rows = sorted(rows, key=lambda t: t[1])''',
'''    top = dams.nlargest(8, "namo_mm").sort_values("namo_mm")
    rows = [(str(r["name"]).split(",")[0], float(r["namo_mm"])) for _, r in top.iterrows()]''')

s = s.replace(
'''    ax.set_xlim(0, 400)
    ax.set_xlabel("mm equivalent water height over the dam\'s own 12,400 km\u00b2 mascon")''',
'''    ax.set_xlim(0, max(r[1] for r in rows) * 1.20)
    ax.set_xlabel("mm equivalent water height, each over its own ~12,400 km\u00b2 mascon")''')

s = s.replace(
'''    s = mty.iloc[:, 0]
    ax.plot(s.index, s, color=C_RES, lw=2.0, zorder=4,''',
'''    s = gapped(mty.iloc[:, 0])
    ax.plot(s.index, s, color=C_RES, lw=2.0, zorder=4,''')

s = s.replace('xy=(0.012, 0.93), xycoords="axes fraction", fontsize=9, color=INK2, va="top")',
              'xy=(0.012, 0.055), xycoords="axes fraction", fontsize=9, color=INK2,\n                va="bottom")')
s = s.replace('f"  =  {mag[\'monterrey_system_mm_over_one_median_mascon\']:.0f} mm over one mascon",',
              'f"  =  {mag[\'monterrey_system_mm_over_one_median_mascon\']:.0f} mm '
              'if it sat in a single mascon",')

s = s.replace(
'''    ax.set_ylim(0, mag["monterrey_system_namo_hm3"] * 1.35)
    ax.set_ylabel("storage (hm\u00b3)")
    ax.legend(frameon=False, loc="upper right", fontsize=9)''',
'''    ax.set_ylim(0, float(s.max()) * 1.15)
    ax.set_ylabel("storage (hm\u00b3)")
    ax.legend(frameon=False, loc="lower right", fontsize=9)''')

s = s.replace(
'''                      ("gsfc_minus_res", C_RESID, "residual: TWS \u2212 reservoirs")):
        s = ser[k].dropna()
        ax.plot(s.index, s, color=c, lw=2.0, label=lab, zorder=4)''',
'''                      ("gsfc_minus_res", C_RESID, "residual: TWS \u2212 reservoirs")):
        s = gapped(ser[k])
        ax.plot(s.index, s, color=c, lw=0.9, alpha=0.35, zorder=3)
        ax.plot(s.index, smooth(s), color=c, lw=2.2, label=lab, zorder=4)''')

s = s.replace('ax.legend(frameon=False, loc="lower left", fontsize=9, ncol=3)\n    ax.set_title("B \u00b7 Per mascon',
              'ax.legend(frameon=False, loc="lower right", fontsize=9, ncol=1)\n    ax.set_title("B \u00b7 Per mascon')

s = s.replace('ax.annotate("1 : 1", xy=(hi, hi), xytext=(-26, 6), textcoords="offset points",',
              'ax.annotate("1 : 1", xy=(hi, hi), xytext=(-34, -18), textcoords="offset points",')
s = s.replace('ax.annotate(f"{int(r.mascon_id)}", (r.lat_center, r.csr_r), xytext=(6, -3),',
              'ax.annotate(f"mascon {int(r.mascon_id)}", (r.lat_center, r.csr_r), xytext=(9, -3),')

s = s.replace(
'''                      ("gsfc_minus_res", C_RESID, "GSFC minus reservoirs")):
        s = ser[k].dropna()
        ax.plot(s.index, s, color=c, lw=2.0, label=lab, zorder=4)''',
'''                      ("gsfc_minus_res", C_RESID, "GSFC minus reservoirs")):
        s = gapped(ser[k])
        ax.plot(s.index, s, color=c, lw=0.9, alpha=0.32, zorder=3)
        ax.plot(s.index, smooth(s), color=c, lw=2.2, label=lab, zorder=4)''')

s = s.replace('        s = pd.Series(rec[k]).sort_index()',
              '        s = gapped(pd.Series(rec[k]).sort_index())')
s = s.replace('    s = ser["chirps_cum_cm"].dropna()', '    s = gapped(ser["chirps_cum_cm"])')

io.open(p, "w", encoding="utf-8").write(s)
print("patched")
