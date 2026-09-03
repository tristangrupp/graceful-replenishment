"""Redo the Oregon flux comparison on native GSFC mascons.

Everything previous ran on the interpolated half-degree netCDF, whose cells
are not solve elements. This works on the mascons the solution actually
estimates, read from the native HDF5, and starts from the best-covered
mascon at 14.5% irrigated rather than the 3.3% of a 300 km footprint.

Also quantifies how far a mascon's signal is shared with its neighbours,
which is what decides whether 58 mascons carry 58 measurements or far fewer.
"""

import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

BASE = Path(r"E:\Water\Oregan\analysis")
H5 = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
OUT = BASE / "processed"

ACRE_FT_TO_M3 = 1233.4818
CM_TO_MM = 10.0
OR_BOX = dict(lat=(41.8, 46.4), lon=(-124.7, -116.4))
GAP = (pd.Timestamp("2017-07-01"), pd.Timestamp("2018-05-31"))


# ---------------------------------------------------------------- geometry
LAND = 80.0   # GSFC location code; 90.0 is ocean


def load_region(land_only=True):
    with h5py.File(H5, "r") as f:
        m = f["mascon"]
        geo = pd.DataFrame({
            "lat_center": np.ravel(m["lat_center"][:]),
            "lon_center": np.ravel(m["lon_center"][:]),
            "lat_span": np.ravel(m["lat_span"][:]),
            "lon_span": np.ravel(m["lon_span"][:]),
            "area_km2": np.ravel(m["area_km2"][:]),
            "location": np.ravel(m["location"][:]),
        })
        geo["mascon_id"] = np.arange(len(geo))
        geo["lon_180"] = ((geo["lon_center"] + 180) % 360) - 180

        lat0, lat1 = OR_BOX["lat"]
        lon0, lon1 = OR_BOX["lon"]
        pad = 1.5
        keep = (geo["lat_center"].between(lat0 - pad, lat1 + pad)
                & geo["lon_180"].between(lon0 - pad, lon1 + pad))
        if land_only:
            # Ocean mascons carry ocean-mass signal that is not terrestrial
            # storage. Leaving them in put r as low as 0.06 between mascons
            # 110 km apart, which reads as fast decorrelation when it is
            # really a land pixel sitting beside a sea pixel.
            keep &= geo["location"] == LAND
        sel = geo[keep].copy()

        cmwe = f["solution/cmwe"][sel["mascon_id"].to_numpy(), :]
        ymd = f["time/yyyy_doy_yrplot_middle"][:]

    years = ymd[0].astype(int)
    doys = ymd[1].astype(int)
    times = pd.to_datetime([f"{y}-01-01" for y in years]) + pd.to_timedelta(doys - 1, unit="D")

    sel = sel.reset_index(drop=True)
    sel["lat_min"] = sel["lat_center"] - sel["lat_span"] / 2
    sel["lat_max"] = sel["lat_center"] + sel["lat_span"] / 2
    sel["lon_min"] = sel["lon_180"] - sel["lon_span"] / 2
    sel["lon_max"] = sel["lon_180"] + sel["lon_span"] / 2
    return sel, cmwe * CM_TO_MM, pd.DatetimeIndex(times)


def to_monthly(values, times):
    """One column per calendar month, duplicates averaged, gaps left absent."""
    df = pd.DataFrame(values.T, index=times)
    months = df.index.to_period("M").to_timestamp()
    return df.groupby(months).mean()


def assign(lon, lat, mascons):
    idx = np.full(len(lon), -1, dtype=int)
    for k, r in mascons.iterrows():
        hit = ((lon >= r["lon_min"]) & (lon < r["lon_max"])
               & (lat >= r["lat_min"]) & (lat < r["lat_max"]) & (idx < 0))
        idx[hit] = k
    return idx


# ------------------------------------------------------------- statistics
def deseasonalise(df):
    return df - df.groupby(df.index.month).transform("mean")


