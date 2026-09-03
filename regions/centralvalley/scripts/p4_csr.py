"""Phase 4b - repeat the flux comparison with CSR RL06.3, an independent solution.

CSR trap, handled: the netCDF time attribute is spelled `Units` with a capital U,
so xarray's CF decoder skips it and every timestamp collapses to 1970. The file
is opened with decode_times=False and the axis is rebuilt from
"days since 2002-01-01".

CSR is a 0.25 deg gridded product, not mascon-shaped, so it is sampled onto the
SAME GSFC mascon boxes to keep the two footprints identical. Also adds an
annual-scale test: GRACE resolves a multi-year Central Valley depletion easily,
so the question of whether year-to-year consumptive-use anomalies track
year-to-year storage change is worth asking separately from the monthly one.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, r"E:\Water\_shared")
from p4_flux import analyse, gap_aware_dsdt, deseason, n_eff, partial_corr
from grace_region import haversine

CSR = Path(r"E:\Water\Saudi\raw\csr_rl0603_mascons.nc")
OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")


def csr_mascon_series(geo):
    ds = xr.open_dataset(CSR, decode_times=False)
    tvar = ds["time"]
    print("CSR time attrs:", dict(tvar.attrs))
    times = pd.Timestamp("2002-01-01") + pd.to_timedelta(tvar.values, unit="D")
    lat = ds["lat"].values
    lon180 = ((ds["lon"].values + 180) % 360) - 180
    lwe = ds["lwe_thickness"].values * 10.0        # cm -> mm
    LON, LAT = np.meshgrid(lon180, lat)
    flon, flat_ = LON.ravel(), LAT.ravel()
    flat_lwe = lwe.reshape(len(times), -1)
    cols = {}
    for k, r in geo.iterrows():
        hit = np.where((flon >= r["lon_min"]) & (flon < r["lon_max"])
                       & (flat_ >= r["lat_min"]) & (flat_ < r["lat_max"]))[0]
        if len(hit) == 0:
            continue
        w = np.cos(np.radians(flat_[hit]))
        v = flat_lwe[:, hit]
        good = np.isfinite(v).all(axis=0)
        if good.sum() == 0:
            continue
        cols[k] = (v[:, good] * w[good]).sum(axis=1) / w[good].sum()
    df = pd.DataFrame(cols, index=pd.DatetimeIndex(times))
    return df.groupby(df.index.to_period("M").to_timestamp()).mean()


def main():
    geo = pd.read_csv(OUT / "mascon_geometry.csv")
    cov = pd.read_csv(OUT / "mascon_coverage.csv").set_index("mascon_id")
    gsfc = pd.read_parquet(OUT / "grace_gsfc_mascon_monthly.parquet")
    gsfc.columns = [int(c) for c in gsfc.columns]
    mon = pd.read_parquet(OUT / "cu_monthly_mascon.parquet")
    mon["time"] = pd.to_datetime(mon["time"])
    cu_w = mon.pivot_table(index="time", columns="mascon", values="cu_mm")
    ppt_w = mon.pivot_table(index="time", columns="mascon", values="ppt_mm")

    csr = csr_mascon_series(geo)
    csr.to_parquet(OUT / "grace_csr_mascon_monthly.parquet")
    print(f"CSR sampled onto {csr.shape[1]} mascon boxes, "
          f"{csr.index.min():%Y-%m}..{csr.index.max():%Y-%m}")

    area = geo["area_km2"].to_numpy()
    mid = geo["mascon_id"].to_numpy()

    def agg(ks, wide):
        ks = [k for k in ks if k in wide.columns]
        return pd.Series(np.average(wide[ks].to_numpy(), axis=1,
                                    weights=area[ks]), index=wide.index)

    best_k = int(geo.index[geo["mascon_id"] == 1850][0])
    core_ids = cov[cov["irr_frac_pct"] >= 10].index.tolist()
    core_ks = [int(k) for k in geo.index[geo["mascon_id"].isin(core_ids)]]
    d = haversine(geo.loc[best_k, "lat_center"], geo.loc[best_k, "lon_180"],
                  geo["lat_center"].to_numpy(), geo["lon_180"].to_numpy())
    ks300 = [int(k) for k in np.where(d <= 150)[0]]

    fps = [("best native mascon (1850)", [best_k]),
           ("300 km footprint", ks300),
           ("irrigated core", core_ks),
           ("all 40 mascons", list(range(len(geo))))]

    rows = []
    for name, ks in fps:
        a = float(area[ks].sum())
        irr = float((cov["irr_frac_pct"].reindex(mid[ks]).to_numpy() * area[ks]).sum() / a)
        irrc = float((cov["irr_crop_frac_pct"].reindex(mid[ks]).to_numpy() * area[ks]).sum() / a)
        for label, tws in [("GSFC", agg(ks, gsfc)), ("CSR", agg(ks, csr))]:
            r, _ = analyse(f"{name} [{label}]", tws, agg(ks, cu_w), agg(ks, ppt_w),
                           a, irr, irrc)
            r["solution"] = label
            r["fp"] = name
            rows.append(r)

        # agreement between the two solutions on this footprint
        g, c = deseason(agg(ks, gsfc)), deseason(agg(ks, csr))
        j = pd.concat([g.rename("g"), c.rename("c")], axis=1).dropna()
        print(f"\n{name}: corr(GSFC', CSR') = {j.corr().iloc[0,1]:+.3f} on {len(j)} months")

    res = pd.DataFrame(rows)
    res.to_csv(OUT / "flux_results_gsfc_vs_csr.csv", index=False)
    piv = res.pivot(index="fp", columns="solution",
                    values=["cu_ds_std_mm", "dsdt_noise_mm", "snr_vs_noisefloor",
                            "partial_r", "partial_p", "b_CU", "se_CU"])
    print("\n=== GSFC vs CSR, same footprints, same CU and P ===")
    print(piv.to_string(float_format=lambda v: f"{v:,.3f}"))

    # ------------------------------------------------------- annual-scale test
    print("\n=== annual scale: does the water-year CU anomaly track dS/dt? ===")
    ann_rows = []
    for name, ks in fps:
        tws = agg(ks, gsfc)
        cu = agg(ks, cu_w)
        pp = agg(ks, ppt_w)
        wy = pd.Index([t.year + (t.month >= 10) for t in tws.index])
        # annual dS = last-minus-first of the water year, only when both exist
        g = tws.groupby(wy)
        dS = g.last() - g.first()
        nmon = g.count()
        dS = dS.where(nmon >= 10)
        cuA = cu.groupby(pd.Index([t.year + (t.month >= 10) for t in cu.index])).sum()
        ppA = pp.groupby(pd.Index([t.year + (t.month >= 10) for t in pp.index])).sum()
        j = pd.concat([dS.rename("dS"), cuA.rename("cu"), ppA.rename("p")],
                      axis=1).dropna()
        if len(j) < 8:
            continue
        r_raw = float(np.corrcoef(j["dS"], -j["cu"])[0, 1])
        # partial_corr() demands >=30 points, which annual data never has, so
        # the ordinary small-sample partial correlation is used here instead.
        Zc = np.column_stack([np.ones(len(j)), j["p"].to_numpy()])
        ry = j["dS"].to_numpy() - Zc @ np.linalg.lstsq(Zc, j["dS"].to_numpy(), rcond=None)[0]
        rx = -j["cu"].to_numpy() - Zc @ np.linalg.lstsq(Zc, -j["cu"].to_numpy(), rcond=None)[0]
        pr = float(np.corrcoef(ry, rx)[0, 1])
        tt = pr * np.sqrt((len(j) - 3) / max(1e-12, 1 - pr ** 2))
        pv = float(2 * stats.t.sf(abs(tt), df=len(j) - 3))
        A = np.column_stack([np.ones(len(j)), j["p"], j["cu"]])
        beta, *_ = np.linalg.lstsq(A, j["dS"].to_numpy(), rcond=None)
        resid = j["dS"].to_numpy() - A @ beta
        s2 = (resid ** 2).sum() / max(len(j) - 3, 1)
        se = np.sqrt(np.diag(s2 * np.linalg.inv(A.T @ A)))
        ann_rows.append({"footprint": name, "n_years": int(len(j)),
                         "r_raw": r_raw, "partial_r": pr, "partial_p": pv,
                         "b_P": float(beta[1]), "se_P": float(se[1]),
                         "b_CU": float(beta[2]), "se_CU": float(se[2])})
        print(f"  {name:28s} n={len(j):2d}  r_raw {r_raw:+.3f}  "
              f"partial r {pr:+.3f} (p={pv:.3f})  "
              f"b_P {beta[1]:+.3f}+/-{se[1]:.3f}  b_CU {beta[2]:+.3f}+/-{se[2]:.3f}")
    pd.DataFrame(ann_rows).to_csv(OUT / "flux_results_annual.csv", index=False)

    (INV / "csr_crosscheck.json").write_text(json.dumps(
        {"footprints": rows, "annual": ann_rows}, indent=2, default=float))


if __name__ == "__main__":
    main()
