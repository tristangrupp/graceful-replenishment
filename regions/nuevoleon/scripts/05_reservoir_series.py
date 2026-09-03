"""Phase 1/2: the reservoir term, in mm of mascon-mean equivalent water height.

Builds a monthly reservoir-storage series for every GSFC mascon in the
window, in the same units and on the same baseline as GRACE.

Two sources, and the reason there are two:

* **CONAGUA SINA** daily monitoring (`almacenaactual`, hm^3) for all dams.
  Verified here to break definitionally in April 2018 for the two
  international Rio Grande reservoirs: between the 2018-03-15 and
  2018-05-15 snapshots Amistad drops 2484.7 -> 494.5 hm^3 and Falcon
  1709.4 -> 231.8 hm^3, with `namoalmac` switching from the whole-lake
  capacity to Mexico's treaty allotment in the same step. After that date
  SINA reports Mexico's ownership balance, which is an accounting quantity,
  not the water GRACE weighs.

* **TWDB Water Data for Texas** daily `reservoir_storage` ("actual storage
  at measured lake elevation") for Amistad and Falcon, 1968-2026. This is
  the whole-lake figure: on 2018-03-15 it gives 2,013,173 ac-ft = 2483.2
  hm^3 at Amistad against SINA's 2484.7, and 1,384,408 ac-ft = 1707.6 hm^3
  at Falcon against SINA's 1709.4 - agreement to 0.1%, which is what
  identifies it as the total rather than the US share (TWDB's
  `conservation_storage` column *is* the US share and does not match).

Anomalies are taken against **2004-01..2009-12**, the GSFC solution's own
baseline, so the reservoir series can be subtracted from GRACE directly.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"E:\Water\NuevoLeon")
SNAP = ROOT / "raw" / "conagua_presas"
INV, SIG = ROOT / "inventory", ROOT / "signals"

ACFT_TO_HM3 = 1233.48183754752 / 1e6      # ac-ft -> hm^3 (1 hm^3 = 1e6 m^3)
BASELINE = ("2004-01", "2009-12")         # GSFC RL06v2.0 mascon baseline
# TWDB replaces SINA for these two; keys are rounded (lat, lon) of the SINA record
INTERNATIONAL = {"29.45_-101.06": "amistad", "26.56_-99.17": "falcon"}


def sina_long():
    rows = []
    for f in sorted(SNAP.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        if not j:
            continue
        d = pd.Timestamp(f.stem)
        for x in j:
            rows.append((d, x.get("nombrecomun"), x.get("nombreoficial"), x.get("estado"),
                         x.get("nommunicipio"), x.get("latitud"), x.get("longitud"),
                         x.get("namoalmac"), x.get("almacenaactual")))
    d = pd.DataFrame(rows, columns=["date", "name", "official", "estado", "municipio",
                                    "lat", "lon", "namo_hm3", "stor_hm3"])
    for c in ["lat", "lon", "namo_hm3", "stor_hm3"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    # `clavesih` is not stable (185 of 212 codes move between coordinates over the
    # record) and dam names change spelling, so the dam key is its position.
    d["key"] = d["lat"].round(2).astype(str) + "_" + d["lon"].round(2).astype(str)
    d["month"] = d["date"].dt.to_period("M")
    return d


def twdb_monthly(name):
    p = ROOT / "raw" / f"twdb_{name}.csv"
    df = pd.read_csv(p, comment="#")
    df["date"] = pd.to_datetime(df["date"])
    df["stor_hm3"] = df["reservoir_storage"] * ACFT_TO_HM3
    df["month"] = df["date"].dt.to_period("M")
    return df.groupby("month")["stor_hm3"].mean()


def main():
    INV.mkdir(parents=True, exist_ok=True)
    mas = pd.read_csv(SIG / "mascon_metadata.csv")
    sina = sina_long()

    # --- cross-source verification, printed and saved, not assumed
    checks = []
    for key, tw in INTERNATIONAL.items():
        t = twdb_monthly(tw)
        s = sina[sina["key"] == key].set_index("month")["stor_hm3"]
        both = pd.concat([s.rename("sina"), t.rename("twdb")], axis=1).dropna()
        pre = both[both.index < pd.Period("2018-04", "M")]
        post = both[both.index >= pd.Period("2018-05", "M")]
        checks.append({
            "dam": tw, "sina_key": key,
            "n_months_overlap": int(len(both)),
            "pre_2018_04_median_ratio_sina_over_twdb": float((pre["sina"] / pre["twdb"]).median()),
            "post_2018_05_median_ratio_sina_over_twdb": float((post["sina"] / post["twdb"]).median()),
            "pre_2018_04_r": float(pre.corr().iloc[0, 1]),
            "post_2018_05_r": float(post.corr().iloc[0, 1]),
        })
    (INV / "international_reservoir_source_check.json").write_text(json.dumps(checks, indent=2))
    print(json.dumps(checks, indent=2))

    # --- monthly storage per dam, TWDB substituted for the two international lakes
    dam_month = (sina.groupby(["key", "month"])["stor_hm3"].mean().unstack("month"))
    months = pd.period_range("2002-04", "2026-06", freq="M")
    dam_month = dam_month.reindex(columns=months)
    for key, tw in INTERNATIONAL.items():
        t = twdb_monthly(tw).reindex(months)
        dam_month.loc[key] = t.to_numpy()

    static = (sina.sort_values("date").groupby("key")
              .agg(name=("name", "last"), official=("official", "last"),
                   estado=("estado", "last"), municipio=("municipio", "last"),
                   lat=("lat", "median"), lon=("lon", "median"),
                   namo_hm3=("namo_hm3", "median")).reset_index())
    static["source"] = np.where(static["key"].isin(INTERNATIONAL),
                                "TWDB reservoir_storage", "CONAGUA SINA almacenaactual")
    # NAMO for the international pair: use the whole-lake conservation capacity
    for key, tw in INTERNATIONAL.items():
        cap = pd.read_csv(ROOT / "raw" / f"twdb_{tw}.csv", comment="#")
        frac = {"amistad": 0.562, "falcon": 0.586}[tw]     # Texas share, from the TWDB footnote
        static.loc[static["key"] == key, "namo_hm3"] = \
            float(cap["conservation_capacity"].iloc[-1]) * ACFT_TO_HM3 / frac

    def which(lat, lon):
        hit = mas[(mas.lat_min <= lat) & (lat < mas.lat_max)
                  & (mas.lon_min <= lon) & (lon < mas.lon_max)]
        return int(hit.iloc[0]["mascon_id"]) if len(hit) else -1

    static["mascon_id"] = [which(a, b) for a, b in zip(static["lat"], static["lon"])]
    inreg = static[static["mascon_id"] >= 0].copy()
    area = mas.set_index("mascon_id")["area_km2"]
    inreg["mascon_area_km2"] = area.reindex(inreg["mascon_id"]).to_numpy()
    inreg["mm_per_hm3"] = 1000.0 / inreg["mascon_area_km2"]
    inreg["namo_mm"] = inreg["namo_hm3"] * inreg["mm_per_hm3"]

    ser = dam_month.loc[inreg["key"]]
    inreg["obs_min_hm3"] = ser.min(axis=1).to_numpy()
    inreg["obs_max_hm3"] = ser.max(axis=1).to_numpy()
    inreg["obs_range_hm3"] = inreg["obs_max_hm3"] - inreg["obs_min_hm3"]
    inreg["obs_range_mm"] = inreg["obs_range_hm3"] * inreg["mm_per_hm3"]
    inreg["n_months"] = ser.notna().sum(axis=1).to_numpy()
    inreg = inreg.sort_values("namo_hm3", ascending=False)
    inreg.to_csv(INV / "dams_in_region.csv", index=False)

    # --- per-mascon reservoir series in mm, anomaly on the GRACE baseline
    # A month is only usable for a mascon if EVERY dam in it reported. Filling a
    # non-reporting dam with zero would manufacture a cliff: CONAGUA's public
    # endpoint has returned an empty array for every date after ~2025-04-15
    # (verified at 2025-04-28, 2025-05-02, 2025-06-10, 2025-09-15, 2026-01-20 and
    # 2026-07-20), so the SINA-sourced dams simply stop, and zero-filling them
    # would look like every reservoir in Mexico emptying overnight.
    res_mm = pd.DataFrame(0.0, index=months, columns=sorted(inreg["mascon_id"].unique()))
    ndam = pd.DataFrame(0, index=months, columns=res_mm.columns)
    for _, r in inreg.iterrows():
        s = dam_month.loc[r["key"]] * r["mm_per_hm3"]
        res_mm[r["mascon_id"]] = res_mm[r["mascon_id"]].add(s.fillna(0.0), fill_value=0.0)
        ndam[r["mascon_id"]] += s.notna().astype(int)
    full = inreg.groupby("mascon_id").size()
    res_mm = res_mm.where(ndam.eq(full.reindex(res_mm.columns), axis=1))
    ndam.to_parquet(SIG / "reservoir_dams_reporting.parquet")
    base = res_mm.loc[(res_mm.index >= pd.Period(BASELINE[0], "M"))
                      & (res_mm.index <= pd.Period(BASELINE[1], "M"))].mean()
    res_anom = res_mm - base
    res_anom.index = res_anom.index.to_timestamp()
    res_mm.index = res_mm.index.to_timestamp()
    res_anom.to_parquet(SIG / "reservoir_anomaly_mm.parquet")
    res_mm.to_parquet(SIG / "reservoir_absolute_mm.parquet")

    per = (inreg.groupby("mascon_id")
           .agg(n_dams=("key", "size"), namo_hm3=("namo_hm3", "sum"),
                namo_mm=("namo_mm", "sum"), obs_range_mm=("obs_range_mm", "sum"))
           .reset_index())
    per["res_anom_sd_mm"] = [res_anom[m].std() for m in per["mascon_id"]]
    per["res_anom_range_mm"] = [res_anom[m].max() - res_anom[m].min() for m in per["mascon_id"]]
    per = per.merge(mas[["mascon_id", "lat_center", "lon_180", "area_km2",
                         "leakage_2sigma_cm", "leakage_trend_cm_yr"]], on="mascon_id")

    long = pd.read_parquet(SIG / "mascon_monthly_long.parquet")
    obs = long[long["observed"]]
    per = per.merge((obs.groupby("mascon_id")["noise_2sigma_cm"].median() * 10)
                    .rename("grace_noise_2sigma_mm"), on="mascon_id")
    per = per.merge((obs.groupby("mascon_id")["lwe_cm"].std() * 10)
                    .rename("grace_tws_sd_mm"), on="mascon_id")
    per["namo_over_noise"] = per["namo_mm"] / per["grace_noise_2sigma_mm"]
    per["res_sd_over_tws_sd"] = per["res_anom_sd_mm"] / per["grace_tws_sd_mm"]
    per = per.sort_values("namo_mm", ascending=False)
    per.to_csv(INV / "reservoir_per_mascon.csv", index=False)

    # --- the Phase 1 headline number
    MTY = {"25.71_-99.28": "El Cuchillo", "24.94_-99.4": "Cerro Prieto",
           "25.43_-100.13": "La Boca"}
    mty = inreg[inreg["key"].isin(MTY)].copy()
    mty_cap = float(mty["namo_hm3"].sum())
    mty_series = dam_month.loc[mty["key"]].sum(axis=0, min_count=1)
    mty_series.index = mty_series.index.to_timestamp()
    mty_series.rename("monterrey_system_hm3").to_frame().to_csv(
        SIG / "monterrey_system_storage_hm3.csv")
    med_area = float(mas["area_km2"].median())
    med_noise = float(per["grace_noise_2sigma_mm"].median())
    headline = {
        "monterrey_system_dams": list(MTY.values()),
        "monterrey_system_namo_hm3": mty_cap,
        "monterrey_system_mm_over_one_median_mascon": mty_cap * 1000.0 / med_area,
        "monterrey_system_observed_range_hm3": float(mty_series.max() - mty_series.min()),
        "monterrey_system_observed_range_mm_over_one_mascon":
            float(mty_series.max() - mty_series.min()) * 1000.0 / med_area,
        "monterrey_system_min_hm3": float(mty_series.min()),
        "monterrey_system_min_date": str(mty_series.idxmin().date()),
        "monterrey_system_max_hm3": float(mty_series.max()),
        "monterrey_system_max_date": str(mty_series.idxmax().date()),
        "median_mascon_area_km2": med_area,
        "mm_per_hm3": 1000.0 / med_area,
        "median_grace_noise_2sigma_mm": med_noise,
        "monterrey_capacity_over_grace_noise": mty_cap * 1000.0 / med_area / med_noise,
        "monterrey_range_over_grace_noise":
            float(mty_series.max() - mty_series.min()) * 1000.0 / med_area / med_noise,
        "all_dams_in_window_namo_hm3": float(inreg["namo_hm3"].sum()),
        "all_dams_in_window_namo_mm_over_region": float(inreg["namo_hm3"].sum()) * 1000.0
                                                  / float(mas["area_km2"].sum()),
        "largest_single_mascon_namo_mm": float(per["namo_mm"].max()),
        "largest_single_mascon_res_anom_range_mm": float(per["res_anom_range_mm"].max()),
        "n_mascons_with_dams": int(len(per)),
        "n_mascons_res_sd_exceeds_half_tws_sd": int((per["res_sd_over_tws_sd"] > 0.5).sum()),
    }
    (INV / "reservoir_magnitude.json").write_text(json.dumps(headline, indent=2))
    print(json.dumps(headline, indent=2))
    print()
    print(per[["mascon_id", "lat_center", "lon_180", "n_dams", "namo_mm", "res_anom_sd_mm",
               "res_anom_range_mm", "grace_noise_2sigma_mm", "grace_tws_sd_mm",
               "res_sd_over_tws_sd"]].to_string(index=False))


if __name__ == "__main__":
    main()
