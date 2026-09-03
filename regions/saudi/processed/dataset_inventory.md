# GSFC mascon dataset inventory

- File: `E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd_halfdegree.nc`
- Size: 530,877,840 bytes
- Source URL: https://earth.gsfc.nasa.gov/sites/default/files/geo/gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd_halfdegree.nc

## Raw netCDF4 view (undecoded)

- netCDF format: `NETCDF3_CLASSIC`
- Groups: []

### Global attributes

```
title: NASA GSFC GRACE and GRACE-FO MASCON RL06 v1.0
summary: Monthly gravity solutions from GRACE and GRACE-FO as determined from the NASA GSFC RL06 v1.0 mascon solution
platform: GRACE and GRACE-FO
creator_name: Bryant Loomis
creator_email: bryant.d.loomis@nasa.gov
creator_url: https://earth.gsfc.nasa.gov/geo/data/grace-mascons
creator_institution: NASA GSFC
product_version: v1.0
geospatial_lat_min: -89.75
geospatial_lat_max: 89.75
geospatial_lat_units: degrees_north
geospatial_lat_resolution: 0.5 degree grid; however the native resolution of the data is 1-arc-degree equal-area mascons
geospatial_lon_min: 0.25
geospatial_lon_max: 359.75
geospatial_lon_units: degrees_east
geospatial_lon_resolution: 0.5 degree grid; however the native resolution of the data is 1-arc-degree equal-area mascons
time_mean_removed: 2004.000 to 2009.999
postprocess_1: OCEAN_ATMOSPHERE_DEALIAS_MODEL (GAD), MONTHLY_AVE, ADDED BACK TO OCEAN PIXELS ONLY
postprocess_2: Water density used to convert to equivalent water height: 1000 kg/m^3
GIA_removed: ICE6G-D; Peltier, W. R., D. F. Argus, and R. Drummond (2018) Comment on the paper by Purcell et al. 2016 entitled An assessment of ICE-6G_C (VM5a) glacial isostatic adjustment model, J. Geophys. Res. Solid Earth, 122.
geocenter_correction: JPL TN-13
C_20_substitution: TN-14; Loomis et al., 2020, Geophys. Res. Lett., https://doi.org/10.1029/2019GL085488
C_30_substitution: TN-14; Loomis et al., 2020, Geophys. Res. Lett., https://doi.org/10.1029/2019GL085488
journal_reference: Loomis et al. 2019, J. Geod., https://doi.org/10.1007/s00190-019-01252-y
date_created: date_stamp
```

### Dimensions

| dim | size | unlimited |
|---|---|---|
| lon | 720 | False |
| lat | 360 | False |
| time | 255 | False |
| bounds | 2 | False |

### Variables

| name | dims | shape | dtype | attributes |
|---|---|---|---|---|
| `lon` | ('lon',) | (720,) | float64 | units='degrees_east'; long_name='longitude'; standard_name='longitude'; axis='X'; valid_min=np.float64(0.25); valid_max=np.float64(359.75); bounds='lon_bounds' |
| `lat` | ('lat',) | (360,) | float64 | units='degrees_north'; latg_name='latitude'; standard_name='latitude'; axis='Y'; valid_min=np.float64(-89.75); valid_max=np.float64(89.75); bounds='lat_bounds' |
| `time` | ('time',) | (255,) | float64 | units='days since 2002-01-01T00:00:00Z'; long_name='time'; standard_name='time'; axis='T'; calendar='gregorian'; bounds='time_bounds' |
| `land_mask` | ('lat', 'lon') | (360, 720) | float64 | units='binary'; long_name='Land_Mask'; standard_name='Land_Mask'; coordinates='lat lon'; description='Land mask used for estimation/interpolation from 1-arc-degree mascon values' |
| `lwe_thickness` | ('time', 'lat', 'lon') | (255, 360, 720) | float64 | units='cm'; long_name='Liquid_Water_Equivalent_Thickness'; standard_name='Liquid_Water_Equivalent_Thickness'; coordinates='time lat lon'; grid_mapping='WGS84'; valid_min=np.float64(-1574.1008872602035); valid_max=np.float64(396.66862296729795); comment='Land values estimated from land 1-arc-degree mascons; Ocean values interpolated/extrapolated from 1-arc-degree mascons' |
| `lon_bounds` | ('lon', 'bounds') | (720, 2) | float64 | long_name='longitude boundaries'; units='degrees_east'; comment='longitude values at the west and east bounds of each pixel' |
| `lat_bounds` | ('lat', 'bounds') | (360, 2) | float64 | long_name='latitude boundaries'; units='degrees_north'; comment='latitude values at the north and south bounds of each pixel' |
| `time_bounds` | ('time', 'bounds') | (255, 2) | float64 | long_name='time boundaries'; units='days since 2002-01-01T00:00:00Z'; comment='time bounds for each time value, i.e. the first day and last day included in the monthly solution' |

