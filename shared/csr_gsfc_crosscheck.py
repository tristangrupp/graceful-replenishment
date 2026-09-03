"""Cross-check the Arabian Peninsula result against CSR RL06.3.

Every number in the Saudi run came from GSFC, and HESS 26, 5757 (2022)
explicitly rejected GSFC for the Saq-Ram domain, saying its solution implied
about 1.1 mm/yr of evaporation from a 150 m-deep water table where theory
allows roughly 0.07. They attributed the disagreement to differences in raw
GRACE data treatment and reported the three processing centres diverging
increasingly after 2012.

This samples CSR onto each GSFC peninsula mascon footprint and refits the
same trend model, so the two are compared on identical geometry, identical
months and identical statistics. It tests the specific claim about post-2012
divergence rather than only the headline number.
"""

import json
import sys
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, r"C:\Users\grupp\dark-water-extract\dark-water-main\src")
sys.path.insert(0, r"E:\Water\_shared")

from dark_water.depletion_watchlist.depletion import trend as trend_mod  # noqa: E402
from grace_region import H5, to_monthly  # noqa: E402

SAUDI = Path(r"E:\Water\Saudi")
CSR = SAUDI / "raw" / "csr_rl0603_mascons.nc"
OUT = SAUDI / "crosscheck"
SPLIT_YEAR = 2012          # the year HESS reports the centres starting to diverge


def gsfc_peninsula():
    flags = pd.read_csv(SAUDI / "trends" / "all_mascons_flags.csv")
    ids = flags["mascon_id"].to_numpy()
    with h5py.File(H5, "r") as f:
        m = f["mascon"]
        geo = pd.DataFrame({
            "lat_center": np.ravel(m["lat_center"][:])[ids],
            "lon_center": np.ravel(m["lon_center"][:])[ids],
            "lat_span": np.ravel(m["lat_span"][:])[ids],
            "lon_span": np.ravel(m["lon_span"][:])[ids],
            "area_km2": np.ravel(m["area_km2"][:])[ids],
        }, index=ids)
        cmwe = f["solution/cmwe"][ids, :] * 10.0          # cm -> mm
        ymd = f["time/yyyy_doy_yrplot_middle"][:]
    times = (pd.to_datetime([f"{int(y)}-01-01" for y in ymd[0]])
             + pd.to_timedelta(ymd[1].astype(int) - 1, unit="D"))
    geo["lon_180"] = ((geo["lon_center"] + 180) % 360) - 180
    monthly = to_monthly(cmwe, pd.DatetimeIndex(times))
    monthly.columns = ids
    return flags, geo, monthly


def csr_time(ds):
    """CSR spells the time unit attribute 'Units', so CF decoding skips it.

    Left undecoded the axis is a float count of days and every timestamp
    collapses to 1970, which silently reduces the whole record to one month.
    """
    t = ds["time"]
    unit = t.attrs.get("units") or t.attrs.get("Units", "")
    epoch = unit.split("since")[-1].strip().replace("Z", "") if "since" in unit else "2002-01-01"
    return pd.to_datetime(epoch) + pd.to_timedelta(t.values.astype("float64"), unit="D")


def csr_on_footprints(geo):
    """Area-weighted CSR mean inside each GSFC mascon box, in mm."""
    ds = xr.open_dataset(CSR, decode_times=False)
    da = (ds["lwe_thickness"] * 10.0).assign_coords(time=csr_time(ds))   # cm -> mm
    lat = da["lat"].values
    lon = da["lon"].values                                # 0-360
    w = np.cos(np.radians(lat))

    out = {}
    for mid, r in geo.iterrows():
        lo = (r["lon_center"] - r["lon_span"] / 2) % 360
        hi = (r["lon_center"] + r["lon_span"] / 2) % 360
        latm = (lat >= r["lat_center"] - r["lat_span"] / 2) & (lat < r["lat_center"] + r["lat_span"] / 2)
        lonm = (lon >= lo) & (lon < hi) if lo < hi else ((lon >= lo) | (lon < hi))
        if not latm.any() or not lonm.any():
            continue
        block = da.isel(lat=np.where(latm)[0], lon=np.where(lonm)[0])
        ww = xr.DataArray(w[latm], dims="lat", coords={"lat": block["lat"]})
        out[mid] = block.weighted(ww).mean(dim=("lat", "lon")).to_series()
    ds.close()
    df = pd.DataFrame(out)
    df.index = pd.to_datetime(df.index)
    return to_monthly(df.to_numpy().T, df.index).set_axis(df.columns, axis=1)


