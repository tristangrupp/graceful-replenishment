"""Phase 4 - flux-space comparison, mirroring the Oregon method exactly.

    dS/dt = P - ET - Q - net abstraction

dS/dt is a GAP-AWARE CENTRED DIFFERENCE of the GRACE mascon series: nothing is
ever differenced across the 2017-07..2018-05 mission gap, or across any of the
33 absent months. Consumptive use is compared against dS/dt DIRECTLY and is
never integrated to meet a storage series, because integrating assumes zero
recharge and the Central Valley has a great deal of it.

Everything is deseasonalised before any correlation is claimed: CU and dS/dt
both cycle annually and will correlate strongly for reasons that have nothing
to do with causality. Precipitation is controlled for and the PARTIAL
correlation is the reported number.

The regression is
    dS/dt' = b0 + b1 P' + b2 CU'
and the physical prediction is b2 = -1: a millimetre consumed is a millimetre
of storage not there. b1 should be positive and below 1.

Run at four nested footprints so coverage can be traded against signal, which
is what the detection threshold needs.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, r"E:\Water\_shared")
from grace_region import haversine

OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")
SIG = Path(r"E:\Water\CentralValley\signals")
SIG.mkdir(parents=True, exist_ok=True)


def gap_aware_dsdt(s):
    full = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"))
    fwd, back = full.shift(-1), full.shift(1)
    out = (fwd - back) / 2.0
    out[fwd.isna() | back.isna()] = np.nan
    return out


def deseason(s):
    return s - s.groupby(s.index.month).transform("mean")


def noise_floor(s):
    full = s.reindex(pd.date_range(s.index.min(), s.index.max(), freq="MS"))
    d2 = full.shift(1) - 2 * full + full.shift(-1)
    d2[full.shift(1).isna() | full.isna() | full.shift(-1).isna()] = np.nan
    return float(d2.std() / np.sqrt(6.0))


def n_eff(x):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) < 5:
        return float(len(x))
    r1 = np.clip(np.corrcoef(x[1:], x[:-1])[0, 1], -0.99, 0.99)
    return float(np.clip(len(x) * (1 - r1) / (1 + r1), 3, len(x)))


def partial_corr(y, x, z):
    ok = np.isfinite(y) & np.isfinite(x) & np.isfinite(z)
    if ok.sum() < 30:
        return np.nan, np.nan, int(ok.sum())
    y, x, z = y[ok], x[ok], z[ok]
    Z = np.column_stack([np.ones_like(z), z])
    ry = y - Z @ np.linalg.lstsq(Z, y, rcond=None)[0]
    rx = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
    r = float(np.corrcoef(ry, rx)[0, 1])
    ne = n_eff(ry)
    t = r * np.sqrt(max(ne - 3, 1) / max(1e-12, 1 - r ** 2))
    return r, float(2 * stats.t.sf(abs(t), df=max(ne - 3, 1))), int(ok.sum())


def ols(y, X, names):
    ok = np.isfinite(y) & np.isfinite(X).all(axis=1)
    y, X = y[ok], X[ok]
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ beta
    ne = n_eff(resid)
    dof = max(ne - A.shape[1], 1)
    s2 = (resid ** 2).sum() / max(len(y) - A.shape[1], 1)
    cov = s2 * np.linalg.inv(A.T @ A) * (len(y) / ne)
    se = np.sqrt(np.diag(cov))
    out = {"n": int(ok.sum()), "n_eff": ne, "resid_std": float(resid.std())}
    for i, nm in enumerate(["const"] + names):
        out[f"b_{nm}"] = float(beta[i])
        out[f"se_{nm}"] = float(se[i])
        out[f"t_{nm}"] = float(beta[i] / se[i]) if se[i] else np.nan
        out[f"p_{nm}"] = float(2 * stats.t.sf(abs(beta[i] / se[i]), df=dof)) if se[i] else np.nan
    return out


def analyse(name, tws, cu, ppt, area_km2, irr_frac, irr_crop_frac, cu_clim=None):
    """One footprint. tws/cu/ppt are monthly Series in mm."""
    dsdt = gap_aware_dsdt(tws)
    idx = dsdt.index.intersection(cu.index).intersection(ppt.index)
    d, c, p = dsdt.loc[idx], cu.loc[idx], ppt.loc[idx]
    dd, cc, pp = deseason(d), deseason(c), deseason(p)

    ok = np.isfinite(dd) & np.isfinite(cc)
    raw = float(np.corrcoef(d[ok], -c[ok])[0, 1])
    r_ds = float(np.corrcoef(dd[ok], -cc[ok])[0, 1])
    okp = ok & np.isfinite(pp)
    r_dp = float(np.corrcoef(dd[okp], pp[okp])[0, 1])
    r_pc = float(np.corrcoef(pp[okp], cc[okp])[0, 1])
    pr, pp_val, npair = partial_corr(dd.to_numpy(), -cc.to_numpy(), pp.to_numpy())

    reg = ols(dd.to_numpy(), np.column_stack([pp.to_numpy(), cc.to_numpy()]),
              ["P", "CU"])

    nf = noise_floor(tws)
    dsdt_noise = nf / np.sqrt(2.0)
    snr_noise = float(cc[ok].std() / dsdt_noise)
    snr_meas = float(cc[ok].std() / dd[ok].std())
    snr_resid = float(cc[ok].std() / reg["resid_std"])

    row = {
        "footprint": name, "area_km2": area_km2,
        "irr_frac_pct": irr_frac, "irr_crop_frac_pct": irr_crop_frac,
        "n_months": int(ok.sum()),
        "cu_mm_yr": float(c[ok].groupby(c[ok].index.year).sum().mean()),
        "cu_ds_std_mm": float(cc[ok].std()),
        "dsdt_ds_std_mm": float(dd[ok].std()),
        "tws_noise_floor_mm": nf, "dsdt_noise_mm": dsdt_noise,
        "snr_vs_noisefloor": snr_noise, "snr_vs_dsdt_std": snr_meas,
        "snr_vs_residual": snr_resid,
        "r_raw": raw, "r_deseason": r_ds,
        "r_dsdt_P": r_dp, "r_P_CU": r_pc,
        "induced_via_P": float(r_dp * -r_pc),
        "partial_r": pr, "partial_p": pp_val,
        "n_eff_resid": reg["n_eff"],
        "b_P": reg["b_P"], "se_P": reg["se_P"],
        "b_CU": reg["b_CU"], "se_CU": reg["se_CU"], "p_CU": reg["p_CU"],
        "months_for_2sigma": float((2.0 / snr_noise) ** 2),
    }
    if cu_clim is not None:
        cl = deseason(cu_clim.loc[idx])
        okc = np.isfinite(dd) & np.isfinite(cl)
        row["cu_clim_ds_std_mm"] = float(cl[okc].std())
        prc, ppc, _ = partial_corr(dd.to_numpy(), -cl.to_numpy(), pp.to_numpy())
        row["partial_r_climweights"] = prc
        row["partial_p_climweights"] = ppc
    return row, pd.DataFrame({"dsdt": d, "dsdt_ds": dd, "cu": c, "cu_ds": cc,
                              "ppt": p, "ppt_ds": pp})


def main():
    geo = pd.read_csv(OUT / "mascon_geometry.csv")
    cov = pd.read_csv(OUT / "mascon_coverage.csv").set_index("mascon_id")
    tws = pd.read_parquet(OUT / "grace_gsfc_mascon_monthly.parquet")
    tws.columns = [int(c) for c in tws.columns]
    mon = pd.read_parquet(OUT / "cu_monthly_mascon.parquet")
    mon["time"] = pd.to_datetime(mon["time"])

    cu_w = mon.pivot_table(index="time", columns="mascon", values="cu_mm")
    cuc_w = mon.pivot_table(index="time", columns="mascon", values="cu_clim_mm")
    ppt_w = mon.pivot_table(index="time", columns="mascon", values="ppt_mm")

    area = geo["area_km2"].to_numpy()
    mid = geo["mascon_id"].to_numpy()

    def agg(ks, wide):
        ks = [k for k in ks if k in wide.columns]
        return pd.Series(np.average(wide[ks].to_numpy(), axis=1,
                                    weights=area[ks]), index=wide.index)

    def build(ks, label):
        ks = sorted(ks)
        a = float(area[ks].sum())
        irr = float((cov["irr_frac_pct"].reindex(mid[ks]).to_numpy() * area[ks]).sum() / a)
        irrc = float((cov["irr_crop_frac_pct"].reindex(mid[ks]).to_numpy() * area[ks]).sum() / a)
        return dict(name=label, ks=ks, area=a, irr=irr, irrc=irrc)

    best_k = int(geo.index[geo["mascon_id"] == 1850][0])
    core_ids = cov[cov["irr_frac_pct"] >= 10].index.tolist()
    core_ks = [int(k) for k in geo.index[geo["mascon_id"].isin(core_ids)]]

    # 300 km footprint: mascons whose centre lies within 150 km of mascon 1850.
    d = haversine(geo.loc[best_k, "lat_center"], geo.loc[best_k, "lon_180"],
                  geo["lat_center"].to_numpy(), geo["lon_180"].to_numpy())
    ks300 = [int(k) for k in np.where(d <= 150)[0]]

    footprints = [
        build([best_k], "best native mascon (1850, Tulare)"),
        build(ks300, "300 km footprint around 1850"),
        build(core_ks, "irrigated core (8 mascons >=10% irr)"),
        build(list(range(len(geo))), "all 40 land mascons"),
    ]

    rows, series = [], {}
    for f in footprints:
        r, s = analyse(f["name"], agg(f["ks"], tws), agg(f["ks"], cu_w),
                       agg(f["ks"], ppt_w), f["area"], f["irr"], f["irrc"],
                       cu_clim=agg(f["ks"], cuc_w))
        rows.append(r)
        series[f["name"]] = s
        print(f"\n=== {f['name']} ===")
        print(f"  area {f['area']:,.0f} km2   irrigated {f['irr']:.2f}% "
              f"(cropped {f['irrc']:.2f}%)   n={r['n_months']}")
        print(f"  CU {r['cu_mm_yr']:.1f} mm/yr   CU' std {r['cu_ds_std_mm']:.2f} mm   "
              f"dS/dt noise {r['dsdt_noise_mm']:.2f} mm/month   SNR {r['snr_vs_noisefloor']:.3f}")
        print(f"  r_raw {r['r_raw']:+.3f}   r_deseason {r['r_deseason']:+.3f}   "
              f"induced via P {r['induced_via_P']:+.3f}   "
              f"partial r {r['partial_r']:+.3f} (p={r['partial_p']:.3f})")
        print(f"  b_P {r['b_P']:+.3f} +/- {r['se_P']:.3f}    "
              f"b_CU {r['b_CU']:+.3f} +/- {r['se_CU']:.3f}  (expect -1)")

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "flux_results_footprints.csv", index=False)
    for k, v in series.items():
        v.to_parquet(SIG / f"flux_{k.split()[0].lower()}.parquet")
    pd.concat({k: v for k, v in series.items()}, names=["footprint"]).to_parquet(
        SIG / "flux_series.parquet")

    # ------------------------------------------------ per-mascon (40 of them)
    per = []
    for k in range(len(geo)):
        if k not in cu_w.columns:
            continue
        m = int(mid[k])
        r, _ = analyse(f"mascon {m}", tws[k], cu_w[k], ppt_w[k],
                       float(area[k]),
                       float(cov.loc[m, "irr_frac_pct"]),
                       float(cov.loc[m, "irr_crop_frac_pct"]))
        r["mascon_id"] = m
        r["lat"] = float(geo.loc[k, "lat_center"])
        r["lon"] = float(geo.loc[k, "lon_180"])
        per.append(r)
    perdf = pd.DataFrame(per).sort_values("irr_frac_pct", ascending=False)
    perdf.to_csv(OUT / "flux_results_per_mascon.csv", index=False)

    print("\n=== per-mascon, top 10 by irrigated fraction ===")
    print(perdf.head(10)[["mascon_id", "lat", "lon", "irr_frac_pct", "cu_mm_yr",
                          "cu_ds_std_mm", "snr_vs_noisefloor", "partial_r",
                          "partial_p", "b_CU", "se_CU"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.3f}"))

    summary = {
        "footprints": rows,
        "n_mascons_partial_p_lt_05": int((perdf["partial_p"] < 0.05).sum()),
        "n_mascons_partial_r_positive": int((perdf["partial_r"] > 0).sum()),
        "n_mascons": int(len(perdf)),
        "spatial_effective_dof": 1.20,
        "note_spatial_dof": ("40 mascons carry 1.20 effective spatial degrees of "
                             "freedom (measured in the decorrelation run), so the "
                             "40 per-mascon tests are ~1 independent test, not 40. "
                             "Counts of 'significant' mascons must be read that way."),
        "oregon": {"cu_ds_std_mm": 0.43, "dsdt_noise_mm": 10.46,
                   "snr_300km": 0.041, "snr_best_mascon": 0.150,
                   "partial_r_300km": -0.087, "b_CU": 3.112, "se_CU": 3.550},
    }
    (INV / "flux_comparison.json").write_text(json.dumps(summary, indent=2, default=float))
    print("\nwrote flux_results_footprints.csv, flux_results_per_mascon.csv")


if __name__ == "__main__":
    main()
