"""Export the red experiment for the site tab.

Two things go into the payload: the level 6 basin outlines as integer Robinson
pixel paths, and one array per metric. The page recomputes the flags itself from
those arrays, so moving a threshold redraws the map immediately. That is the
point of shipping the metrics rather than the verdicts: every threshold in this
experiment is a judgment call, and a reader who cannot move one has to take the
author's word for where the line sits.

16,397 basins is too many for one SVG path element each, so the page draws them
to a canvas and hit-tests against a second, hidden canvas painted with basin
index as colour.
"""

import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

RED = rg.RED
OUT = rg.ROOT / "viz" / "site"
OUT.mkdir(parents=True, exist_ok=True)
W = 5000
SIMPLIFY = 5000
ROBIN = "+proj=robin +lon_0=0 +datum=WGS84 +units=m +no_defs"
XMAX, YMAX = 17005833.0, 8625155.0
H = int(round(W * YMAX / XMAX))
# The unit of analysis: a HydroSHEDS level, or "aq" for the WHYMAP
# hydrogeological units. Outputs are tagged with it so the two never overwrite
# each other, and every script downstream reads the same tag.
LEVEL = sys.argv[1] if len(sys.argv) > 1 else "06"
TAG = "aquifer" if LEVEL in ("aq", "aquifer", "aquifers") else f"level{LEVEL}"

REGION = {1: "Africa", 2: "Europe and Middle East", 3: "Siberia",
          4: "Central and SE Asia", 5: "Australia and Oceania",
          6: "South America", 7: "North America", 8: "North American Arctic",
          9: "Greenland"}

flags = pd.read_parquet(RED / f"{TAG}_red_flags.parquet")
summ = json.load(open(RED / f"{TAG}_red_summary.json"))
geo_summ = json.load(open(RED / f"{TAG}_geometry_summary.json"))
sources = json.load(open(RED / f"{TAG}_sources.json"))

basins = rg.load_basins(LEVEL)
assert (basins["HYBAS_ID"].to_numpy() == flags["HYBAS_ID"].to_numpy()).all()
proj = basins.to_crs(ROBIN)
proj["geometry"] = proj.geometry.simplify(SIMPLIFY, preserve_topology=True)
cent = basins.geometry.representative_point()


def to_path(geom):
    parts = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    out = []
    for poly in parts:
        for ring in [poly.exterior, *poly.interiors]:
            xs, ys = ring.coords.xy
            px = np.round((np.asarray(xs) + XMAX) / (2 * XMAX) * W).astype(int)
            py = np.round((YMAX - np.asarray(ys)) / (2 * YMAX) * H).astype(int)
            pts = list(dict.fromkeys(zip(px.tolist(), py.tolist())))
            if len(pts) < 3:
                continue
            out.append("M" + "L".join(f"{a} {b}" for a, b in pts) + "Z")
    return "".join(out)


paths = [to_path(g) for g in proj.geometry]


def arr(col, nd=5):
    if col not in flags.columns:
        return None
    v = flags[col].to_numpy(dtype="float64")
    return [None if not np.isfinite(x) else round(float(x), nd) for x in v]


def iarr(col):
    if col not in flags.columns:
        return None
    v = flags[col].to_numpy(dtype="float64")
    return [None if not np.isfinite(x) else int(x) for x in v]


hyb = flags["HYBAS_ID"].to_numpy(dtype="int64")


def region_of():
    """A readable region per unit.

    HydroBASINS encodes its region in the first digit of the id. WHYMAP carries
    a continent field instead, so the unit that has one is asked directly rather
    than having a region inferred from an id that does not hold one.
    """
    if "region" in flags.columns:
        return flags["region"].astype(str).tolist()
    return [REGION.get(int(x) // 1000000000, "?") for x in hyb]

payload = {
    "width": W, "height": H,
    "meta": {
        "unit": TAG,
        "level": LEVEL,
        "common_period": summ["common_period"],
        "n_months": summ["n_months"],
        "n_months_with_predictors": summ["n_months_with_predictors"],
        "n_basins": summ["n_basins"],
        "n_tested": summ["n_tested"],
        "config": summ["config"],
        "spearman": summ["spearman"],
        "medians": summ["medians"],
        "geometry": geo_summ,
        "sources": sources,
        "flag_counts": summ["flags"],
        "area": summ["area"],
    },
    "sens": summ["sensitivity"],
    "corners": summ.get("sensitivity_corners"),
    "d": paths,
    "id": [int(x) for x in hyb],
    "reg": region_of(),
    "grp": (flags["aq_group"].tolist() if "aq_group" in flags.columns else None),
    "rch": (flags["aq_recharge"].tolist() if "aq_recharge" in flags.columns else None),
    "lon": [round(float(p.x), 2) for p in cent],
    "lat": [round(float(p.y), 2) for p in cent],
    "area": [int(round(float(a))) for a in flags["SUB_AREA"].to_numpy()],
    "tested": [1 if b else 0 for b in flags["usable"].to_numpy()],
    "ncG": iarr("n_cells_G"), "ncL": iarr("n_cells_L"),
    "nfp": iarr("n_native_footprints"), "nfp5": iarr("n_native_footprints_5pct"),
    # The page recomputes the flags from these, so anything a threshold is
    # compared against keeps five decimals. Rounding to three moved the headline
    # count by 22 basins, all of them sitting exactly on a cut.
    "fdom": arr("frac_dominant_mascon"),
    "vrG": arr("var_ratio_G"), "vrL": arr("var_ratio_L"), "vrS": arr("var_ratio_solution", 3),
    "vrRel": arr("var_ratio_release", 5),
    "prG": arr("pred_r2_G"), "prL": arr("pred_r2_L"),
    "prGe": arr("pred_r2_eff_G", 3), "prLe": arr("pred_r2_eff_L", 3),
    "rGL": arr("r_GL"), "rGC": arr("r_GC", 3), "rLC": arr("r_LC", 3),
    # Trends for all four solutions, so the page can draw the same storage rate
    # map the first tab draws and then show what moves when the solution
    # changes rather than when the water does.
    "tG": arr("trend_G", 2), "tL": arr("trend_L", 2),
    "tC": arr("trend_coarse", 2), "tC2": arr("trend_coarse_gsfc", 2),
    "tC61": arr("trend_coarse_rl0601", 2), "pC61": arr("p_coarse_rl0601", 4),
    "pG": arr("p_G", 4), "pL": arr("p_L", 4), "pC": arr("p_coarse", 4),
    "tdr": arr("trend_diff_ratio"),
    "rkG": arr("rank_G", 1), "rkL": arr("rank_L", 1), "rkC": arr("rank_coarse", 1),
    "shift": arr("rank_shift", 4),
}

txt = f"window.RED_{TAG}=" + json.dumps(payload, separators=(",", ":")) + ";\n"
(OUT / f"red_data_{TAG}.js").write_text(txt, encoding="utf-8")
print(f"wrote {OUT/f'red_data_{TAG}.js'} {len(txt)/1e6:.2f} MB, {len(paths)} basins, "
      f"map {W}x{H}")
