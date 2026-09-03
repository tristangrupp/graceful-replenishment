"""Region-agnostic GRACE mascon decorrelation analysis.

Generalises the Oregon work so the same question can be asked anywhere:
given the mascons GSFC actually solves for, how much of a mascon's signal
already belongs to its neighbours, and how many independent measurements
does a region really contain?

Reads the native GSFC HDF5 rather than the interpolated half-degree netCDF.
The interpolated grid destroys mascon identity, so every cell looks unique
and a naive count badly overstates the number of measurements.

Ocean mascons are excluded by default. They carry ocean-mass signal that is
not terrestrial storage, and leaving them in makes a coastal region look far
less correlated than it is.
"""

import json
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

H5 = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
LAND = 80.0            # GSFC location code; 90.0 is ocean
CM_TO_MM = 10.0
PAD_DEG = 1.5


def load_region(lat_range, lon_range, land_only=True, pad=PAD_DEG):
    """Mascon geometry and TWS series (mm) for a lat/lon window."""
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

        keep = (geo["lat_center"].between(lat_range[0] - pad, lat_range[1] + pad)
                & geo["lon_180"].between(lon_range[0] - pad, lon_range[1] + pad))
        if land_only:
            keep &= geo["location"] == LAND
        sel = geo[keep].copy()
        if sel.empty:
            raise ValueError(f"No mascons in lat {lat_range} lon {lon_range}")

        cmwe = f["solution/cmwe"][sel["mascon_id"].to_numpy(), :]
        ymd = f["time/yyyy_doy_yrplot_middle"][:]

    times = (pd.to_datetime([f"{int(y)}-01-01" for y in ymd[0]])
             + pd.to_timedelta(ymd[1].astype(int) - 1, unit="D"))

    sel = sel.reset_index(drop=True)
    sel["lat_min"] = sel["lat_center"] - sel["lat_span"] / 2
    sel["lat_max"] = sel["lat_center"] + sel["lat_span"] / 2
    sel["lon_min"] = sel["lon_180"] - sel["lon_span"] / 2
    sel["lon_max"] = sel["lon_180"] + sel["lon_span"] / 2
    return sel, cmwe * CM_TO_MM, pd.DatetimeIndex(times)


def to_monthly(values, times):
    """One row per calendar month; the occasional duplicate solution averaged."""
    df = pd.DataFrame(values.T, index=times)
    return df.groupby(df.index.to_period("M").to_timestamp()).mean()


def deseasonalise(df):
    return df - df.groupby(df.index.month).transform("mean")


def haversine(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = np.radians(lat1), np.radians(lat2)
    dp, dl = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dp / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(dl / 2) ** 2
    return 2 * r * np.arcsin(np.sqrt(a))


def analyse(name, lat_range, lon_range, out_dir, adjacent_km=130):
    """Decorrelation and effective degrees of freedom for one region."""
    out_dir = Path(out_dir)
    (out_dir / "processed").mkdir(parents=True, exist_ok=True)

    mascons, tws, times = load_region(lat_range, lon_range)
    monthly = to_monthly(tws, times)
    monthly.columns = mascons.index
    ds = deseasonalise(monthly)

    usable = [c for c in ds.columns if ds[c].notna().sum() > 100]
    dsu = ds[usable]
    lat = mascons.loc[usable, "lat_center"].to_numpy()
    lon = mascons.loc[usable, "lon_180"].to_numpy()

    corr = dsu.corr().to_numpy()
    ii, jj = np.triu_indices(len(usable), k=1)
    pairs = pd.DataFrame({
        "dist_km": haversine(lat[ii], lon[ii], lat[jj], lon[jj]),
        "r": corr[ii, jj],
        "a": np.array(usable)[ii],
        "b": np.array(usable)[jj],
    })
    pairs.to_parquet(out_dir / "processed" / "pair_correlations.parquet")

    bins = np.arange(0, pairs["dist_km"].max() + 50, 50)
    binned = (pairs.assign(bin=pd.cut(pairs["dist_km"], bins))
              .groupby("bin", observed=True)["r"]
              .agg(["mean", "std", "count"]).reset_index())
    binned["dist_mid"] = [iv.mid for iv in binned["bin"]]
    binned = binned.drop(columns="bin")
    binned.to_csv(out_dir / "processed" / "decorrelation.csv", index=False)

    # Distance at which the binned mean first drops through a threshold.
    def crossing(level):
        below = binned[binned["mean"] < level]
        return float(below["dist_mid"].iloc[0]) if len(below) else np.nan

    filled = dsu.dropna()
    eof1 = eff_dof = np.nan
    if len(filled) > 24:
        x = filled.to_numpy()
        s = np.linalg.svd(x - x.mean(0), full_matrices=False)[1]
        var = s ** 2 / (s ** 2).sum()
        eof1, eff_dof = float(var[0]), float(1.0 / (var ** 2).sum())

    adj = pairs[pairs["dist_km"] < adjacent_km]["r"]
    summary = {
        "region": name,
        "lat_range": list(lat_range), "lon_range": list(lon_range),
        "n_land_mascons": int(len(mascons)),
        "n_usable": int(len(usable)),
        "median_mascon_area_km2": float(mascons["area_km2"].median()),
        "n_months": int(dsu.notna().any(axis=1).sum()),
        "adjacent_km": adjacent_km,
        "n_adjacent_pairs": int(len(adj)),
        "adjacent_r_mean": float(adj.mean()) if len(adj) else np.nan,
        "adjacent_r_min": float(adj.min()) if len(adj) else np.nan,
        "r07_km": crossing(0.7),
        "r05_km": crossing(0.5),
        "first_eof_variance_frac": eof1,
        "effective_dof": eff_dof,
        "mascons_per_effective_dof": float(len(usable) / eff_dof) if eff_dof else np.nan,
    }
    (out_dir / "processed" / "decorrelation_summary.json").write_text(json.dumps(summary, indent=2))

    monthly.to_parquet(out_dir / "processed" / "tws_monthly.parquet")
    ds.to_parquet(out_dir / "processed" / "tws_deseasonalised.parquet")
    mascons.to_csv(out_dir / "processed" / "mascon_geometry.csv", index=False)
    return summary, mascons, ds, pairs, binned
