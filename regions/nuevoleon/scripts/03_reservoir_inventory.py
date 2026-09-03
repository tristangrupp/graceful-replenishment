"""Phase 1: what the reservoirs are worth in GRACE units.

Assembles the CONAGUA SINA daily-monitoring snapshots into (a) a static dam
table and (b) a per-dam storage series, assigns every dam to the GSFC mascon
whose box contains it, and converts hm^3 of water into mm of equivalent
water height spread over that mascon's own area.

That conversion is the whole question. A mascon here is ~12,400 km^2, so

    1 hm^3 (= 1e6 m^3) over 12,400 km^2  =  8.06e-5 m  =  0.081 mm

and a 1,000 hm^3 reservoir is therefore ~81 mm of mascon-mean storage --
which is the same order as the entire post-2020 drying signal. The output
decides whether the reservoir term has to be removed before anything can
be said about groundwater.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"E:\Water\NuevoLeon")
SNAP = ROOT / "raw" / "conagua_presas"
INV = ROOT / "inventory"
SIG = ROOT / "signals"

MONTERREY = (25.6866, -100.3161)   # city centre, background knowledge


def load_snapshots():
    frames = []
    for f in sorted(SNAP.glob("*.json")):
        try:
            j = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not j:
            continue
        d = pd.DataFrame(j)
        d["snapshot_date"] = pd.Timestamp(f.stem)
        frames.append(d)
    df = pd.concat(frames, ignore_index=True)
    for c in ["latitud", "longitud", "namoalmac", "almacenaactual", "llenano",
              "namealmac", "alturacortina"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def main():
    INV.mkdir(parents=True, exist_ok=True)
    df = load_snapshots()
    print(f"{df['snapshot_date'].nunique()} snapshots, "
          f"{df['snapshot_date'].min():%Y-%m} .. {df['snapshot_date'].max():%Y-%m}, "
          f"{df['clavesih'].nunique()} distinct dams")

    mas = pd.read_csv(SIG / "mascon_metadata.csv")

    # static dam table: take the most recent non-null record per dam
    df = df.sort_values("snapshot_date")
    static = (df.groupby("clavesih")
                .agg(nombrecomun=("nombrecomun", "last"),
                     nombreoficial=("nombreoficial", "last"),
                     estado=("estado", "last"),
                     municipio=("nommunicipio", "last"),
                     lat=("latitud", "median"),
                     lon=("longitud", "median"),
                     namo_hm3=("namoalmac", "median"),
                     name_hm3=("namealmac", "median"),
                     n_obs=("almacenaactual", "count"),
                     stor_min_hm3=("almacenaactual", "min"),
                     stor_max_hm3=("almacenaactual", "max"),
                     stor_mean_hm3=("almacenaactual", "mean"))
                .reset_index())

    # assign to mascon boxes
    def which(lat, lon):
        hit = mas[(mas.lat_min <= lat) & (lat < mas.lat_max)
                  & (mas.lon_min <= lon) & (lon < mas.lon_max)]
        return int(hit.iloc[0]["mascon_id"]) if len(hit) else -1

    static["mascon_id"] = [which(a, b) for a, b in zip(static["lat"], static["lon"])]
    inreg = static[static["mascon_id"] >= 0].copy()
    area = mas.set_index("mascon_id")["area_km2"]
    # hm^3 -> mm over the mascon: 1e6 m^3 / (area_km2 * 1e6 m^2) * 1000 mm/m
    inreg["mm_per_hm3"] = 1000.0 / area.reindex(inreg["mascon_id"]).to_numpy()
    for c in ["namo", "stor_min", "stor_max", "stor_mean"]:
        inreg[f"{c}_mm"] = inreg[f"{c}_hm3"] * inreg["mm_per_hm3"]
    inreg["range_hm3"] = inreg["stor_max_hm3"] - inreg["stor_min_hm3"]
    inreg["range_mm"] = inreg["range_hm3"] * inreg["mm_per_hm3"]
    inreg = inreg.sort_values("namo_hm3", ascending=False)
    inreg.to_csv(INV / "dams_in_region.csv", index=False)

    # per-mascon aggregation
    per = (inreg.groupby("mascon_id")
           .agg(n_dams=("clavesih", "size"),
                namo_hm3=("namo_hm3", "sum"),
                namo_mm=("namo_mm", "sum"),
                range_hm3=("range_hm3", "sum"),
                range_mm=("range_mm", "sum"))
           .reset_index())
    per = per.merge(mas[["mascon_id", "lat_center", "lon_180", "area_km2",
                         "leakage_2sigma_cm", "leakage_trend_cm_yr"]], on="mascon_id")
    per.to_csv(INV / "reservoir_per_mascon.csv", index=False)

    # GRACE noise floor for comparison
    long = pd.read_parquet(SIG / "mascon_monthly_long.parquet")
    obs = long[long["observed"]]
    noise = obs.groupby("mascon_id")["noise_2sigma_cm"].median() * 10.0     # mm
    tws_sd = obs.groupby("mascon_id")["lwe_cm"].std() * 10.0
    per = per.merge(noise.rename("noise_2sigma_mm"), on="mascon_id")
    per = per.merge(tws_sd.rename("tws_sd_mm"), on="mascon_id")
    per["namo_over_noise"] = per["namo_mm"] / per["noise_2sigma_mm"]
    per["range_over_noise"] = per["range_mm"] / per["noise_2sigma_mm"]
    per["range_over_tws_sd"] = per["range_mm"] / per["tws_sd_mm"]
    per = per.sort_values("namo_mm", ascending=False)
    per.to_csv(INV / "reservoir_per_mascon.csv", index=False)

    mty = which(*MONTERREY)
    tot_area = mas["area_km2"].sum()
    summary = {
        "n_snapshots": int(df["snapshot_date"].nunique()),
        "snapshot_first": str(df["snapshot_date"].min().date()),
        "snapshot_last": str(df["snapshot_date"].max().date()),
        "n_dams_national": int(static["clavesih"].nunique()),
        "n_dams_in_mascon_window": int(len(inreg)),
        "monterrey_mascon_id": mty,
        "region_area_km2": float(tot_area),
        "region_namo_hm3": float(inreg["namo_hm3"].sum()),
        "region_namo_mm_over_whole_region": float(inreg["namo_hm3"].sum() * 1e6
                                                  / (tot_area * 1e6) * 1000),
        "region_observed_range_hm3": float(inreg["range_hm3"].sum()),
        "region_observed_range_mm_over_whole_region": float(inreg["range_hm3"].sum() * 1e6
                                                            / (tot_area * 1e6) * 1000),
        "max_single_mascon_namo_mm": float(per["namo_mm"].max()),
        "max_single_mascon_range_mm": float(per["range_mm"].max()),
        "median_mascon_noise_2sigma_mm": float(per["noise_2sigma_mm"].median()),
        "n_mascons_with_dams": int(len(per)),
        "n_mascons_range_gt_noise": int((per["range_mm"] > per["noise_2sigma_mm"]).sum()),
        "mm_per_hm3_at_12400km2": float(1000.0 / 12400.0),
    }
    (INV / "reservoir_magnitude.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print()
    print(inreg.head(15)[["nombrecomun", "estado", "lat", "lon", "mascon_id",
                          "namo_hm3", "namo_mm", "range_hm3", "range_mm"]].to_string(index=False))
    print()
    print(per.head(12)[["mascon_id", "lat_center", "lon_180", "n_dams", "namo_hm3",
                        "namo_mm", "range_mm", "noise_2sigma_mm", "tws_sd_mm",
                        "range_over_noise", "range_over_tws_sd"]].to_string(index=False))


if __name__ == "__main__":
    main()
