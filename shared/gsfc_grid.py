"""GSFC mascon geometry, and which mascon a lat/lon cell falls in.

Shared by the global scripts. GSFC mascons tile the sphere in latitude bands,
each band cut into equal-area cells whose longitude width grows toward the
poles, so locating a cell is two searchsorted steps: which band, then which
cell within that band.
"""

from pathlib import Path

import h5py
import numpy as np
import pandas as pd

H5 = Path(r"E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5")
LAND = 80.0          # GSFC location code for ice-free land
OCEAN = 90.0
# 1 = Greenland, 3 = Antarctica, 4 and 5 = ice caps and glacier systems.
# All of them are terrestrial mass that GRACE measures, so "not ocean" is
# the right filter for a storage map; "== 80" silently drops Greenland.
ICE = (1.0, 3.0, 4.0, 5.0)
CM_TO_MM = 10.0


def load_geometry(h5=H5) -> pd.DataFrame:
    with h5py.File(h5, "r") as f:
        m = f["mascon"]
        geo = pd.DataFrame({
            "lat_center": np.ravel(m["lat_center"][:]),
            "lon_center": np.ravel(m["lon_center"][:]),
            "lat_span": np.ravel(m["lat_span"][:]),
            "lon_span": np.ravel(m["lon_span"][:]),
            "area_km2": np.ravel(m["area_km2"][:]),
            "location": np.ravel(m["location"][:]),
        })
    geo["mascon_id"] = np.arange(len(geo))
    geo["lon_180"] = ((geo["lon_center"] + 180) % 360) - 180
    geo["lat_min"] = geo["lat_center"] - geo["lat_span"] / 2
    geo["lat_max"] = geo["lat_center"] + geo["lat_span"] / 2
    geo["lon_min"] = geo["lon_center"] - geo["lon_span"] / 2
    geo["lon_max"] = geo["lon_center"] + geo["lon_span"] / 2
    return geo


def load_series(h5=H5) -> tuple[pd.DataFrame, pd.DatetimeIndex]:
    """Monthly TWS in mm, one column per mascon."""
    with h5py.File(h5, "r") as f:
        cmwe = f["solution/cmwe"][:]
        ymd = f["time/yyyy_doy_yrplot_middle"][:]
    times = (pd.to_datetime([f"{int(y)}-01-01" for y in ymd[0]])
             + pd.to_timedelta(ymd[1].astype(int) - 1, unit="D"))
    df = pd.DataFrame(cmwe.T * CM_TO_MM, index=pd.DatetimeIndex(times))
    # GRACE occasionally carries two sub-monthly solutions in one calendar
    # month; average rather than let one overwrite the other.
    return df.groupby(df.index.to_period("M").to_timestamp()).mean()


def cell_to_mascon(geo: pd.DataFrame, lat: np.ndarray, lon: np.ndarray) -> np.ndarray:
    """(nlat, nlon) int32 of mascon_id for each cell centre of a regular grid."""
    lon360 = np.mod(np.asarray(lon, dtype="float64"), 360.0)
    bands = np.sort(geo["lat_min"].unique())
    band_of_lat = np.clip(np.searchsorted(bands, lat, side="right") - 1, 0, len(bands) - 1)

    by_band = {}
    for b, sub in geo.groupby("lat_min"):
        s = sub.sort_values("lon_min")
        by_band[b] = (s["lon_min"].to_numpy(), s["mascon_id"].to_numpy())

    out = np.empty((len(lat), len(lon)), dtype=np.int32)
    for i, bi in enumerate(band_of_lat):
        edges, ids = by_band[bands[bi]]
        j = np.clip(np.searchsorted(edges, lon360, side="right") - 1, 0, len(ids) - 1)
        out[i] = ids[j]
    return out


def terrestrial(geo) -> "np.ndarray":
    """Boolean mask of every mascon that is not ocean, ice sheets included."""
    return geo["location"].to_numpy() != OCEAN
