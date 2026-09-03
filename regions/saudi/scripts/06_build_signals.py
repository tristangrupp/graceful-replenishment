"""Build the clean per-mascon monthly signal product for the Arabian Peninsula.

Primary source is the NATIVE GSFC product (1-arc-degree equal-area mascons,
gsfc...obp-ice6gd.h5), not the half-degree netCDF: reconnaissance showed every
half-degree LAND cell in the region carries a unique time series, i.e. the
half-degree grid is interpolated from the mascons and does not preserve mascon
identity. The native file also carries per-mascon noise and leakage
uncertainties that the half-degree netCDF drops.
"""
import json
from pathlib import Path

import geopandas as gpd
import h5py
import numpy as np
import pandas as pd
import xarray as xr
from shapely.geometry import box as shp_box
from shapely.ops import unary_union
import cartopy.io.shapereader as shpreader

ROOT = Path(r"E:\Water\Saudi")
H5 = ROOT / "raw" / "gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5"
SIG = ROOT / "signals"; PROC = ROOT / "processed"
for d in (SIG, PROC):
    d.mkdir(parents=True, exist_ok=True)

# Analysis box (brief): lat 12-32N, lon 34-60E.
LAT0, LAT1, LON0, LON1 = 12.0, 32.0, 34.0, 60.0
PENINSULA = {"Saudi Arabia", "Yemen", "Oman", "United Arab Emirates",
             "Qatar", "Bahrain", "Kuwait"}

# ---------------------------------------------------------------- read native
f = h5py.File(H5, "r")
g = lambda k: np.asarray(f[k][()]).squeeze()

lat_c, lon_c = g("mascon/lat_center"), g("mascon/lon_center")
lat_sp, lon_sp = g("mascon/lat_span"), g("mascon/lon_span")
area_km2 = g("mascon/area_km2")
labels = g("mascon/labels").astype(int)
location = g("mascon/location").astype(int)
basin = g("mascon/basin").astype(int)

lon180 = ((lon_c + 180) % 360) - 180
in_box = (lat_c >= LAT0) & (lat_c <= LAT1) & (lon180 >= LON0) & (lon180 <= LON1)
sel = np.where(in_box & (location == 80))[0]           # land mascons only
print(f"land mascons with centre in box: {len(sel)}")

cmwe = f["solution/cmwe"][sel, :]                       # (n_mascon, n_time)
noise2 = f["uncertainty/noise_2sigma"][sel, :]
leak2 = np.asarray(f["uncertainty/leakage_2sigma"][()]).squeeze()[sel]
leak_tr = np.asarray(f["uncertainty/leakage_trend"][()]).squeeze()[sel]

rd_first = g("time/ref_days_first"); rd_mid = g("time/ref_days_middle")
rd_last = g("time/ref_days_last"); n_days = g("time/n_ref_days_solution")
f.close()

EPOCH = pd.Timestamp("2002-01-01")          # "days since Jan 0, 2002" -> day 1 = Jan 1
t_mid = EPOCH + pd.to_timedelta(rd_mid - 1, "D")
t_first = EPOCH + pd.to_timedelta(rd_first - 1, "D")
t_last = EPOCH + pd.to_timedelta(rd_last - 1, "D")
per = pd.PeriodIndex(t_mid, freq="M")

# ------------------------------------------- collapse sub-monthly duplicates
# 2018-11 holds two solutions (windows 2018-10-22..11-09 and 11-10..11-30).
# Average them weighted by the number of L1B days each used, so we get one
# value per calendar month rather than a duplicated month label. Noise is
# combined as the same weighted mean (NOT reduced by sqrt(n)): the two
# sub-monthly solutions share systematic error, so claiming error reduction
# would be unjustified.
dfm = pd.DataFrame({"per": per, "w": n_days, "i": np.arange(len(per))})
groups = dfm.groupby("per", sort=True)
months = pd.PeriodIndex([p for p, _ in groups], freq="M")
n_merged = int((groups.size() > 1).sum())
print(f"solutions={len(per)} -> distinct months={len(months)} (merged {n_merged})")