### Raw value ranges (undecoded, ignoring nothing)

```
lon                      min=            0.25 max=          359.75 n_nan=0 n=720
lat                      min=          -89.75 max=           89.75 n_nan=0 n=360
time                     min=             107 max=            8841 n_nan=0 n=255
land_mask                min=               0 max=               1 n_nan=0 n=259200
lwe_thickness            min=         -1574.1 max=         396.669 n_nan=0 n=66096000
lon_bounds               min=               0 max=             360 n_nan=0 n=1440
lat_bounds               min=             -90 max=              90 n_nan=0 n=720
time_bounds              min=              94 max=            8855 n_nan=0 n=510
```

## xarray view

### decode_times=True

```
<xarray.Dataset> Size: 531MB
Dimensions:        (lat: 360, lon: 720, time: 255, bounds: 2)
Coordinates:
  * lat            (lat) float64 3kB -89.75 -89.25 -88.75 ... 88.75 89.25 89.75
  * lon            (lon) float64 6kB 0.25 0.75 1.25 1.75 ... 358.8 359.2 359.8
  * time           (time) datetime64[ns] 2kB 2002-04-18 ... 2026-03-17
Dimensions without coordinates: bounds
Data variables:
    land_mask      (lat, lon) float64 2MB ...
    lwe_thickness  (time, lat, lon) float64 529MB ...
    lon_bounds     (lon, bounds) float64 12kB ...
    lat_bounds     (lat, bounds) float64 6kB ...
    time_bounds    (time, bounds) datetime64[ns] 4kB ...
Attributes: (12/25)
    title:                      NASA GSFC GRACE and GRACE-FO MASCON RL06 v1.0
    summary:                    Monthly gravity solutions from GRACE and GRAC...
    platform:                   GRACE and GRACE-FO
    creator_name:               Bryant Loomis
    creator_email:              bryant.d.loomis@nasa.gov
    creator_url:                https://earth.gsfc.nasa.gov/geo/data/grace-ma...
    ...                         ...
    GIA_removed:                ICE6G-D; Peltier, W. R., D. F. Argus, and R. ...
    geocenter_correction:       JPL TN-13
    C_20_substitution:          TN-14; Loomis et al., 2020, Geophys. Res. Let...
    C_30_substitution:          TN-14; Loomis et al., 2020, Geophys. Res. Let...
    journal_reference:          Loomis et al. 2019, J. Geod., https://doi.org...
    date_created:               date_stamp
```

### decode_times=False

```
<xarray.Dataset> Size: 531MB
Dimensions:        (lat: 360, lon: 720, time: 255, bounds: 2)
Coordinates:
  * lat            (lat) float64 3kB -89.75 -89.25 -88.75 ... 88.75 89.25 89.75
  * lon            (lon) float64 6kB 0.25 0.75 1.25 1.75 ... 358.8 359.2 359.8
  * time           (time) float64 2kB 107.0 130.0 228.0 ... 8.811e+03 8.841e+03
Dimensions without coordinates: bounds
Data variables:
    land_mask      (lat, lon) float64 2MB ...
    lwe_thickness  (time, lat, lon) float64 529MB ...
    lon_bounds     (lon, bounds) float64 12kB ...
    lat_bounds     (lat, bounds) float64 6kB ...
    time_bounds    (time, bounds) float64 4kB ...
Attributes: (12/25)
    title:                      NASA GSFC GRACE and GRACE-FO MASCON RL06 v1.0
    summary:                    Monthly gravity solutions from GRACE and GRAC...
    platform:                   GRACE and GRACE-FO
    creator_name:               Bryant Loomis
    creator_email:              bryant.d.loomis@nasa.gov
    creator_url:                https://earth.gsfc.nasa.gov/geo/data/grace-ma...
    ...                         ...
    GIA_removed:                ICE6G-D; Peltier, W. R., D. F. Argus, and R. ...
    geocenter_correction:       JPL TN-13
    C_20_substitution:          TN-14; Loomis et al., 2020, Geophys. Res. Let...
    C_30_substitution:          TN-14; Loomis et al., 2020, Geophys. Res. Let...
    journal_reference:          Loomis et al. 2019, J. Geod., https://doi.org...
    date_created:               date_stamp
```

## Coordinate conventions

