"""Restrict the Saudi work to the Arabian Peninsula; move Iran to its own folder.

The bounding box the Arabian Peninsula run was given (12-32N, 34-60E) also
contains Iran, Sudan, Ethiopia, Iraq, Egypt, Eritrea and Jordan. The run
already excluded them from its candidate list using polygon membership, but
its two wide tables still carried all 379 mascons, so a reader sorting by
trend would have found Iranian depletion at the top of an Arabian Peninsula
file.

This rewrites those tables to peninsula-only (>50% of mascon area inside the
seven peninsula countries) and writes the Iranian mascons out separately.
Originals are preserved with a .full.csv suffix rather than deleted.
"""

import json
from pathlib import Path

import pandas as pd

SAUDI = Path(r"E:\Water\Saudi\trends")
IRAN = Path(r"E:\Water\Iran")
TABLES = ["all_mascons_flags.csv", "mascon_trends_and_quality.csv"]
PENINSULA_MIN = 0.5


def main():
    (IRAN / "trends").mkdir(parents=True, exist_ok=True)
    report = {}

    for name in TABLES:
        src = SAUDI / name
        df = pd.read_csv(src)
        full = SAUDI / name.replace(".csv", ".full.csv")
        if not full.exists():
            df.to_csv(full, index=False)

        pen = df[df["frac_area_arabian_peninsula"] > PENINSULA_MIN].copy()
        pen.to_csv(src, index=False)

        iran = df[df["country_of_center"] == "Iran"].copy()
        iran.to_csv(IRAN / "trends" / name.replace("mascon", "iran_mascon"), index=False)

        report[name] = {
            "original_rows": int(len(df)),
            "peninsula_rows": int(len(pen)),
            "iran_rows": int(len(iran)),
            "removed_rows": int(len(df) - len(pen)),
        }
        print(f"{name}: {len(df)} -> {len(pen)} peninsula, {len(iran)} Iran")

    # Headline numbers for each set, from the flags table.
    pen = pd.read_csv(SAUDI / "all_mascons_flags.csv")
    iran = pd.read_csv(IRAN / "trends" / "all_iran_mascons_flags.csv"
                       if (IRAN / "trends" / "all_iran_mascons_flags.csv").exists()
                       else IRAN / "trends" / "all_mascons_flags.csv")

    def stats(d, label):
        t = d["trend_cm_per_yr"].dropna()
        return {
            "set": label, "n_mascons": int(len(d)),
            "mean_trend_cm_per_yr": float(t.mean()),
            "median_trend_cm_per_yr": float(t.median()),
            "steepest_trend_cm_per_yr": float(t.min()),
            "n_significant_decline": int(d["significant_decline"].sum())
            if "significant_decline" in d else None,
        }

    report["peninsula_stats"] = stats(pen, "Arabian Peninsula")
    report["iran_stats"] = stats(iran, "Iran")
    (Path(r"E:\Water\Saudi") / "peninsula_iran_split.json").write_text(
        json.dumps(report, indent=2))
    print("\n" + json.dumps({k: report[k] for k in ("peninsula_stats", "iran_stats")}, indent=2))


if __name__ == "__main__":
    main()