def collapse(arr):
    out = np.empty((arr.shape[0], len(months)))
    for j, (_, gdf) in enumerate(groups):
        idx = gdf["i"].to_numpy(); w = np.array(gdf["w"], dtype=float); w = w / w.sum()
        out[:, j] = arr[:, idx] @ w
    return out

cmwe_m = collapse(cmwe)
noise_m = collapse(noise2)
mid_m = pd.to_datetime([groups.get_group(p)["i"].pipe(lambda s: t_mid[s.to_numpy()].mean()) for p in months])
first_m = pd.to_datetime([t_first[groups.get_group(p)["i"].to_numpy()].min() for p in months])
last_m = pd.to_datetime([t_last[groups.get_group(p)["i"].to_numpy()].max() for p in months])
ndays_m = np.array([n_days[groups.get_group(p)["i"].to_numpy()].sum() for p in months])

# ---------------------------------------------- gap-aware complete month axis
full = pd.period_range(months.min(), months.max(), freq="M")
pos = {p: k for k, p in enumerate(months)}
present = np.array([p in pos for p in full])
take = np.array([pos.get(p, -1) for p in full])
n_mas = len(sel)

def expand(arr2d):
    out = np.full((n_mas, len(full)), np.nan)
    out[:, present] = arr2d[:, take[present]]
    return out

CM = expand(cmwe_m); NZ = expand(noise_m)
mid_full = pd.Series(pd.NaT, index=range(len(full)))
mid_full[present] = mid_m[take[present]]
mid_full = pd.to_datetime(mid_full.to_numpy())
missing = [str(p) for p in full[~present]]
print(f"full monthly axis {full[0]}..{full[-1]} n={len(full)}; observed={present.sum()}; missing={len(missing)}")

# decimal year at the actual solution midpoint (NOT month centre) where observed
dec_year = np.full(len(full), np.nan)
obs_dt = mid_full[present]
dec_year[present] = obs_dt.year + (obs_dt.dayofyear - 1) / np.where(obs_dt.is_leap_year, 366, 365)
# for unobserved months use the month midpoint so plotting/regridding still works
mp = full.to_timestamp(how="start") + (full.to_timestamp(how="end") - full.to_timestamp(how="start")) / 2
dec_year_axis = mp.year + (mp.dayofyear - 1) / np.where(mp.is_leap_year, 366, 365)

# ------------------------------------------------------- mission segmentation
gap_days = np.diff(mid_full[present].astype("int64")) / 86400e9
gi = int(np.argmax(gap_days))
gap_start, gap_end = mid_full[present][gi], mid_full[present][gi + 1]
print(f"largest gap: {gap_start.date()} -> {gap_end.date()} ({gap_days[gi]:.0f} d)")
mission = np.where(mid_full <= gap_start, "GRACE", "GRACE-FO").astype(object)
mission[~present] = np.where(mp[~present] <= gap_start, "GRACE", "GRACE-FO")

# ------------------------------------------------------------ geography
land_shp = shpreader.natural_earth("10m", "physical", "land")
ctry_shp = shpreader.natural_earth("10m", "cultural", "admin_0_countries")
land_g = gpd.read_file(land_shp)
ctry = gpd.read_file(ctry_shp)
name_col = "NAME_EN" if "NAME_EN" in ctry.columns else "NAME"
clip = shp_box(LON0 - 3, LAT0 - 3, LON1 + 3, LAT1 + 3)
land_u = unary_union(land_g.geometry.values).intersection(clip)
pen_u = unary_union(ctry[ctry[name_col].isin(PENINSULA)].geometry.values)

rects, frac_land, frac_pen, country = [], [], [], []
for k in sel:
    w = lon_sp[k] / 2; h = lat_sp[k] / 2
    r = shp_box(lon180[k] - w, lat_c[k] - h, lon180[k] + w, lat_c[k] + h)
    rects.append(r)
    frac_land.append(r.intersection(land_u).area / r.area)
    frac_pen.append(r.intersection(pen_u).area / r.area)
gm = gpd.GeoDataFrame({"i": np.arange(len(sel))},
                      geometry=gpd.points_from_xy(lon180[sel], lat_c[sel]), crs="EPSG:4326")