- `lon`: n=720, first=0.25, last=359.75, dtype=float64
    step: min=0.5 max=0.5 (uniform=True)
- `lat`: n=360, first=-89.75, last=89.75, dtype=float64
    step: min=0.5 max=0.5 (uniform=True)
- `time`: n=255, first=2002-04-18T00:00:00.000000000, last=2026-03-17T00:00:00.000000000, dtype=datetime64[ns]

- Longitude convention: **0-360** (min=0.25, max=359.75)

## Time axis

- dim `time`: n=255
- range: 2002-04-18 00:00:00 .. 2026-03-17 00:00:00
- distinct calendar months: 254; months with >1 solution: 1
- duplicated months: ['2018-11']
- expected months in span: 288; missing: 34
- missing month list: ['2002-06', '2002-07', '2003-06', '2011-01', '2011-06', '2012-05', '2012-10', '2013-03', '2013-08', '2013-09', '2014-02', '2014-07', '2014-12', '2015-06', '2015-10', '2015-11', '2016-04', '2016-09', '2016-10', '2017-02', '2017-07', '2017-08', '2017-09', '2017-10', '2017-11', '2017-12', '2018-01', '2018-02', '2018-03', '2018-04', '2018-05', '2018-08', '2018-09', '2018-10']

---

# Findings from inspection (interpretation)

## Units and sign convention — verified against file metadata

- `lwe_thickness` carries `units='cm'`, long name `Liquid_Water_Equivalent_Thickness`.
  **No unit conversion was needed or applied.** The global attribute
  `postprocess_2: Water density used to convert to equivalent water height: 1000 kg/m^3`
  confirms cm equivalent water height.
- Sign: positive = water gained relative to baseline. Verified empirically — the mean of
  every land pixel over 2004-01..2009-12 is **exactly 0.000000 cm**, matching the global
  attribute `time_mean_removed: 2004.000 to 2009.999`. So these are anomalies about a
  2004.0-2010.0 mean, and a negative trend is loss of stored water.
- GIA already removed (ICE6G-D). Geocentre (TN-13), C20 and C30 (TN-14) already substituted.
  `postprocess_1` adds the GAD ocean/atmosphere de-aliasing model back **to ocean pixels only**,
  which is a further reason ocean pixels must not be mixed into land statistics.

## Fill values, masks, uncertainty

- **No `_FillValue`, no `missing_value`, no NaN anywhere.** Every pixel of every month has a
  finite number, including ocean. Nothing can be identified as "missing" from the values alone.
- The file **does carry its own land mask**: `land_mask(lat, lon)`, binary 0/1, described as
  "Land mask used for estimation/interpolation from 1-arc-degree mascon values". This is the
  mask that was used to build the file, so it is the correct one. **JPL's land mask and JPL's
  gain grid were not used and must not be** (different mascon geometry entirely).
- **This netCDF carries no uncertainty field at all.** Noise and leakage uncertainty exist only
  in the native HDF5 product (see below).

## Missing months are absent, not flagged

The time axis has 255 entries spanning 288 calendar months. The 34 absent months (listed above)
simply have no record — they are not present-and-flagged. The largest block is the
GRACE / GRACE-FO transition: the last GRACE solution is centred **2017-06-11** and the first
GRACE-FO solution **2018-06-16**, a **370-day gap**. Note the gap is wider than the nominal
2017-06 -> 2018-05 because 2018-05, 2018-08, 2018-09 and 2018-10 are also absent.

## Sub-monthly duplicates

Exactly one calendar month, **2018-11**, holds two solutions, and `time_bounds` shows they are
non-overlapping sub-monthly windows:

| midpoint | window |
|---|---|
| 2018-11-01 | 2018-10-22 -> 2018-11-09 |
| 2018-11-21 | 2018-11-10 -> 2018-11-30 |

They were averaged weighted by `n_ref_days_solution` rather than truncated, so the month appears
once. Several early GRACE months also have unusually short windows (e.g. 2002-05 covers only
May 3-17), which is why the actual solution midpoint, not the month centre, is used as the time
coordinate in every fit.

## CRITICAL: the half-degree grid does not preserve mascon identity

The global attributes state the native resolution is **1-arc-degree equal-area mascons**, and
`lwe_thickness` is commented "Land values estimated from land 1-arc-degree mascons".
Empirically, over the Arabian box (lat 8-36N, lon 30-64E):

| cell class | cells | unique time series | group sizes |
|---|---|---|---|
| **land** | 2706 | **2706** | all singletons |
| ocean | 1102 | 520 | blocks of 1-6 |