def gap_aware_dsdt(df):
    """Centred difference in mm/month, NaN wherever a neighbour month is absent."""
    full = df.reindex(pd.date_range(df.index.min(), df.index.max(), freq="MS"))
    fwd, back = full.shift(-1), full.shift(1)
    out = (fwd - back) / 2.0
    out[fwd.isna() | back.isna()] = np.nan
    return out


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def partial_corr(y, x, z):
    ok = np.isfinite(y) & np.isfinite(x) & np.isfinite(z)
    if ok.sum() < 30:
        return np.nan, np.nan, int(ok.sum())
    y, x, z = y[ok], x[ok], z[ok]
    zz = np.column_stack([np.ones_like(z), z])
    ry = y - zz @ np.linalg.lstsq(zz, y, rcond=None)[0]
    rx = x - zz @ np.linalg.lstsq(zz, x, rcond=None)[0]
    r = np.corrcoef(ry, rx)[0, 1]
    n = ok.sum()
    from scipy import stats
    t = r * np.sqrt((n - 3) / max(1e-12, 1 - r ** 2))
    return r, 2 * stats.t.sf(abs(t), df=n - 3), int(n)


def main():
    mascons, tws_mm, times = load_region()
    print(f"{len(mascons)} native mascons, {len(times)} solutions")

    monthly = to_monthly(tws_mm, times)
    monthly.columns = mascons.index
    print(f"monthly axis {monthly.index.min():%Y-%m} .. {monthly.index.max():%Y-%m}, "
          f"{len(monthly)} months")

    # ---- field data folded into mascons ---------------------------------
    cells = pd.read_parquet(OUT / "cell_monthly.parquet")
    cells["time"] = pd.to_datetime(cells["time"])
    rank = pd.read_parquet(OUT / "cell_irrigation_ranking.parquet")
    lut = rank.set_index(["grid_i", "grid_j"])[["lon_c", "lat_c"]]
    cells = cells.join(lut, on=["grid_i", "grid_j"])
    cells = cells[cells["lon_c"].notna()]
    cells["mascon"] = assign(cells["lon_c"].to_numpy(), cells["lat_c"].to_numpy(), mascons)
    cells = cells[cells["mascon"] >= 0]

    irr = cells[cells["is_irrigated"]]
    field = (irr.groupby(["mascon", "time"])[["eta_af", "cuadj_af"]].sum()
             .join(cells.groupby(["mascon", "time"])[["ppt_af"]].sum()))
    field = field.reset_index()

    # acre-feet over the mascon -> mm depth over the whole mascon
    area_m2 = mascons["area_km2"].to_numpy() * 1e6
    field["area_m2"] = area_m2[field["mascon"].to_numpy()]
    for col, name in [("eta_af", "eta_mm"), ("cuadj_af", "cu_mm"), ("ppt_af", "ppt_mm")]:
        field[name] = field[col] * ACRE_FT_TO_M3 / field["area_m2"] * 1000.0

    # ---- decorrelation among native mascons -----------------------------
    ds = deseasonalise(monthly)
    valid = ds.columns[ds.notna().sum() > 100]
    corr = ds[valid].corr()
    lat = mascons.loc[valid, "lat_center"].to_numpy()
    lon = mascons.loc[valid, "lon_180"].to_numpy()
    n = len(valid)
    ii, jj = np.triu_indices(n, k=1)
    dist = haversine(lat[ii], lon[ii], lat[jj], lon[jj])
    rvals = corr.to_numpy()[ii, jj]
    pairs = pd.DataFrame({"dist_km": dist, "r": rvals,
                          "a": np.array(valid)[ii], "b": np.array(valid)[jj]})
    pairs.to_parquet(OUT / "native_mascon_pair_correlations.parquet")

    bins = np.arange(0, 1000, 50)
    binned = (pairs.assign(bin=pd.cut(pairs["dist_km"], bins))
              .groupby("bin", observed=True)["r"].agg(["mean", "std", "count"]).reset_index())
    binned["dist_mid"] = [iv.mid for iv in binned["bin"]]
    binned.drop(columns="bin").to_csv(OUT / "native_mascon_decorrelation.csv", index=False)

    adjacent = pairs[pairs["dist_km"] < 130]["r"]
    filled = ds[valid].dropna()
    eof_frac = np.nan
    if len(filled) > 24:
        u, s, vt = np.linalg.svd(filled.to_numpy() - filled.to_numpy().mean(0), full_matrices=False)
        var = s ** 2 / (s ** 2).sum()
        eof_frac = float(var[0])
        eff_dof = float(1.0 / (var ** 2).sum())
    else:
        eff_dof = np.nan

    # ---- per-mascon flux regression -------------------------------------
    dsdt = gap_aware_dsdt(monthly)
    cov = pd.read_csv(OUT / "native_mascon_coverage.csv")
    cov_by_id = cov.set_index("mascon_id")

    rows = []
    for k in valid:
        mid = int(mascons.loc[k, "mascon_id"])
        fk = field[field["mascon"] == k].set_index("time").sort_index()
        if fk.empty:
            continue
        idx = dsdt.index.intersection(fk.index)
        if len(idx) < 40:
            continue
        d = deseasonalise(dsdt.loc[idx, [k]]).iloc[:, 0]
        cu = deseasonalise(fk.loc[idx, "cu_mm"])
        pp = deseasonalise(fk.loc[idx, "ppt_mm"])
        r_pc, p_pc, nobs = partial_corr(d.to_numpy(), -cu.to_numpy(), pp.to_numpy())
        raw = np.corrcoef(*[v[np.isfinite(d) & np.isfinite(cu)]
                            for v in (d.to_numpy(), -cu.to_numpy())])[0, 1]
        info = cov_by_id.loc[mid] if mid in cov_by_id.index else None
        rows.append({
            "mascon_id": mid, "lat": mascons.loc[k, "lat_center"],
            "lon": mascons.loc[k, "lon_180"],
            "irr_frac_pct": float(info["irr_frac_pct"]) if info is not None else np.nan,
            "all_field_frac_pct": float(info["all_field_frac_pct"]) if info is not None else np.nan,
            "crosses_border": bool(info["crosses_border"]) if info is not None else False,
            "cu_mm_yr": float(fk["cu_mm"].groupby(fk.index.year).sum().mean()),
            "cu_ds_std": float(cu.std()), "dsdt_ds_std": float(d.std()),
            "snr": float(cu.std() / d.std()) if d.std() else np.nan,
            "r_raw": float(raw), "partial_r": r_pc, "partial_p": p_pc, "n_months": nobs,
        })

    res = pd.DataFrame(rows).sort_values("irr_frac_pct", ascending=False)
    res.to_csv(OUT / "native_mascon_flux_results.csv", index=False)

    monthly.to_parquet(OUT / "native_mascon_tws_monthly.parquet")
    ds.to_parquet(OUT / "native_mascon_tws_deseasonalised.parquet")

    summary = {
        "n_mascons": int(len(mascons)),
        "n_analysed": int(len(res)),
        "adjacent_pair_r_mean": float(adjacent.mean()),
        "adjacent_pair_r_min": float(adjacent.min()),
        "n_adjacent_pairs": int(len(adjacent)),
        "first_eof_variance_frac": eof_frac,
        "effective_dof": eff_dof,
        "best_irr_frac_pct": float(res["irr_frac_pct"].max()),
        "best_snr": float(res["snr"].max()),
        "median_snr": float(res["snr"].median()),
        "n_partial_significant_p05": int((res["partial_p"] < 0.05).sum()),
        "n_partial_negative": int((res["partial_r"] < 0).sum()),
    }
    (OUT / "native_mascon_flux_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("\nTop mascons by irrigated coverage")
    print(res.head(8)[["lat", "lon", "irr_frac_pct", "cu_mm_yr", "snr",
                       "r_raw", "partial_r", "partial_p"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.3f}"))


if __name__ == "__main__":
    main()