j = gpd.sjoin(gm, ctry[[name_col, "geometry"]], predicate="within", how="left")
j = j.drop_duplicates("i").set_index("i")
country = j[name_col].reindex(range(len(sel))).fillna("(offshore/unassigned)").to_numpy()

frac_land = np.array(frac_land); frac_pen = np.array(frac_pen)
on_pen = frac_pen > 0.5
print(f"mascons with >50% area on the Arabian Peninsula: {on_pen.sum()} / {len(sel)}")
print("country breakdown:", pd.Series(country).value_counts().to_dict())

# --------------------------------------------------- noise vs signal variance
sig_var = np.nanvar(CM, axis=1)
noise_var = np.nanmean((NZ / 2.0) ** 2, axis=1)      # 2-sigma -> sigma
snr_var = (sig_var - noise_var) / noise_var

# ------------------------------------------------------------ dS/dt (flux)
# Centred difference across observed neighbours, only when both are within 45
# days of the target month -- so no derivative is manufactured across the
# 11-month mission gap or any other missing month.
dt_days = np.full(len(full), np.nan)
DS = np.full_like(CM, np.nan)
t_ns = mid_full.astype("int64").astype(float)
for k in range(1, len(full) - 1):
    if not (present[k - 1] and present[k + 1]):
        continue
    dtm = (t_ns[k + 1] - t_ns[k - 1]) / 86400e9
    if dtm > 80:                       # >~2.6 months apart -> refuse
        continue
    dt_days[k] = dtm
    DS[:, k] = (CM[:, k + 1] - CM[:, k - 1]) / (dtm / 365.25)

# ------------------------------------------------------------ write outputs
mascon_id = labels[sel]
meta = pd.DataFrame({
    "mascon_id": mascon_id,
    "lat_center": lat_c[sel], "lon_center": lon180[sel], "lon_center_0_360": lon_c[sel],
    "lat_span_deg": lat_sp[sel], "lon_span_deg": lon_sp[sel], "area_km2": area_km2[sel],
    "gsfc_location_code": location[sel], "gsfc_basin_code": basin[sel],
    "country_of_center": country,
    "frac_area_land": frac_land, "frac_area_arabian_peninsula": frac_pen,
    "on_arabian_peninsula": on_pen,
    "leakage_2sigma_cm": leak2, "leakage_trend_uncert_cm_per_yr": leak_tr,
    "mean_noise_2sigma_cm": np.nanmean(NZ, axis=1),
    "series_std_cm": np.nanstd(CM, axis=1),
    "signal_variance_cm2": sig_var, "noise_variance_cm2": noise_var,
    "variance_snr": snr_var,
    "n_months_observed": np.isfinite(CM).sum(axis=1),
})
meta.to_csv(SIG / "mascon_metadata.csv", index=False)

month_str = np.array([str(p) for p in full])
wide = pd.DataFrame(CM.T, index=pd.Index(month_str, name="month"),
                    columns=[f"m{ i }" for i in mascon_id])
wide.to_csv(SIG / "mascon_monthly_cmwe_wide.csv")
pd.DataFrame(NZ.T, index=pd.Index(month_str, name="month"),
             columns=[f"m{i}" for i in mascon_id]).to_csv(SIG / "mascon_monthly_noise2sigma_wide.csv")

long = pd.DataFrame({
    "mascon_id": np.repeat(mascon_id, len(full)),
    "month": np.tile(month_str, n_mas),
    "solution_mid_date": np.tile(mid_full.to_numpy(), n_mas),
    "decimal_year": np.tile(np.where(present, dec_year, dec_year_axis), n_mas),
    "observed": np.tile(present, n_mas),
    "mission": np.tile(mission.astype(str), n_mas),
    "lwe_cm": CM.reshape(-1),
    "noise_2sigma_cm": NZ.reshape(-1),
    "dSdt_cm_per_yr": DS.reshape(-1),
})
long.to_parquet(SIG / "mascon_monthly_long.parquet", index=False)