**Every single land cell has a unique time series.** The land field is therefore *interpolated*
from the mascon solutions, not block-assigned, so mascon identity cannot be recovered from this
file. Supporting evidence: median absolute difference between adjacent land cells is 0.44 cm
(E-W) and 0.60 cm (N-S) against a median temporal standard deviation of 5.83 cm — neighbours are
similar but never identical.

Consequence for degrees of freedom: an SVD of the 1533 core land cells gives
PC1 = 85.0%, PC2 = 6.2%, PC3 = 3.4% of variance; **4 modes reach 95%, 12 modes reach 99%.**
Treating the 1533 half-degree cells as independent samples would overstate the spatial degrees of
freedom by two orders of magnitude.

**This is why the analysis was moved onto the native product.**

---

# Secondary source: native GSFC mascon HDF5 (PRIMARY for this analysis)

`E:\Water\Saudi\raw\gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5` (172,188,426 bytes)
from `https://earth.gsfc.nasa.gov/sites/default/files/geo/gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5`
Format doc: `https://earth.gsfc.nasa.gov/sites/default/files/2022-05/gsfc_mascons_hdf5_format_rl06v2.pdf`
(saved as `raw/gsfc_mascons_hdf5_format_rl06v2.pdf`).

| group/dataset | shape | units | notes |
|---|---|---|---|
| `mascon/lat_center`, `lon_center` | 1 x 41168 | degrees | lon is **0-360** |
| `mascon/lat_span`, `lon_span` | 1 x 41168 | degrees | 1.0 x 1.02-1.18 in Arabia |
| `mascon/area_km2` | 1 x 41168 | km^2 | 12373-12409 in Arabia (equal-area) |
| `mascon/labels` | 1 x 41168 | - | contiguous 1..41168 |
| `mascon/location` | 1 x 41168 | - | 1=GIS 3=AIS 4=ice shelf 5=GoA **80=Land 90=Water** |
| `mascon/basin` | 1 x 41168 | - | 6nnn = Middle East, 7nnn = Africa |
| `solution/cmwe` | 41168 x 255 | **cm equivalent water height** | mean over 2004.0-2010.0 removed |
| `uncertainty/noise_2sigma` | 41168 x 255 | cm (2-sigma) | stochastic, per mascon per month |
| `uncertainty/leakage_2sigma` | 41168 x 1 | cm (2-sigma) | stochastic leakage |
| `uncertainty/leakage_trend` | 41168 x 1 | **cm/yr** | leakage *trend uncertainty* |
| `time/ref_days_first/middle/last` | 1 x 255 | days since Jan 0 2002 | day 1 = 2002-01-01 |
| `time/n_ref_days_solution` | 1 x 255 | days | 13-37 L1B days per solution |

Time axis cross-checks exactly against the netCDF (2002-04-18 .. 2026-03-17, same 255 epochs,
same single duplicate month 2018-11).

## Scale / gain factor: GSFC does not distribute one

There is **no gain factor, scale factor or leakage-correction grid** in either GSFC file, and none
on the GSFC distribution page. Instead GSFC characterises leakage as an *uncertainty*. The format
document specifies:

> 95% confidence uncertainty for individual mascon = |l_trend| + 2*sigma_l + 2*sigma_noise
> 95% confidence uncertainty for mascon regions = |mean l_trend| + (mean 2*sigma_l + mean 2*sigma_noise) / sqrt(N/Z)
> ... Z is the number of mascons that defines the approximate spatial resolution: Z = 22 mascons (~300 km). If N <= Z, set Z = N.

So `leakage_trend` is a **symmetric uncertainty, not a signed bias to subtract**, and it does not
average down with region size (it is systematic) whereas the stochastic terms do. Both were used
as specified; **no scale factor was applied, and none exists to apply.** JPL's CLM4-derived gain
grid is built for JPL's 3-degree mascon geometry with a coastline-resolution (CRI) filter and is
**not interchangeable** with GSFC's 1-arc-degree equal-area mascons.

Consequence: basin/mascon amplitudes here are **biased low** by an unquantified leakage-damping
factor. GSFC bounds the resulting trend error at |leakage_trend|, which over the peninsula is
0.249 cm/yr (area-weighted mean of the absolute value).

## Metadata inconsistency worth knowing

The half-degree netCDF's global attributes say `title: ... RL06 v1.0` and `product_version: v1.0`,
while its filename says `rl06v2.0` and the HDF5's `/solution` group says `Version: RL06 v2.0`.
`date_created` is the literal unfilled string `date_stamp`. The netCDF global attributes are stale;
the data are RL06 v2.0.
