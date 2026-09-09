"""Basin geometry and area-weighted aggregation for the red experiment.

Every product in this experiment sits on a different regular grid: 0.5 degrees
for GRACE-SeDA and for the JPL mascon grid, 0.25 degrees for Li and Kusche and
for GLDAS-Noah, 0.05 degrees for CHIRPS. Rather than regrid each product onto
each other, the basins are rasterized once at 0.05 degrees and every coarser
grid inherits its overlap from that raster.

Why this counts as conservative regridding. A basin mean here is

    sum_c ( value_c * area of cell c inside the basin )
    -------------------------------------------------
    sum_c ( area of cell c inside the basin )

which is the exact area-weighted average a first-order conservative remap
produces, up to the 0.05 degree quantization of the overlap areas. Nearest
neighbour and bilinear do not conserve mass and are not used anywhere.

The 0.05 degree master grid divides every product grid used here exactly:
0.5 / 0.05 = 10, 0.25 / 0.05 = 5, and CHIRPS is that grid.
"""

from __future__ import annotations

import glob
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd

ROOT = Path(r"E:\Water\Global")
RAW = ROOT / "raw"
RED = ROOT / "red"
MASTER_RES = 0.05
EARTH_R_KM = 6371.0088

# Master cell centers. Latitude ascends so that a product grid stored either
# way can be flipped to match with a single slice.
MLAT = np.arange(-90 + MASTER_RES / 2, 90, MASTER_RES)
MLON = np.arange(-180 + MASTER_RES / 2, 180, MASTER_RES)


def level_paths(level: str = "06") -> list[str]:
    return sorted(glob.glob(str(RAW / "hydrobasins" / f"*lev{level}*.shp")))


def load_basins(level: str = "06") -> gpd.GeoDataFrame:
    """Every HydroBASINS region at one level, concatenated, with a dense index."""
    parts = [gpd.read_file(p) for p in level_paths(level)]
    b = pd.concat(parts, ignore_index=True)
    b = gpd.GeoDataFrame(b, geometry="geometry", crs="EPSG:4326")
    b["basin_idx"] = np.arange(len(b), dtype=np.int32)
    return b


def cell_area_km2() -> np.ndarray:
    """Area of one master cell in each latitude row, in square kilometers."""
    half = np.deg2rad(MASTER_RES / 2)
    lat = np.deg2rad(MLAT)
    return (EARTH_R_KM ** 2) * np.deg2rad(MASTER_RES) * (np.sin(lat + half) - np.sin(lat - half))


def basin_raster(level: str = "06", cache: Path | None = None) -> np.ndarray:
    """(nlat, nlon) int32 basin_idx per master cell, -1 outside every basin.

    Rasterized by cell center, so a cell belongs to exactly one basin. That
    matches how HydroBASINS tiles the land: the polygons do not overlap and
    together cover it, so center assignment loses only sub-cell coastline.
    """
    cache = cache or (RED / f"basin_raster_lev{level}.npy")
    if cache.exists():
        return np.load(cache)
    from rasterio.features import rasterize
    from rasterio.transform import from_origin

    b = load_basins(level)
    # rasterio writes north-up, so build it that way and flip at the end.
    tr = from_origin(-180.0, 90.0, MASTER_RES, MASTER_RES)
    out = rasterize(
        ((geom, int(idx)) for geom, idx in zip(b.geometry, b.basin_idx)),
        out_shape=(len(MLAT), len(MLON)),
        transform=tr,
        fill=-1,
        dtype="int32",
        all_touched=False,
    )
    out = out[::-1].copy()          # north-up to latitude-ascending
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.save(cache, out)
    return out


