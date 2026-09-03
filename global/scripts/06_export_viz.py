"""Export everything the interactive page needs into one JSON payload.

Basin polygons are projected to Robinson in Python and written as integer pixel
coordinates, so the page needs no projection library and the geometry compresses
to a fraction of what GeoJSON degrees would cost.

Series are stored as tenths of a millimetre in integers, with null for the two
months GRACE did not solve inside the window, so the page can break the line at
a gap instead of drawing through it.
"""

import glob
import json
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
from gsfc_grid import ICE, cell_to_mascon, load_geometry, terrestrial  # noqa: E402

ROOT = Path(r"E:\Water\Global")
RES = 0.1
W = 10000                      # Robinson pixel width; 1 unit ~ 3.4 km
ROBIN = "+proj=robin +lon_0=0 +datum=WGS84 +units=m +no_defs"
XMAX, YMAX = 17005833.0, 8625155.0
H = int(round(W * YMAX / XMAX))
SIMPLIFY = {"03": 8000, "04": 4000}

# HydroBASINS encodes its region in the first digit of HYBAS_ID.
REGION = {1: "Africa", 2: "Europe", 3: "Siberia", 4: "Asia", 5: "Australasia",
          6: "South America", 7: "North America", 8: "Arctic", 9: "Greenland"}

geo = load_geometry()
land = terrestrial(geo)
is_ice = geo["location"].isin(ICE).to_numpy()

tws = pd.read_parquet(ROOT / "processed" / "tws_anomaly_mm_land.parquet")
gws = pd.read_parquet(ROOT / "processed" / "gws_anomaly_mm_land.parquet")
tws.columns = [int(c) for c in tws.columns]
gws.columns = [int(c) for c in gws.columns]
months = pd.period_range(tws.index.min().to_period("M"), tws.index.max().to_period("M"), freq="M")
month_labels = [str(p) for p in months]
have = pd.DatetimeIndex([p.to_timestamp() for p in months])
print(f"{len(months)} calendar months, {len(tws)} solved")

lat = np.arange(-90 + RES / 2, 90, RES)
lon = np.arange(-180 + RES / 2, 180, RES)
mapping = cell_to_mascon(geo, lat, lon)
LON, LAT = np.meshgrid(lon, lat)
keep = land[mapping]
cells = gpd.GeoDataFrame(
    {"mascon_id": mapping[keep].astype(np.int64), "w": np.cos(np.deg2rad(LAT[keep]))},
    geometry=gpd.points_from_xy(LON[keep], LAT[keep]), crs="EPSG:4326")


def to_path(geom):
    """SVG path in integer Robinson pixel space, holes included."""
    parts = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    out = []
    for poly in parts:
        for ring in [poly.exterior, *poly.interiors]:
            xs, ys = ring.coords.xy
            px = np.round((np.asarray(xs) + XMAX) / (2 * XMAX) * W).astype(int)
            py = np.round((YMAX - np.asarray(ys)) / (2 * YMAX) * H).astype(int)
            pts = [(int(a), int(b)) for a, b in zip(px, py)]
            dedup = [pts[0]]
            for p in pts[1:]:
                if p != dedup[-1]:
                    dedup.append(p)
            if len(dedup) < 3:
                continue
            out.append("M" + "L".join(f"{a} {b}" for a, b in dedup) + "Z")
    return "".join(out)


def series_int(s):
    v = s.reindex(have)
    return [None if not np.isfinite(x) else int(round(x * 10)) for x in v.to_numpy()]


payload = {"months": month_labels, "width": W, "height": H, "levels": {}}

for level in ("03", "04"):
    src = sorted(glob.glob(str(ROOT / "raw" / "hydrobasins" / f"*lev{level}*.shp")))
    basins = pd.concat([gpd.read_file(p) for p in src], ignore_index=True)
    basins = gpd.GeoDataFrame(basins, geometry="geometry", crs="EPSG:4326")
    basins["basin_idx"] = np.arange(len(basins))
    tr = pd.read_csv(ROOT / "trends" / f"basins_lev{level}_trends.csv").set_index("basin_idx")

    joined = gpd.sjoin(cells, basins[["basin_idx", "geometry"]], how="inner", predicate="within")
    wmat = joined.groupby(["basin_idx", "mascon_id"])["w"].sum().reset_index()

    proj = basins.to_crs(ROBIN)
    proj["geometry"] = proj["geometry"].simplify(SIMPLIFY[level], preserve_topology=True)
    cent = basins.geometry.representative_point()

    rows, npts = [], 0
    for bi, g in wmat.groupby("basin_idx"):
        if bi not in tr.index or not np.isfinite(tr.loc[bi, "tws_trend_mm_yr"]):
            continue
        ids = g["mascon_id"].to_numpy()
        w = g["w"].to_numpy()
        sel = np.array([i in tws.columns for i in ids])
        ids, w = ids[sel], w[sel]
        if not len(ids):
            continue
        t = (tws[ids] * (w / w.sum())).sum(axis=1)

        gv = gws[ids]
        ok = np.isfinite(gv.to_numpy()).all(axis=0)
        row = tr.loc[bi]
        gser = None
        if ok.any() and np.isfinite(row.get("gws_trend_mm_yr", np.nan)):
            gser = series_int((gv.loc[:, gv.columns[ok]] * (w[ok] / w[ok].sum())).sum(axis=1))

        d = to_path(proj.geometry.iloc[bi])
        npts += d.count("L")
        hid = int(basins.HYBAS_ID.iloc[bi])
        rows.append({
            "id": hid,
            "region": REGION.get(hid // 1000000000, "?"),
            "lon": round(float(cent.iloc[bi].x), 2),
            "lat": round(float(cent.iloc[bi].y), 2),
            "area": int(round(float(basins.SUB_AREA.iloc[bi]))),
            "nm": int(row["n_mascons"]),
            "ice": round(float(row.get("ice_fraction", 0) or 0), 3),
            "tt": round(float(row["tws_trend_mm_yr"]), 2),
            "tp": round(float(row["tws_p"]), 4),
            "gt": None if not np.isfinite(row.get("gws_trend_mm_yr", np.nan)) else round(float(row["gws_trend_mm_yr"]), 2),
            "gp": None if not np.isfinite(row.get("gws_p", np.nan)) else round(float(row["gws_p"]), 4),
            "sp": None if not np.isfinite(row.get("gws_model_spread_mm_yr", np.nan)) else round(float(row["gws_model_spread_mm_yr"]), 2),
            "d": d,
            "t": series_int(t),
            "g": gser,
        })

    # area-weighted global mean of everything on this level, for context
    aw = np.array([r["area"] for r in rows], dtype=float)
    def global_mean(key):
        M = np.array([[np.nan if v is None else v / 10 for v in r[key]] for r in rows
                      if r[key] is not None], dtype=float)
        wts = np.array([r["area"] for r in rows if r[key] is not None], dtype=float)
        num = np.nansum(M * wts[:, None], axis=0)
        den = np.nansum(np.isfinite(M) * wts[:, None], axis=0)
        return [None if d == 0 else round(float(n / d) * 10) for n, d in zip(num, den)]

    payload["levels"][level] = {
        "basins": rows,
        "global_t": global_mean("t"),
        "global_g": global_mean("g"),
    }
    print(f"level {level}: {len(rows)} basins, {npts:,} path vertices")

out = ROOT / "viz" / "grace_basins.json"
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
print(f"wrote {out} ({out.stat().st_size/1e6:.1f} MB)")