# regional (area-weighted) aggregate + GSFC regional uncertainty (Z=22)
def regional(mask, tag):
    w = area_km2[sel][mask]; w = w / w.sum()
    s = np.nansum(CM[mask] * w[:, None], axis=0)
    s[np.all(~np.isfinite(CM[mask]), axis=0)] = np.nan
    N = int(mask.sum()); Z = min(22, N)
    n_bar = np.nanmean(NZ[mask], axis=0)
    l_bar = float(np.mean(leak2[mask])); lt_bar = float(np.mean(leak_tr[mask]))
    unc95 = (n_bar + l_bar) / np.sqrt(N / Z)
    return pd.DataFrame({
        "month": month_str, "observed": present, "mission": mission.astype(str),
        "decimal_year": np.where(present, dec_year, dec_year_axis),
        f"{tag}_lwe_cm": s, f"{tag}_uncert95_cm": unc95,
    }), dict(region=tag, n_mascons=N, Z=Z, mean_leakage_2sigma_cm=l_bar,
             mean_leakage_trend_uncert_cm_per_yr=lt_bar,
             total_area_km2=float(area_km2[sel][mask].sum()))

reg_frames, reg_meta = [], []
for tag, mask in [("arabian_peninsula", on_pen), ("box_all_land", np.ones(n_mas, bool))]:
    d, m = regional(mask, tag); reg_frames.append(d.set_index("month")); reg_meta.append(m)
reg = pd.concat([reg_frames[0], reg_frames[1].filter(like="box_all_land")], axis=1)
reg.to_csv(SIG / "regional_mean_series.csv")

# netCDF of the per-mascon product
ds = xr.Dataset(
    {
        "lwe_thickness": (("mascon", "month"), CM),
        "noise_2sigma": (("mascon", "month"), NZ),
        "dSdt": (("mascon", "month"), DS),
        "observed": (("month",), present),
        "mission": (("month",), mission.astype(str)),
        "decimal_year": (("month",), np.where(present, dec_year, dec_year_axis)),
        "solution_mid_date": (("month",), mid_full.to_numpy()),
        **{c: (("mascon",), meta[c].to_numpy()) for c in meta.columns if c != "mascon_id"},
    },
    coords={"mascon": mascon_id, "month": month_str},
    attrs=dict(
        title="GSFC RL06v2.0 mascon LWE anomaly, Arabian Peninsula subset",
        source_file=str(H5),
        source_url="https://earth.gsfc.nasa.gov/sites/default/files/geo/gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5",
        units="cm equivalent water height",
        baseline="mean over 2004.0-2010.0 removed (per GSFC)",
        gia="ICE6G-D removed by GSFC",
        box=f"lat {LAT0}-{LAT1}N, lon {LON0}-{LON1}E; GSFC location code 80 (land) only",
        scale_factor="NONE APPLIED - GSFC distributes no gain/leakage scale factor",
        submonthly_handling=f"{n_merged} calendar month(s) held 2 solutions; averaged weighted by n_ref_days_solution",
        gaps="missing months are NaN; never interpolated",
    ),
)
ds.to_netcdf(PROC / "arabia_mascons.nc")

json.dump({
    "n_land_mascons_in_box": int(n_mas),
    "n_on_peninsula": int(on_pen.sum()),
    "months_axis": [str(full[0]), str(full[-1])], "n_months_axis": len(full),
    "n_months_observed": int(present.sum()), "n_months_missing": len(missing),
    "missing_months": missing,
    "n_calendar_months_with_two_solutions": n_merged,
    "largest_gap": [str(gap_start.date()), str(gap_end.date()), float(gap_days[gi])],
    "regions": reg_meta,
}, open(PROC / "signal_build_summary.json", "w"), indent=2)

print("\nwrote:")
for p in sorted(list(SIG.glob("*")) + [PROC / "arabia_mascons.nc", PROC / "signal_build_summary.json"]):
    print("  ", p, f"{p.stat().st_size:,}")
print(f"\nvariance SNR (signal/noise) across mascons: median {np.median(snr_var):.1f}, "
      f"min {snr_var.min():.1f}, max {snr_var.max():.1f}")
print(f"peninsula regional series: std {np.nanstd(reg['arabian_peninsula_lwe_cm']):.2f} cm, "
      f"median 95% uncert {np.nanmedian(reg['arabian_peninsula_uncert95_cm']):.2f} cm")
