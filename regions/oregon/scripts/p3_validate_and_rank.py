"""Phase 3: (a) validate our field aggregation against DRI's published HUC-8
annual totals, (b) rank half-degree cells by irrigated-area fraction.

(a) is the proof that we read the database correctly: if our re-derived
irrigated acreage and CU volumes reproduce DRI's own HUC-8 numbers, then the
water-year handling, the irrigation-status rule and the unit handling are all
right. Any systematic gap is reported, not hidden.
"""
import numpy as np
import pandas as pd

P = r"E:\Water\Oregan\analysis\processed"
ACRE_M2 = 4046.8564224
AF_M3 = 1233.48183754752


def cell_area_m2(lat_c, dlat=0.5, dlon=0.5):
    """Spherical-Earth area of a lat/lon cell centred at lat_c."""
    R = 6371007.181  # authalic radius, m
    la0 = np.radians(lat_c - dlat / 2)
    la1 = np.radians(lat_c + dlat / 2)
    return (R ** 2) * np.radians(dlon) * (np.sin(la1) - np.sin(la0))


def main():
    cm = pd.read_parquet(rf"{P}\cell_monthly.parquet")
    print("cell_monthly:", cm.shape)
    print(cm.dtypes.to_string())
    print("\ntime range:", cm["time"].min(), "->", cm["time"].max())
    print("n distinct months:", cm["time"].nunique())
    print("n distinct cells:", cm.groupby(["grid_i", "grid_j"]).ngroups)

    # ---------- (a) validation against published HUC-8 annual totals -------
    pub = pd.read_parquet(rf"{P}\huc8_published_annual.parquet")
    ours = (cm[cm["is_irrigated"]]
            .groupby(["huc8", "water_year"], as_index=False)
            .agg(eta_af=("eta_af", "sum"), cuadj_af=("cuadj_af", "sum"),
                 aw_af=("aw_af", "sum"), effadj_af=("effadj_af", "sum"),
                 ppt_af=("ppt_af", "sum"), niwr_af=("niwr_af", "sum")))
    # acreage is per-field-year, not per-month: take one month's worth
    acr = (cm[cm["is_irrigated"]]
           .drop_duplicates(subset=["grid_i", "grid_j", "huc8", "water_year", "time"])
           .groupby(["huc8", "water_year", "time"], as_index=False)["acres"].sum()
           .groupby(["huc8", "water_year"], as_index=False)["acres"].mean())
    ours = ours.merge(acr, on=["huc8", "water_year"])

    v = pub.merge(ours, on=["huc8", "water_year"], how="inner")
    v = v[v["acres_pub"].notna()]
    print("\n=== VALIDATION vs published HUC-8 annual totals ===")
    print("matched HUC8-year pairs:", len(v))
    for a, b, lab in [("acres", "acres_pub", "irrigated acres"),
                      ("eta_af", "et_v_pub", "ETa volume (af)"),
                      ("cuadj_af", "cu_v_pub", "CU volume (af)"),
                      ("aw_af", "aw_v_pub", "AW volume (af)"),
                      ("effadj_af", "eff_v_pub", "Prz adj volume (af)"),
                      ("niwr_af", "niwr_v_pub", "NIWR volume (af)")]:
        x, y = v[a].values, v[b].values
        ok = np.isfinite(x) & np.isfinite(y) & (y != 0)
        bias = (x[ok].sum() / y[ok].sum() - 1) * 100
        r = np.corrcoef(x[ok], y[ok])[0, 1]
        mape = np.median(np.abs(x[ok] - y[ok]) / np.abs(y[ok])) * 100
        print(f"  {lab:22s} ours/pub-1 = {bias:+7.2f}%   r = {r:.5f}   "
              f"median|rel err| = {mape:6.2f}%   (n={ok.sum()})")

    st = v.groupby("water_year")[["acres", "acres_pub", "cuadj_af", "cu_v_pub"]].sum()
    print("\nstatewide by water year (ours vs published):")
    print(st.assign(acres_ratio=st["acres"] / st["acres_pub"],
                    cu_ratio=st["cuadj_af"] / st["cu_v_pub"]).round(3).to_string())

    # ---------- (b) rank half-degree cells by irrigated fraction -----------
    cells = cm.copy()
    cells["lon_c"] = -180 + (cells["grid_i"] + 0.5) * 0.5
    cells["lat_c"] = -90 + (cells["grid_j"] + 0.5) * 0.5

    # Per cell-year irrigated acreage. `acres` is a GROUP-level constant that
    # the melt replicated onto all 12 months, so it must be de-duplicated down
    # to ONE row per (cell, huc8, is_irrigated, water_year) before summing --
    # keeping one row per month would multiply every area by 12.
    one = cells.drop_duplicates(
        subset=["grid_i", "grid_j", "huc8", "is_irrigated", "water_year"])
    peryr = (one.groupby(["grid_i", "grid_j", "lon_c", "lat_c",
                          "water_year", "is_irrigated"], as_index=False)["acres"].sum())
    irr = (peryr[peryr["is_irrigated"]]
           .groupby(["grid_i", "grid_j", "lon_c", "lat_c"], as_index=False)["acres"]
           .mean().rename(columns={"acres": "irr_acres_mean"}))
    allf = (peryr.groupby(["grid_i", "grid_j"], as_index=False)["acres"]
            .mean().rename(columns={"acres": "field_acres_mean"}))
    rank = irr.merge(allf, on=["grid_i", "grid_j"], how="outer").fillna(0)
    rank["cell_area_km2"] = cell_area_m2(rank["lat_c"]) / 1e6
    rank["irr_km2"] = rank["irr_acres_mean"] * ACRE_M2 / 1e6
    rank["irr_frac_pct"] = 100 * rank["irr_km2"] / rank["cell_area_km2"]

    # annual mean CU per cell, and CU expressed as depth over the WHOLE cell
    cu = (cm[cm["is_irrigated"]]
          .groupby(["grid_i", "grid_j", "water_year"], as_index=False)["cuadj_af"].sum()
          .groupby(["grid_i", "grid_j"], as_index=False)["cuadj_af"].mean()
          .rename(columns={"cuadj_af": "cu_af_yr"}))
    eta = (cm.groupby(["grid_i", "grid_j", "water_year"], as_index=False)["eta_af"].sum()
           .groupby(["grid_i", "grid_j"], as_index=False)["eta_af"].mean()
           .rename(columns={"eta_af": "eta_af_yr_allfields"}))
    rank = rank.merge(cu, on=["grid_i", "grid_j"], how="left") \
               .merge(eta, on=["grid_i", "grid_j"], how="left").fillna(0)
    rank["cu_mm_yr_over_cell"] = (rank["cu_af_yr"] * AF_M3
                                  / (rank["cell_area_km2"] * 1e6)) * 1000
    rank = rank.sort_values("cu_mm_yr_over_cell", ascending=False)
    rank.to_parquet(rf"{P}\cell_irrigation_ranking.parquet", index=False)

    print("\n=== TOP 25 half-degree cells by CU depth spread over the whole cell ===")
    cols = ["lon_c", "lat_c", "cell_area_km2", "irr_km2", "irr_frac_pct",
            "cu_af_yr", "cu_mm_yr_over_cell"]
    print(rank[cols].head(25).to_string(index=False,
          float_format=lambda x: f"{x:,.2f}"))
    print("\nn cells with any field:", len(rank))
    print("total irrigated km2 (mean over years):", f"{rank['irr_km2'].sum():,.0f}")
    print("total CU af/yr:", f"{rank['cu_af_yr'].sum():,.0f}")


if __name__ == "__main__":
    main()
