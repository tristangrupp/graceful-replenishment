"""Phase 3b + 4: dilution chain, and FLUX-SPACE comparison of GRACE dS/dt
against ET / consumptive-use fluxes.

FRAMING (corrected per user direction). GRACE measures a storage state S; its
derivative is the flux that closes the water balance

        dS/dt = P - ET - Q - net abstraction              [mm/month]

CU is therefore compared against dS/dt directly and is NEVER integrated to
meet a storage series. Integrating CU would assume every unit of consumptive
use becomes a permanent storage loss (zero recharge) -- badly wrong for
snowmelt-fed Oregon where aquifers refill seasonally, and the two series would
drift apart for structural rather than physical reasons.

Recharge is a first-class term. A basin can sustain large CU with no net
storage decline if recharge matches it, so the absence of a GRACE decline is
NOT evidence that CU is absent. The detectable signature would be a *mismatch*
between abstraction and replenishment.

dS/dt is a gap-aware CENTRED difference, defined only where both bracketing
calendar months carry a real solution -- nothing is differenced across the
11-month GRACE/GRACE-FO gap or any scattered missing month. Differencing
amplifies noise: for measurement noise of std sigma the centred difference has
std sigma/sqrt(2), which is carried explicitly into the detectability budget
rather than smoothed away.

Q (runoff) is NOT available and is not estimated. Its omission is discussed:
it is large and correlated with P, so the regression below controls for P and
reports the CU coefficient as partial, not causal.
"""
import sys
import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
from dark_water.depletion_watchlist.depletion.trend import _decimal_years, _design_matrix

NC = r"E:\Water\Oregan\analysis\raw\gsfc_mascons_halfdegree.nc"
P = r"E:\Water\Oregan\analysis\processed"
S = r"E:\Water\Oregan\analysis\signals"
INV = r"E:\Water\Oregan\analysis\inventory"
AF_M3 = 1233.48183754752
ACRE_M2 = 4046.8564224
R_EARTH = 6371007.181
OR_BOX = dict(lon0=-124.6, lon1=-116.4, lat0=41.9, lat1=46.3)
BUF = 3.0
DSDT_NOISE = 10.46      # mm/month, measured in p2b_signal_quality.py
OUT = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    OUT.append(s)


def sect(t):
    say("\n" + "=" * 74); say(t); say("=" * 74)


def cell_area_km2(lat_c, d=0.5):
    la0, la1 = np.radians(lat_c - d / 2), np.radians(lat_c + d / 2)
    return (R_EARTH ** 2) * np.radians(d) * (np.sin(la1) - np.sin(la0)) / 1e6


def r1(a):
    a = np.asarray(a, float); a = a[np.isfinite(a)]; a = a - a.mean()
    d = (a[:-1] ** 2).sum()
    return 0.0 if d == 0 else float((a[1:] * a[:-1]).sum() / d)