def master_index(lat: np.ndarray, lon: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Master row and column containing each point, by floor rather than nearest.

    A 0.5 degree cell center such as 0.25 lands exactly on a master cell edge,
    so nearest-cell rounding would be decided by floating point. Flooring is
    arbitrary too, but it is arbitrary the same way every time.
    """
    jy = np.clip(np.floor((np.asarray(lat, dtype="float64") + 90.0) / MASTER_RES).astype(np.int64),
                 0, len(MLAT) - 1)
    lon180 = ((np.asarray(lon, dtype="float64") + 180.0) % 360.0)
    jx = np.clip(np.floor(lon180 / MASTER_RES).astype(np.int64), 0, len(MLON) - 1)
    return jy, jx


class GridWeights:
    """Overlap between one regular product grid and every basin.

    One row per (basin, product cell) that actually overlap, so the table stays
    small: tens of thousands of rows at 0.5 degrees, a few hundred thousand at
    0.25, against 16,000 basins times a million cells if it were dense.
    """

    def __init__(self, basin_of: np.ndarray, lat: np.ndarray, lon: np.ndarray, n_basins: int):
        self.lat = np.asarray(lat, dtype="float64")
        self.lon = np.asarray(lon, dtype="float64")
        self.n_basins = int(n_basins)
        self.nlat, self.nlon = len(self.lat), len(self.lon)
        # CHIRPS stores its coordinates as float32, so 0.05 arrives as
        # 0.049999237. Rounding to six decimals recovers the intended grid;
        # keeping the raw value would drift a whole cell across 7,200 columns.
        self.res_lat = round(abs(float(self.lat[-1] - self.lat[0])) / (len(self.lat) - 1), 6)
        self.res_lon = round(abs(float(self.lon[-1] - self.lon[0])) / (len(self.lon) - 1), 6)
        self._build(basin_of)

    def _build(self, basin_of: np.ndarray) -> None:
        fy, fx = self.res_lat / MASTER_RES, self.res_lon / MASTER_RES
        if abs(fy - round(fy)) > 1e-6 or abs(fx - round(fx)) > 1e-6:
            raise ValueError(f"grid {self.res_lat}x{self.res_lon} is not a multiple of {MASTER_RES}")

        # Locate product cells by their own edges rather than assuming the two
        # grids share an origin.
        lat0 = round(float(self.lat.min()) - self.res_lat / 2, 6)
        lon0 = round(float(self.lon.min()) - self.res_lon / 2, 6)
        iy = np.floor((MLAT - lat0) / self.res_lat).astype(np.int64)
        ok_y = (iy >= 0) & (iy < self.nlat)
        ix = np.floor(np.mod(MLON - lon0, 360.0) / self.res_lon).astype(np.int64)
        ix = np.clip(ix, 0, self.nlon - 1)

        if self.lat[0] > self.lat[-1]:              # product rows run north-down
            iy = self.nlat - 1 - iy
        if self.lon[0] > self.lon[-1]:
            ix = self.nlon - 1 - ix

        area = cell_area_km2()
        n_cells = self.nlat * self.nlon
        rows_key, rows_w = [], []
        for j in np.where(ok_y)[0]:
            row = basin_of[j]
            m = row >= 0
            if not m.any():
                continue
            key = row[m].astype(np.int64) * n_cells + (iy[j] * self.nlon + ix[m])
            rows_key.append(key)
            rows_w.append(np.full(int(m.sum()), area[j], dtype="float64"))
        key = np.concatenate(rows_key)
        ww = np.concatenate(rows_w)
        order = np.argsort(key, kind="stable")
        key, ww = key[order], ww[order]
        uk, start = np.unique(key, return_index=True)
        self.basin = (uk // n_cells).astype(np.int32)
        self.cell = (uk % n_cells).astype(np.int64)
        self.weight = np.add.reduceat(ww, start)
        self.basin_area_km2 = np.bincount(self.basin, weights=self.weight,
                                          minlength=self.n_basins)

    def means(self, values: np.ndarray) -> np.ndarray:
        """(n_time, n_basins) area-weighted basin means of a (n_time, nlat, nlon) cube.

        Cells that are NaN in a given month drop out of both the numerator and
        the denominator, so a partly covered basin is renormalized rather than
        scored as zero over the part that did not report.
        """
        nt = values.shape[0]
        out = np.full((nt, self.n_basins), np.nan)
        for t in range(nt):
            v = values[t].reshape(-1)[self.cell]
            ok = np.isfinite(v)
            num = np.bincount(self.basin, weights=np.where(ok, v, 0.0) * self.weight,
                              minlength=self.n_basins)
            den = np.bincount(self.basin, weights=self.weight * ok, minlength=self.n_basins)
            np.divide(num, den, out=out[t], where=den > 0)
        return out

    def coverage(self, valid_2d: np.ndarray) -> np.ndarray:
        """Share of each basin's area whose product cell is valid at all."""
        ok = valid_2d.reshape(-1)[self.cell].astype("float64")
        got = np.bincount(self.basin, weights=self.weight * ok, minlength=self.n_basins)
        return np.divide(got, self.basin_area_km2, out=np.zeros_like(got),
                         where=self.basin_area_km2 > 0)

    def n_cells_centroid(self, basins: "gpd.GeoDataFrame") -> np.ndarray:
        """Product cells whose own center falls inside each basin.

        This is the count the geometry test uses, and it is deliberately not
        the number of cells that touch the basin: a cell clipped by a basin
        edge describes its neighbours as much as it describes this basin.

        Point in polygon against the outlines, not a lookup in the 0.05 degree
        raster. A 0.5 degree cell center such as 0.25 sits exactly on a raster
        cell edge, so the raster answer is decided by a tie-break and differs
        from the true count for about a third of basins, almost always by one.
        The threshold this number feeds is two.
        """
        lon = ((self.lon + 180.0) % 360.0) - 180.0
        LON, LAT = np.meshgrid(lon, self.lat)
        pts = gpd.GeoDataFrame(
            geometry=gpd.points_from_xy(LON.ravel(), LAT.ravel()), crs="EPSG:4326")
        hit = gpd.sjoin(pts, basins[["basin_idx", "geometry"]], how="inner",
                        predicate="within")
        return np.bincount(hit["basin_idx"].to_numpy(dtype=np.int64),
                           minlength=self.n_basins)
