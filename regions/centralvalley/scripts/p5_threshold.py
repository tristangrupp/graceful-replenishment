"""Phase 5 - the deliverable: a detection threshold that can be applied to a new
basin from coverage statistics alone.

Three measured relations, each fitted here rather than assumed:

  (1) SIGNAL.  The deseasonalised consumptive-use anomaly scales with the mean
      consumptive-use depth over the footprint:
          sigma_CU'  =  gamma * (CU_annual / 12)
      gamma is fitted across four Central Valley footprints and all 40 mascons,
      and checked against Oregon's independent numbers.

  (2) NOISE.  The dS/dt noise floor is a property of GRACE, not of the basin,
      and barely improves with aggregation when mascons are correlated.
      Measured here against footprint size and against effective DOF.

  (3) POWER.  The standard error of the regression coefficient on CU is
          se(b_CU) = 1 / (SNR * sqrt(n_eff))
      so constraining a unit coefficient at 2 sigma needs
          SNR * sqrt(n_eff) >= 2.
      This identity is verified against the four measured regressions before
      being used to extrapolate.

Combining gives a threshold in the one number a new basin can supply cheaply:
      D = f_irr * CU_irr   (= consumptive-use depth over the whole footprint,
                             mm/yr)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

OUT = Path(r"E:\Water\CentralValley\processed")
INV = Path(r"E:\Water\CentralValley\inventory")

# Oregon's published calibration points (E:\Water\Oregan\analysis\REPORT.md)
OREGON = {
    "cu_ds_std_mm": 0.43, "dsdt_noise_mm": 10.46,
    "snr_300km": 0.041, "snr_best_mascon": 0.150,
    "cu_mm_yr_300km": 17.7, "irr_frac_300km": 3.27,
    "cu_mm_yr_1deg": 79.2, "irr_frac_1deg": 12.72,
    "irr_frac_best_mascon": 14.5, "n_months": 176,
    "b_CU": 3.112, "se_CU": 3.550,
}


def main():
    fp = pd.read_csv(OUT / "flux_results_footprints.csv")
    per = pd.read_csv(OUT / "flux_results_per_mascon.csv")

    # ---------------------------------------------------------- (1) signal
    fp["cu_mm_month"] = fp["cu_mm_yr"] / 12.0
    per["cu_mm_month"] = per["cu_mm_yr"] / 12.0
    sub = per[per["cu_mm_yr"] > 5]
    gamma_fp = float((fp["cu_ds_std_mm"] / fp["cu_mm_month"]).mean())
    gamma_per = float((sub["cu_ds_std_mm"] / sub["cu_mm_month"]).median())
    gamma_all = float(np.median(np.concatenate([
        (fp["cu_ds_std_mm"] / fp["cu_mm_month"]).to_numpy(),
        (sub["cu_ds_std_mm"] / sub["cu_mm_month"]).to_numpy()])))
    gamma_or = OREGON["cu_ds_std_mm"] / (OREGON["cu_mm_yr_300km"] / 12.0)
    print(f"(1) gamma = sigma_CU' / mean monthly CU")
    print(f"    footprints      {gamma_fp:.3f}")
    print(f"    per-mascon med  {gamma_per:.3f}  (n={len(sub)})")
    print(f"    pooled median   {gamma_all:.3f}")
    print(f"    Oregon 300 km   {gamma_or:.3f}   <- independent basin")

    # CU depth over irrigated land, from the coverage table
    cov = pd.read_csv(OUT / "mascon_coverage.csv").set_index("mascon_id")
    per = per.join(cov[["irr_crop_frac_pct"]].rename(
        columns={"irr_crop_frac_pct": "_icf"}), on="mascon_id")
    per["cu_over_irrigated_mm_yr"] = per["cu_mm_yr"] / (per["irr_frac_pct"] / 100.0)

    # ----------------------------------------------------------- (2) noise
    print("\n(2) dS/dt noise floor vs footprint")
    n_masc = {"best native mascon (1850, Tulare)": 1,
              "300 km footprint around 1850": 6,
              "irrigated core (8 mascons >=10% irr)": 8,
              "all 40 land mascons": 40}
    fp["n_mascons"] = fp["footprint"].map(n_masc)
    for _, r in fp.iterrows():
        ideal = fp.loc[0, "dsdt_noise_mm"] / np.sqrt(r["n_mascons"])
        print(f"    {r['footprint'][:36]:36s} N={r['n_mascons']:2.0f}  "
              f"measured {r['dsdt_noise_mm']:5.2f}   "
              f"if independent {ideal:5.2f}   "
              f"ratio {r['dsdt_noise_mm']/ideal:4.2f}x")
    noise_ref = float(per["dsdt_noise_mm"].median())
    print(f"    median single-mascon dS/dt noise: {noise_ref:.2f} mm/month")
    print(f"    Oregon (300 km):                  {OREGON['dsdt_noise_mm']:.2f} mm/month")

    # ----------------------------------------------------------- (3) power
    print("\n(3) power identity  se(b_CU) = 1 / (SNR * sqrt(n_eff))")
    fp["se_pred"] = 1.0 / (fp["snr_vs_residual"] * np.sqrt(fp["n_eff_resid"]))
    for _, r in fp.iterrows():
        print(f"    {r['footprint'][:36]:36s} predicted {r['se_pred']:.3f}   "
              f"measured {r['se_CU']:.3f}   ratio {r['se_CU']/r['se_pred']:.2f}")
    calib = float((fp["se_CU"] / fp["se_pred"]).mean())
    print(f"    calibration factor {calib:.2f} (1.0 = identity exact)")

    # ------------------------------------------------------- the threshold
    # The FOOTPRINT-level gamma is used, not the pooled one. The per-mascon
    # median (0.46) is inflated by mascons whose consumptive use is small, where
    # DAUCO-to-mascon assignment noise is a large fraction of a small signal;
    # the threshold is applied to footprints, and the footprint value (0.305)
    # is independently reproduced by Oregon (0.292). Using the pooled 0.43
    # would make the threshold ~40% more optimistic on no evidence.
    gamma = gamma_fp
    gamma_spread = float(np.std(
        (fp["cu_ds_std_mm"] / fp["cu_mm_month"]).to_numpy(), ddof=1))
    n_eff_typ = float(fp["n_eff_resid"].mean())
    snr_needed = 2.0 / np.sqrt(n_eff_typ) * calib
    sigma_cu_needed = snr_needed * noise_ref
    D_needed = sigma_cu_needed * 12.0 / gamma

    print("\n" + "=" * 68)
    print("DETECTION THRESHOLD")
    print("=" * 68)
    print(f"  record length used here      {int(fp['n_months'].iloc[0])} usable dS/dt months")
    print(f"  effective sample size        {n_eff_typ:.0f}  (lag-1 corrected)")
    print(f"  required SNR for 2 sigma     {snr_needed:.3f}")
    print(f"  required sigma_CU'           {sigma_cu_needed:.2f} mm/month")
    print(f"  required CU depth over the footprint  D = f_irr x CU_irr")
    print(f"                               >= {D_needed:.0f} mm/yr")
    print()
    for cu_irr, label in [(1000, "Central Valley orchards/row crops"),
                          (700, "mixed irrigated agriculture"),
                          (620, "Oregon (measured 79.2/0.1272)"),
                          (400, "low-demand / short season")]:
        print(f"    if CU over irrigated land = {cu_irr:5d} mm/yr  ->  "
              f"need f_irr >= {100*D_needed/cu_irr:5.1f}% of the footprint")

    # where each measured footprint sits
    print("\n  measured footprints against the threshold:")
    fp["D_mm_yr"] = fp["cu_mm_yr"]
    for _, r in fp.iterrows():
        verdict = "PASS" if r["snr_vs_noisefloor"] >= snr_needed else "fail"
        print(f"    {r['footprint'][:36]:36s} f_irr {r['irr_frac_pct']:5.2f}%  "
              f"D {r['D_mm_yr']:6.1f} mm/yr  SNR {r['snr_vs_noisefloor']:.3f}  {verdict}")
    print(f"    {'OREGON best native mascon':36s} f_irr "
          f"{OREGON['irr_frac_best_mascon']:5.2f}%  "
          f"D {OREGON['cu_mm_yr_1deg']:6.1f} mm/yr  "
          f"SNR {OREGON['snr_best_mascon']:.3f}  "
          f"{'PASS' if OREGON['snr_best_mascon'] >= snr_needed else 'fail'}")
    print(f"    {'OREGON 300 km footprint':36s} f_irr "
          f"{OREGON['irr_frac_300km']:5.2f}%  "
          f"D {OREGON['cu_mm_yr_300km']:6.1f} mm/yr  "
          f"SNR {OREGON['snr_300km']:.3f}  "
          f"{'PASS' if OREGON['snr_300km'] >= snr_needed else 'fail'}")

    # months required, per footprint and for a hypothetical basin
    fp["months_for_2sigma"] = (2.0 * calib / fp["snr_vs_noisefloor"]) ** 2
    print("\n  effective months of record needed for a 2 sigma constraint:")
    for _, r in fp.iterrows():
        print(f"    {r['footprint'][:36]:36s} {r['months_for_2sigma']:8.0f} "
              f"(= {r['months_for_2sigma']/12:6.1f} yr effective)")
    or_months = (2.0 * calib / OREGON["snr_300km"]) ** 2
    print(f"    {'OREGON 300 km footprint':36s} {or_months:8.0f} "
          f"(= {or_months/12:6.1f} yr effective)")

    out = {
        "gamma_sigma_cu_over_mean_cu": {
            "central_valley_footprints": gamma_fp,
            "central_valley_per_mascon_median": gamma_per,
            "pooled_median_not_used": gamma_all,
            "used_for_threshold": gamma_fp,
            "footprint_gamma_sd": gamma_spread,
            "oregon_independent": gamma_or,
        },
        "dsdt_noise_mm_per_month": {
            "central_valley_single_mascon_median": noise_ref,
            "central_valley_40_mascon_mean": float(fp.loc[3, "dsdt_noise_mm"]),
            "reduction_from_1_to_40_mascons": float(
                fp.loc[3, "dsdt_noise_mm"] / fp.loc[0, "dsdt_noise_mm"]),
            "reduction_if_independent": float(1 / np.sqrt(40)),
            "oregon_300km": OREGON["dsdt_noise_mm"],
        },
        "power": {
            "identity": "se(b_CU) = 1 / (SNR * sqrt(n_eff))",
            "calibration_factor_measured": calib,
            "n_eff_typical": n_eff_typ,
            "n_months_usable": int(fp["n_months"].iloc[0]),
        },
        "threshold": {
            "required_snr_2sigma": snr_needed,
            "required_sigma_cu_mm_month": sigma_cu_needed,
            "required_cu_depth_over_footprint_mm_yr": D_needed,
            "formula": ("f_irr * CU_irr >= 2 * sigma_noise * 12 / "
                        "(gamma * sqrt(n_eff))"),
            "required_irrigated_fraction_pct": {
                "cu_irr_1000": 100 * D_needed / 1000,
                "cu_irr_700": 100 * D_needed / 700,
                "cu_irr_620_oregon": 100 * D_needed / 620,
                "cu_irr_400": 100 * D_needed / 400,
            },
        },
        "footprints_measured": fp.to_dict("records"),
    }
    (INV / "detection_threshold.json").write_text(json.dumps(out, indent=2, default=float))
    fp.to_csv(OUT / "threshold_footprints.csv", index=False)
    per.to_csv(OUT / "threshold_per_mascon.csv", index=False)
    print("\nwrote inventory/detection_threshold.json")


if __name__ == "__main__":
    main()
