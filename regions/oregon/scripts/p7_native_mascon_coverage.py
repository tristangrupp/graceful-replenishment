"""How much of a real GSFC mascon does Oregon farmland actually cover?

The Oregon run measured coverage on the interpolated half-degree netCDF grid
and on a 1-degree block approximation. Neither is a mascon. The native GSFC
solution stores true ~1-arc-degree equal-area mascons in its HDF5
distribution, which the Arabian Peninsula run downloaded and which is global,
so the honest question can be answered directly: assign Oregon fields to the
mascons the solution actually solves for, and see how high the coverage gets.

Two coverage numbers are reported per mascon:
  irrigated  -- land irrigated in a given year, the term that consumes water
  all fields -- every field boundary in the inventory, irrigated or not

The second is the ceiling. If even total farmland cannot fill a mascon, no
amount of irrigation-status accounting will.

Mascons clipped by the state line are flagged, because the field inventory
stops at the Oregon border while the mascon does not.
"""

import json
from pathlib import Path

import geopandas as gpd
import h5py
import numpy as np
import pandas as pd

BASE = Path(r"E:\Water\Oregan\analysis")
H5 = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
OUT = BASE / "processed"

ACRE_KM2 = 0.00404686
OR_BOX = dict(lat=(41.8, 46.4), lon=(-124.7, -116.4))


def load_mascon_geometry():
    """Mascon centres, spans and areas from the native GSFC HDF5."""
    with h5py.File(H5, "r") as f:
        loc = f["mascon"]
        geom = {
            "lat_center": np.ravel(loc["lat_center"][:]),
            "lon_center": np.ravel(loc["lon_center"][:]),
            "lat_span": np.ravel(loc["lat_span"][:]),
            "lon_span": np.ravel(loc["lon_span"][:]),
            "area_km2": np.ravel(loc["area_km2"][:]),
        }
    df = pd.DataFrame(geom)
    df["mascon_id"] = np.arange(len(df))
    df["lon_180"] = ((df["lon_center"] + 180) % 360) - 180
    return df


def select_region(mascons, pad=1.5):
    lat0, lat1 = OR_BOX["lat"]
    lon0, lon1 = OR_BOX["lon"]
    m = mascons[
        mascons["lat_center"].between(lat0 - pad, lat1 + pad)
        & mascons["lon_180"].between(lon0 - pad, lon1 + pad)
    ].copy()
    m["lat_min"] = m["lat_center"] - m["lat_span"] / 2
    m["lat_max"] = m["lat_center"] + m["lat_span"] / 2
    m["lon_min"] = m["lon_180"] - m["lon_span"] / 2
    m["lon_max"] = m["lon_180"] + m["lon_span"] / 2
    return m.reset_index(drop=True)


def assign(points_lon, points_lat, mascons):
    """Index of the containing mascon for each point, or -1."""
    idx = np.full(len(points_lon), -1, dtype=int)
    for k, r in mascons.iterrows():
        hit = (
            (points_lon >= r["lon_min"]) & (points_lon < r["lon_max"])
            & (points_lat >= r["lat_min"]) & (points_lat < r["lat_max"])
            & (idx < 0)
        )
        idx[hit] = k
    return idx


def main():
    mascons = select_region(load_mascon_geometry())
    print(f"{len(mascons)} native mascons over the Oregon region")
    print(f"mascon area: min {mascons['area_km2'].min():,.0f} "
          f"max {mascons['area_km2'].max():,.0f} km2")

    # All field boundaries, with their true areas.
    fields = pd.read_parquet(OUT / "field_centroids.parquet")
    fields["mascon"] = assign(fields["lon"].to_numpy(), fields["lat"].to_numpy(), mascons)

    all_fields = (
        fields[fields["mascon"] >= 0]
        .groupby("mascon")["acres_calc"].sum().rename("all_field_acres")
    )

    # Irrigated area per 0.5-degree cell, from the existing ranking, folded
    # into the mascon containing each cell centre. Irrigation status varies by
    # year, so this uses the run's own per-cell mean.
    cells = pd.read_parquet(OUT / "cell_irrigation_ranking.parquet")
    cells["mascon"] = assign(cells["lon_c"].to_numpy(), cells["lat_c"].to_numpy(), mascons)
    irr = (
        cells[cells["mascon"] >= 0]
        .groupby("mascon")
        .agg(irr_km2=("irr_km2", "sum"), cu_af_yr=("cu_af_yr", "sum"))
    )

    out = mascons.join(all_fields).join(irr)
    out["all_field_km2"] = out["all_field_acres"].fillna(0) * ACRE_KM2
    out["irr_km2"] = out["irr_km2"].fillna(0)
    out["cu_af_yr"] = out["cu_af_yr"].fillna(0)
    out["irr_frac_pct"] = 100 * out["irr_km2"] / out["area_km2"]
    out["all_field_frac_pct"] = 100 * out["all_field_km2"] / out["area_km2"]

    # A mascon is truncated if its box reaches past the Oregon border, so the
    # inventory cannot see all of its farmland.
    out["crosses_border"] = (
        (out["lat_max"] > OR_BOX["lat"][1]) | (out["lat_min"] < OR_BOX["lat"][0])
        | (out["lon_max"] > OR_BOX["lon"][1]) | (out["lon_min"] < OR_BOX["lon"][0])
    )

    out = out.sort_values("irr_frac_pct", ascending=False)
    cols = ["mascon_id", "lat_center", "lon_180", "area_km2", "irr_km2",
            "irr_frac_pct", "all_field_km2", "all_field_frac_pct",
            "cu_af_yr", "crosses_border"]
    out[cols].to_csv(OUT / "native_mascon_coverage.csv", index=False)

    top = out[out["irr_km2"] > 0].head(10)
    print("\nTop native mascons by irrigated fraction")
    print(top[["lat_center", "lon_180", "area_km2", "irr_frac_pct",
               "all_field_frac_pct", "crosses_border"]]
          .to_string(index=False, float_format=lambda v: f"{v:,.2f}"))

    covered = out[out["irr_km2"] > 0]
    summary = {
        "n_mascons_region": int(len(out)),
        "n_mascons_with_irrigation": int(len(covered)),
        "max_irrigated_frac_pct": float(out["irr_frac_pct"].max()),
        "max_all_field_frac_pct": float(out["all_field_frac_pct"].max()),
        "median_mascon_area_km2": float(out["area_km2"].median()),
        "total_irrigated_km2": float(out["irr_km2"].sum()),
        "n_top10_crossing_border": int(top["crosses_border"].sum()),
    }
    (OUT / "native_mascon_coverage.json").write_text(json.dumps(summary, indent=2))
    print("\n" + json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