def fit(series: pd.Series):
    s = series.dropna()
    if len(s) < 60:
        return np.nan, np.nan
    da = xr.DataArray(s.to_numpy()[:, None], dims=("time", "x"),
                      coords={"time": s.index, "x": [0]})
    r = trend_mod.fit_trend(da)
    return float(r["trend"].values[0]) / 10.0, float(r["p_value"].values[0])   # mm/yr -> cm/yr


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    flags, geo, gsfc = gsfc_peninsula()
    print(f"{len(geo)} peninsula mascons; GSFC months {len(gsfc)}")

    csr = csr_on_footprints(geo)
    print(f"CSR sampled onto {csr.shape[1]} footprints, {len(csr)} months")

    common = gsfc.index.intersection(csr.index)
    cols = [c for c in gsfc.columns if c in csr.columns]
    gsfc, csr = gsfc.loc[common, cols], csr.loc[common, cols]
    print(f"common months {len(common)}: {common.min():%Y-%m} .. {common.max():%Y-%m}")

    area = geo.loc[cols, "area_km2"].to_numpy()
    wts = area / area.sum()
    reg = pd.DataFrame({
        "gsfc": (gsfc * wts).sum(axis=1, min_count=1),
        "csr": (csr * wts).sum(axis=1, min_count=1),
    })
    reg.to_csv(OUT / "peninsula_mean_series.csv")

    rows = []
    for c in cols:
        tg, pg = fit(gsfc[c])
        tc, pc = fit(csr[c])
        both = pd.concat([gsfc[c], csr[c]], axis=1).dropna()
        rows.append({
            "mascon_id": c,
            "lat": geo.loc[c, "lat_center"], "lon": geo.loc[c, "lon_180"],
            "gsfc_trend_cm_yr": tg, "csr_trend_cm_yr": tc,
            "diff_cm_yr": tc - tg,
            "gsfc_p": pg, "csr_p": pc,
            "r": float(both.corr().iloc[0, 1]) if len(both) > 30 else np.nan,
        })
    per = pd.DataFrame(rows)
    per.to_csv(OUT / "per_mascon_comparison.csv", index=False)

    early = reg[reg.index.year < SPLIT_YEAR]
    late = reg[reg.index.year >= SPLIT_YEAR]

    def pair_trend(df):
        return {k: fit(df[k])[0] for k in ("gsfc", "csr")}

    summary = {
        "n_mascons": len(cols),
        "n_common_months": int(len(common)),
        "regional_trend_cm_yr": pair_trend(reg),
        "regional_trend_pre_2012": pair_trend(early),
        "regional_trend_2012_on": pair_trend(late),
        "regional_series_r": float(reg.corr().iloc[0, 1]),
        "regional_series_r_pre_2012": float(early.corr().iloc[0, 1]),
        "regional_series_r_2012_on": float(late.corr().iloc[0, 1]),
        "per_mascon_trend_r": float(per[["gsfc_trend_cm_yr", "csr_trend_cm_yr"]].corr().iloc[0, 1]),
        "mean_trend_diff_cm_yr": float(per["diff_cm_yr"].mean()),
        "median_abs_trend_diff_cm_yr": float(per["diff_cm_yr"].abs().median()),
        "n_sign_disagreement": int(((per["gsfc_trend_cm_yr"] < 0)
                                    != (per["csr_trend_cm_yr"] < 0)).sum()),
        "median_per_mascon_series_r": float(per["r"].median()),
    }
    (OUT / "crosscheck_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
