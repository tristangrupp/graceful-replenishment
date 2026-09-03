import sys
import numpy as np
sys.path.insert(0, r"E:\Water\_shared")
from gsfc_grid import LAND, cell_to_mascon, load_geometry

geo = load_geometry()
print("mascons", len(geo), "| lon_center range", geo.lon_center.min(), geo.lon_center.max())
print("lat bands", geo.lat_center.nunique(), "| lon spans", sorted(geo.lon_span.unique())[:3], "...")

# every mascon's own centre must map back to itself
lat = geo.lat_center.to_numpy()
lon = geo.lon_center.to_numpy()
bands = np.sort(geo["lat_min"].unique())
bad = 0
for i in range(0, len(geo), 997):           # stride, not all 41k, for speed
    got = cell_to_mascon(geo, np.array([lat[i]]), np.array([lon[i]]))[0, 0]
    if got != geo.mascon_id.iloc[i]:
        bad += 1
        if bad < 5:
            print("MISMATCH", i, geo.mascon_id.iloc[i], got, lat[i], lon[i])
print("self-lookup mismatches:", bad, "of", len(range(0, len(geo), 997)))

# a 0.25 deg global grid must hit every mascon at least once and only real ids
la = np.arange(-89.875, 90, 0.25)
lo = np.arange(-179.875, 180, 0.25)
mp = cell_to_mascon(geo, la, lo)
print("grid", mp.shape, "unique mascons hit", len(np.unique(mp)), "of", len(geo))
print("id range", mp.min(), mp.max())
land = geo.location.to_numpy() == LAND
frac = np.average(land[mp], weights=np.broadcast_to(np.cos(np.deg2rad(la))[:, None], mp.shape))
print(f"land fraction of the sphere by this mapping: {frac:.3f} (truth ~0.29)")

# spot check: Riyadh 24.7N 46.7E must land on a Saudi land mascon
i = cell_to_mascon(geo, np.array([24.7]), np.array([46.7]))[0, 0]
r = geo.loc[i]
print(f"Riyadh -> mascon {i} centre {r.lat_center:.2f},{r.lon_180:.2f} "
      f"location {r.location} area {r.area_km2:.0f} km2")
