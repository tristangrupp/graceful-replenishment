"""Minimal GeoTIFF reading helpers.

There is no rasterio/GDAL python binding in the shared venv and that venv must
not be modified, so tifffile+imagecodecs were installed to a separate directory
under E:\\Water\\CentralValley\\tmp\\pylibs and are put on sys.path here.

Only what is needed: pixel array plus the affine geotransform and EPSG code,
read straight from the TIFF tags (ModelPixelScale 33550, ModelTiepoint 33922,
GeoKeyDirectory 34735).
"""
import sys
from pathlib import Path

PYLIBS = Path(r"E:\Water\CentralValley\tmp\pylibs")
if str(PYLIBS) not in sys.path:
    sys.path.append(str(PYLIBS))       # append: venv numpy must win

import numpy as np
import tifffile


def geotransform(page):
    tags = page.tags
    scale = tags["ModelPixelScaleTag"].value if "ModelPixelScaleTag" in tags else None
    tie = tags["ModelTiepointTag"].value if "ModelTiepointTag" in tags else None
    if scale is None or tie is None:
        raise ValueError("no ModelPixelScale/ModelTiepoint in TIFF")
    sx, sy = float(scale[0]), float(scale[1])
    i, j, _, x, y, _ = [float(v) for v in tie[:6]]
    # upper-left corner of pixel (0,0)
    x0 = x - i * sx
    y0 = y + j * sy
    return x0, sx, y0, sy


def epsg(page):
    tags = page.tags
    if "GeoKeyDirectoryTag" not in tags:
        return None
    keys = list(tags["GeoKeyDirectoryTag"].value)
    n = keys[3]
    for k in range(n):
        kid, loc, cnt, val = keys[4 + 4 * k: 8 + 4 * k]
        if kid in (2048, 3072) and loc == 0:      # Geographic/ProjectedCSType
            return int(val)
    return None


def read(path):
    """-> (array, x0, dx, y0, dy, epsg). array is (bands, ny, nx) or (ny, nx)."""
    with tifffile.TiffFile(path) as tf:
        page = tf.pages[0]
        arr = tf.asarray()
        gt = geotransform(page)
        code = epsg(page)
        nod = None
        if "GDAL_NODATA" in page.tags:
            nod = float(page.tags["GDAL_NODATA"].value)
    if arr.ndim == 3 and arr.shape[-1] < arr.shape[0]:
        arr = np.moveaxis(arr, -1, 0)          # (ny,nx,band) -> (band,ny,nx)
    return arr, gt[0], gt[1], gt[2], gt[3], code, nod


def cell_centres(x0, dx, y0, dy, nx, ny):
    xs = x0 + (np.arange(nx) + 0.5) * dx
    ys = y0 - (np.arange(ny) + 0.5) * dy
    return xs, ys