def corr_effn(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = np.asarray(x)[ok], np.asarray(y)[ok]
    if len(x) < 6:
        return dict(n=len(x), r=np.nan, p=np.nan, n_eff=np.nan)
    r = float(np.corrcoef(x, y)[0, 1])
    rx, ry = np.clip(r1(x), -.99, .99), np.clip(r1(y), -.99, .99)
    ne = max(3.0, len(x) * (1 - rx * ry) / (1 + rx * ry))
    t = r * np.sqrt(max(ne - 2, 1) / max(1 - r ** 2, 1e-12))
    return dict(n=int(len(x)), r=r, p=float(2 * stats.t.sf(abs(t), df=max(ne - 2, 1))),
                n_eff=float(ne))


def deseason(t, v):
    v = pd.Series(v)
    return (v - v.groupby(pd.DatetimeIndex(t).month).transform("mean")).values


def main():
    # ---------- GRACE ----------
    ds = xr.open_dataset(NC)
    lwe = ds["lwe_thickness"] * 10.0
    land = ds["land_mask"]
    lwe = lwe.assign_coords(lon=(((lwe.lon + 180) % 360) - 180)).sortby("lon")
    land = land.assign_coords(lon=(((land.lon + 180) % 360) - 180)).sortby("lon")
    b = dict(lon0=OR_BOX["lon0"] - BUF, lon1=OR_BOX["lon1"] + BUF,
             lat0=OR_BOX["lat0"] - BUF, lat1=OR_BOX["lat1"] + BUF)
    sub = lwe.sel(lon=slice(b["lon0"], b["lon1"]), lat=slice(b["lat0"], b["lat1"])).load()
    lnd = (land.sel(lon=slice(b["lon0"], b["lon1"]),
                    lat=slice(b["lat0"], b["lat1"])).load().values > 0)
    months = sub.time.values.astype("datetime64[M]").astype("datetime64[ns]")
    sub = sub.assign_coords(time=months).groupby("time").mean("time")
    per = pd.PeriodIndex(pd.to_datetime(sub.time.values), freq="M")
    gt = pd.to_datetime(sub.time.values)
    latv, lonv = sub.lat.values, sub.lon.values
    arr = sub.values
    AREA = cell_area_km2(latv)[:, None] * np.ones((1, len(lonv)))

    # ---------- field data ----------
    cm = pd.read_parquet(rf"{P}\cell_monthly.parquet")
    cm["lon_c"] = -180 + (cm["grid_i"] + 0.5) * 0.5
    cm["lat_c"] = -90 + (cm["grid_j"] + 0.5) * 0.5
    cm["time"] = pd.to_datetime(cm["time"])

    BEST = (-119.75, 45.75)      # top cell from the ranking (Boardman/Umatilla)
    say(f"Reference location: {BEST} (highest CU depth half-degree cell)")

    def footprint(kind):
        """Boolean (lat,lon) mask of LAND pixels in the footprint."""
        if kind == "pixel_0.5deg":
            m = (np.abs(latv[:, None] - BEST[1]) < 1e-6) & \
                (np.abs(lonv[None, :] - BEST[0]) < 1e-6)
        elif kind == "block_1deg":
            # the 2x2 group of half-degree cells filling the 1-degree box that
            # contains BEST -- approximates the native 1-arc-degree mascon size
            la0, lo0 = np.floor(BEST[1]), np.floor(BEST[0])
            m = (latv[:, None] >= la0) & (latv[:, None] <= la0 + 1) & \
                (lonv[None, :] >= lo0) & (lonv[None, :] <= lo0 + 1)
        elif kind == "footprint_300km":
            dx = (lonv[None, :] - BEST[0]) * 111.0 * np.cos(np.radians(BEST[1]))
            dy = (latv[:, None] - BEST[1]) * 111.0
            m = np.hypot(dx, dy) <= 150.0
        elif kind == "oregon_box":
            m = ((lonv[None, :] >= OR_BOX["lon0"]) & (lonv[None, :] <= OR_BOX["lon1"])
                 & (latv[:, None] >= OR_BOX["lat0"]) & (latv[:, None] <= OR_BOX["lat1"]))
        return m & lnd

    # ---------------------------------------------------------------
    sect("A. DILUTION CHAIN — irrigated fraction and CU depth vs footprint size")
    say("GRACE's measured decorrelation length is ~186 km at r=0.7 and ~281 km")
    say("at r=0.5 (p2b), and the Oregon box carries ~1.6 effective spatial DOF.")
    say("So the physically meaningful footprint is the 300 km one, NOT a pixel.\n")

    one = cm.drop_duplicates(subset=["grid_i", "grid_j", "huc8",
                                     "is_irrigated", "water_year"])
    rows = []
    fps = {}
    for kind in ["pixel_0.5deg", "block_1deg", "footprint_300km", "oregon_box"]:
        m = footprint(kind)
        fps[kind] = m
        area = AREA[m].sum()
        li, lj = np.where(m)
        cells = set(zip(np.round(lonv[lj], 2), np.round(latv[li], 2)))
        insel = cm.apply(lambda r: (round(r["lon_c"], 2), round(r["lat_c"], 2)) in cells,
                         axis=1) if False else \
            pd.Series([ (a, b_) in cells for a, b_ in
                        zip(cm["lon_c"].round(2), cm["lat_c"].round(2))], index=cm.index)
        onesel = pd.Series([ (a, b_) in cells for a, b_ in
                             zip(one["lon_c"].round(2), one["lat_c"].round(2))],
                           index=one.index)
        irr_ac = (one[onesel & one["is_irrigated"]]
                  .groupby("water_year")["acres"].sum().mean())
        cu_af = (cm[insel & cm["is_irrigated"]]
                 .groupby("water_year")["cuadj_af"].sum().mean())
        eta_af = (cm[insel].groupby("water_year")["eta_af"].sum().mean())
        irr_km2 = (irr_ac or 0) * ACRE_M2 / 1e6
        rows.append(dict(footprint=kind, n_land_px=int(m.sum()),
                         land_km2=area, irr_km2=irr_km2,
                         irr_frac_pct=100 * irr_km2 / area,
                         cu_af_yr=cu_af or 0,
                         cu_mm_yr=(cu_af or 0) * AF_M3 / (area * 1e6) * 1000,
                         eta_mm_yr=(eta_af or 0) * AF_M3 / (area * 1e6) * 1000))
    dil = pd.DataFrame(rows)
    say(dil.to_string(index=False, float_format=lambda x: f"{x:,.2f}"))
    dil.to_parquet(rf"{P}\dilution_chain.parquet", index=False)

    say("\nCU expressed as a monthly depth in the IRRIGATION SEASON is what")
    say("GRACE would have to see; annual mean depth understates the peak.")

    # ---------------------------------------------------------------
    sect("B. MONTHLY FLUX SERIES AND COMPARISON")
    results = []
    for kind in ["pixel_0.5deg", "block_1deg", "footprint_300km", "oregon_box"]:
        m = fps[kind]
        area_m2 = AREA[m].sum() * 1e6
        w = np.where(m, np.cos(np.radians(latv))[:, None], 0.0)
        sser = (arr * w[None]).sum(axis=(1, 2)) / w.sum()

        idx = {p: i for i, p in enumerate(per)}
        d = np.full(len(sser), np.nan)
        for i, p in enumerate(per):
            a, bb = idx.get(p - 1), idx.get(p + 1)
            if a is not None and bb is not None:
                d[i] = (sser[bb] - sser[a]) / 2.0

        g = pd.DataFrame({"time": gt, "tws_mm": sser, "dSdt": d})

        li, lj = np.where(m)
        cells = set(zip(np.round(lonv[lj], 2), np.round(latv[li], 2)))
        sel = pd.Series([(a, b_) in cells for a, b_ in
                         zip(cm["lon_c"].round(2), cm["lat_c"].round(2))], index=cm.index)
        fm = cm[sel]
        fl = fm.groupby("time", as_index=False).agg(
            eta_af=("eta_af", "sum"), ppt_af=("ppt_af", "sum"),
            acres=("acres", "sum"))
        cu = (fm[fm.is_irrigated].groupby("time", as_index=False)
              .agg(cuadj_af=("cuadj_af", "sum"), aw_af=("aw_af", "sum")))
        fl = fl.merge(cu, on="time", how="left").fillna(0)

        # CU / ETa / AW: an abstraction FLUX, correctly expressed as a depth
        # spread over the whole footprint -- that is what GRACE would sense.
        for a_, mm_ in [("eta_af", "eta"), ("cuadj_af", "cu"), ("aw_af", "aw")]:
            fl[mm_] = fl[a_] * AF_M3 / area_m2 * 1000

        # PRECIPITATION IS DIFFERENT. ppt_af is the gridMET precip volume over
        # the FIELD polygons only. Dividing it by the footprint area would
        # shrink P by the field-area fraction (3-25%) and inflate any
        # regression coefficient on P by its reciprocal. P must stay an areal
        # DEPTH: volume / field area, i.e. the area-weighted mean gridMET
        # precipitation depth over agricultural land, used as a proxy for
        # footprint-mean precipitation.
        fl["ppt"] = np.where(fl["acres"] > 0,
                             fl["ppt_af"] / fl["acres"] * 12.0 * 25.4, np.nan)
        #   acre-ft / acre = ft -> x12 in -> x25.4 mm

        mrg = g.merge(fl, on="time", how="inner")
        mrg = mrg[(mrg.time >= "2002-04-01") & (mrg.time <= "2022-10-01")].reset_index(drop=True)
        for c in ["dSdt", "cu", "ppt", "eta", "aw", "tws_mm"]:
            mrg[c + "_ds"] = deseason(mrg["time"], mrg[c].values)
        mrg["footprint"] = kind
        results.append(mrg)

        row = dil[dil.footprint == kind].iloc[0]
        say(f"\n--- {kind}: land {row.land_km2:,.0f} km2, "
            f"irr {row.irr_frac_pct:.2f}%, CU {row.cu_mm_yr:.1f} mm/yr ---")
        say(f"  months overlapping GRACE+ET: {len(mrg)}, "
            f"with defined dS/dt: {int(np.isfinite(mrg.dSdt).sum())}")
        say(f"  TWS    std {mrg.tws_mm.std():7.2f} mm   "
            f"seasonal p2p {mrg.tws_mm.max()-mrg.tws_mm.min():7.1f} mm")
        say(f"  dS/dt  std {mrg.dSdt.std():7.2f} mm/mo  "
            f"deseasonalised {mrg.dSdt_ds.std():7.2f} mm/mo")
        say(f"  CU     std {mrg.cu.std():7.2f} mm/mo  "
            f"deseasonalised {mrg.cu_ds.std():7.2f} mm/mo  "
            f"Jul mean {mrg[mrg.time.dt.month==7].cu.mean():.1f} mm/mo")
        say(f"  PPT    std {mrg.ppt.std():7.2f} mm/mo  "
            f"deseasonalised {mrg.ppt_ds.std():7.2f} mm/mo")

        say("\n  RAW correlations (both series strongly seasonal — NOT evidence):")
        for lab, xx, yy in [("dS/dt vs -CU", mrg.dSdt, -mrg.cu),
                            ("dS/dt vs  P ", mrg.dSdt, mrg.ppt)]:
            c = corr_effn(xx.values, yy.values)
            say(f"    {lab}: r={c['r']:+.3f} p={c['p']:.3g} n={c['n']} "
                f"n_eff={c['n_eff']:.0f}")
        say("  DESEASONALISED (the only version that can support a claim):")
        for lab, xx, yy in [("dS/dt vs -CU", mrg.dSdt_ds, -mrg.cu_ds),
                            ("dS/dt vs  P ", mrg.dSdt_ds, mrg.ppt_ds),
                            ("  P   vs  CU", mrg.ppt_ds, mrg.cu_ds)]:
            c = corr_effn(xx.values, yy.values)
            say(f"    {lab}: r={c['r']:+.3f} p={c['p']:.3g} n={c['n']} "
                f"n_eff={c['n_eff']:.0f}")

        sb = mrg.dropna(subset=["dSdt_ds", "ppt_ds", "cu_ds"])
        X = np.column_stack([np.ones(len(sb)), sb.ppt_ds, sb.cu_ds])
        y = sb.dSdt_ds.values
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        res = y - X @ beta
        dof = len(sb) - X.shape[1]
        cov = np.linalg.inv(X.T @ X) * (res @ res) / dof
        se = np.sqrt(np.diag(cov))
        rr = r1(res)
        infl = np.sqrt(max((1 + rr) / max(1 - rr, 1e-6), 1.0))
        say(f"\n  OLS  dS/dt' = a + b1*P' + b2*CU'   (n={len(sb)}, "
            f"SE inflated x{infl:.2f} for AR(1))")
        say(f"    b1 (P)  = {beta[1]:+.3f} +/- {se[1]*infl:.3f}")
        say(f"    b2 (CU) = {beta[2]:+.3f} +/- {se[2]*infl:.3f}  "
            f"[expected ~ -1 if CU came straight out of storage]")

        # Partial correlation of dS/dt' with CU' controlling for P'. CU' and P'
        # are strongly anticorrelated (irrigation demand rises when it is dry),
        # so the raw dS/dt'-CU' correlation is largely induced by P. This
        # removes that path.
        def resid_of(a, bb):
            A = np.column_stack([np.ones(len(bb)), bb])
            cf, *_ = np.linalg.lstsq(A, a, rcond=None)
            return a - A @ cf
        rx = resid_of(sb.dSdt_ds.values, sb.ppt_ds.values)
        ry = resid_of(sb.cu_ds.values, sb.ppt_ds.values)
        pc = corr_effn(rx, -ry)
        rraw = corr_effn(sb.dSdt_ds.values, -sb.cu_ds.values)
        say(f"    partial corr(dS/dt', -CU' | P') = {pc['r']:+.3f} "
            f"p={pc['p']:.3g}   (raw was {rraw['r']:+.3f})")
        rdp = corr_effn(sb.dSdt_ds.values, sb.ppt_ds.values)["r"]
        rcp = corr_effn(sb.cu_ds.values, sb.ppt_ds.values)["r"]
        say(f"    correlation induced purely via P: "
            f"{-rdp*rcp:+.3f}  [= -r(dS/dt',P')*r(CU',P')]")

        say("\n  DETECTABILITY BUDGET")
        say(f"    measured GRACE dS/dt noise floor : {DSDT_NOISE:.2f} mm/month")
        say(f"    deseasonalised CU signal std     : {mrg.cu_ds.std():.2f} mm/month")
        snr = mrg.cu_ds.std() / DSDT_NOISE
        say(f"    SNR (CU' / noise)                : {snr:.3f}")
        say(f"    months needed for a 2-sigma detection at this SNR: "
            f"{(2/snr)**2 if snr>0 else np.inf:,.0f}")
        say(f"    CU' explains at most "
            f"{100*(mrg.cu_ds.std()/mrg.dSdt_ds.std())**2:.2f}% of dS/dt' variance")

    pd.concat(results).to_parquet(rf"{S}\flux_series.parquet", index=False)
    with open(rf"{INV}\flux_comparison.txt", "w") as f:
        f.write("\n".join(OUT))
    say("\nwrote signals/flux_series.parquet, inventory/flux_comparison.txt")


if __name__ == "__main__":
    main()
