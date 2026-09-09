"""Export the green experiment for the site tab.

Wells go out as Robinson pixel coordinates rather than degrees, so the page
needs no projection code, and the level 3 basin outlines come along at heavy
simplification purely as a backdrop. The scores travel per well because the
point of the page is that a reader can see where the answer holds and where
there is simply nothing to test against.
"""

import json
import sys

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

GREEN = rg.ROOT / "green"
OUT = rg.ROOT / "viz" / "site"
W = 3000
SIMPLIFY = 22000
ROBIN = "+proj=robin +lon_0=0 +datum=WGS84 +units=m +no_defs"
XMAX, YMAX = 17005833.0, 8625155.0
H = int(round(W * YMAX / XMAX))

# One byte per well instead of a repeated 33-character string, which is two
# megabytes of payload for nothing.
AQ_NAMES = ["Major groundwater basin", "Complex hydrogeological structure",
            "Local and shallow aquifer"]
AQ_CODE = {n: i for i, n in enumerate(AQ_NAMES)}

summary = json.load(open(GREEN / "green_summary.json"))
sources = json.load(open(GREEN / "wells_sources.json"))
t = pd.read_parquet(GREEN / "well_scores.parquet")
blk = pd.read_parquet(GREEN / "mascon_oos_r2.parquet")

land = rg.load_basins("03").to_crs(ROBIN)
land["geometry"] = land.geometry.simplify(SIMPLIFY, preserve_topology=True)


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


paths = [to_path(g) for g in land.geometry]

p = gpd.GeoSeries(gpd.points_from_xy(t.lon, t.lat), crs="EPSG:4326").to_crs(ROBIN)
px = np.round((p.x.to_numpy() + XMAX) / (2 * XMAX) * W).astype(int)
py = np.round((YMAX - p.y.to_numpy()) / (2 * YMAX) * H).astype(int)


# Two decimals is all a correlation needs here: the page colours by it and
# prints it, and nothing recomputes a threshold from it.
def arr(col, nd=2):
    v = t[col].to_numpy(dtype="float64")
    return [None if not np.isfinite(x) else round(float(x), nd) for x in v]


payload = {
    "width": W, "height": H,
    "meta": {**summary, "sources": sources},
    "land": paths,
    "px": px.tolist(), "py": py.tolist(),
    "lat": [round(float(v), 2) for v in t.lat],
    "lon": [round(float(v), 2) for v in t.lon],
    "ny": [int(v) for v in t.n_years],
    # WHYMAP's class per well, so the page can ask whether the answer depends on
    # what kind of aquifer the well sits in. A catchment cannot say that.
    "aqg": ([AQ_CODE.get(v) for v in t["aq_group"]]
            if "aq_group" in t.columns else None),
    "aq_names": AQ_NAMES,
    "mas": [int(v) for v in t.mascon],
    "pr": [int(round(float(v))) if np.isfinite(v) else None for v in t.mean_precip_mm_yr],
    "rC": arr("r_jpl"), "rG": arr("r_seda"), "rL": arr("r_liku"),
    "dG": arr("dr_seda"), "dL": arr("dr_liku"),
    "blk": {c: [None if not np.isfinite(v) else round(float(v), 4)
                for v in blk[c].to_numpy()] for c in blk.columns},
    "blk_id": [int(v) for v in blk.index],
}
txt = "window.GREEN=" + json.dumps(payload, separators=(",", ":")) + ";\n"
(OUT / "wells_data.js").write_text(txt, encoding="utf-8")
print(f"wrote {OUT/'wells_data.js'} {len(txt)/1e6:.2f} MB, {len(px):,} wells, "
      f"{len(paths)} land shapes, map {W}x{H}")
