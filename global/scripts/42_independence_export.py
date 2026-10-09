"""Payload for the shared-signal tab.

40_spatial_autocorr.py writes a full JSON of everything it measured. The page
needs a fraction of it, plus one thing the JSON does not hold: the p-value cut
each multiple-testing rule implies, so the map can hatch on the rule the reader
picks rather than on a stored flag.

The map itself reuses data.js, which already carries the 1,283 level 4 basins
with their trends and p-values, so this file stays a few kilobytes.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(r"E:\Water\Global")
SRC = ROOT / "trends" / "spatial_autocorr_lev04.json"
TRENDS = ROOT / "trends" / "basins_lev04_trends.csv"
OUT = ROOT / "viz" / "site" / "independence_data.js"

sac = json.load(open(SRC))
tr = pd.read_csv(TRENDS)


def cuts(p, alpha=0.05):
    """The largest p-value each rule still accepts.

    Both rules walk the sorted p-values against a threshold that rises with
    rank. Benjamini-Hochberg uses alpha * i / m; Benjamini-Yekutieli divides
    that by c(m), the harmonic sum, which is what buys validity under any
    dependence. Returning the accepted cut lets the page hatch with a single
    comparison instead of shipping three flag arrays.
    """
    p = np.sort(np.asarray(p[np.isfinite(p)], dtype="float64"))
    m = len(p)
    rank = np.arange(1, m + 1)
    c_m = np.log(m) + 0.5772156649 + 1.0 / (2 * m)
    out = {"n_tested": int(m), "c_m": float(c_m),
           "raw": alpha, "bonferroni": alpha / m}
    for name, thr in (("bh", alpha * rank / m), ("by", alpha * rank / (m * c_m))):
        ok = p <= thr
        out[name] = float(p[rank[ok].max() - 1]) if ok.any() else 0.0
        out["n_" + name] = int(rank[ok].max()) if ok.any() else 0
    out["n_raw"] = int((p < alpha).sum())
    return out


payload = {
    "n_basins": sac["n_basins"],
    "n_perm": sac["n_perm"],
    "mean_neighbours": round(sac["weights"]["mean_neighbours"], 2),
    "layers": {},
    "comparators": sac["comparators"],
}

for key, tcol, pcol, label in [("t", "tws_trend_mm_yr", "tws_p", "Total water storage"),
                               ("g", "gws_trend_mm_yr", "gws_p", "Groundwater estimate")]:
    src = sac["layers"]["tws" if key == "t" else "gws"]
    a = src["all"]
    payload["layers"][key] = {
        "label": label,
        "n": a["n"],
        "moran": round(a["global_moran_contiguity"]["I"], 3),
        "moran_p": a["global_moran_contiguity"]["p_perm"],
        "moran_ranks": round(src["all_ranks"]["global_moran_contiguity"]["I"], 3),
        "moran_no_ice": round(src["no_ice"]["global_moran_contiguity"]["I"], 3),
        "e_folding_km": round(a["effective_n"]["e_folding_km"]),
        "n_eff": round(a["effective_n"]["n_eff"], 1),
        "n_eff_share": round(a["effective_n"]["n_eff_share"], 4),
        "correlogram": [{"lo": c["lo_km"], "hi": c["hi_km"],
                         "I": round(c["I"], 3), "p": c["p_perm"],
                         "pairs": c["pairs"]}
                        for c in a["correlogram"]],
        "cuts": cuts(tr[pcol].to_numpy()),
    }

OUT.write_text("window.IND=" + json.dumps(payload, separators=(",", ":")) + ";\n",
               encoding="utf-8")
print("wrote", OUT, OUT.stat().st_size, "bytes")
for k, v in payload["layers"].items():
    c = v["cuts"]
    print(f"  {v['label']}: Moran {v['moran']}, e-folding {v['e_folding_km']} km, "
          f"n_eff {v['n_eff']}; significant raw {c['n_raw']}, BH {c['n_bh']} "
          f"(p<={c['bh']:.4f}), BY {c['n_by']} (p<={c['by']:.4f})")
