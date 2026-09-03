# Graceful replenishment

Satellite gravimetry turned into basin water storage, and then into an estimate of
groundwater. Everything here works from GRACE and GRACE-FO mascon solutions, removes the
parts of a storage change that the weather and the land surface can account for, and asks
what is left over.

The output is a global map at two basin scales, an interactive page for reading any single
basin's monthly record, and six regional studies that go deeper than a global map can.

## What the analysis actually does

**Preprocessing.** GRACE ships as mascons, roughly 12,400 km2 equal-area cells. The code
reads the native GSFC HDF5 rather than an interpolated grid, because interpolating GRACE to
a finer grid invents structure the measurement does not have. Ocean mascons are excluded by
location code, and ice sheets are kept or excluded deliberately rather than by accident:
GSFC codes Greenland, Antarctica and the ice caps as 1, 3, 4 and 5, not as land, so a
filter on `location == 80` silently drops Greenland from a global map.

**Trend fitting.** A slope is fitted jointly with annual and semi-annual harmonics, so the
seasonal cycle is removed rather than smoothed. Significance uses an effective sample size
that discounts for lag-1 residual autocorrelation, following Dawdy and Matalas (1964).
Monthly storage anomalies are strongly autocorrelated and a naive least-squares p-value
overstates confidence by a wide margin.

**Removing precipitation.** A significant decline is equally consistent with a dry decade
and with over-pumping. The trend is refitted with accumulated precipitation anomaly as a
covariate, and the part that survives is reported as `fraction_unexplained`. The regressor
is cumulative rather than monthly, because storage integrates flux: a storage anomaly
responds to accumulated surplus or deficit, not to any single month of rain.

**Removing soil moisture.** `GWS = TWS - (soil moisture + snow water equivalent + canopy)`,
computed per land-surface model and then averaged across GLDAS NOAH, VIC and CLSM so the
model spread becomes a stated uncertainty instead of an assumption. GLDAS is averaged up
onto each mascon, never the other way round. Baselines are removed only over the months the
two records share, because GRACE has gaps and GLDAS does not, and de-meaning each over its
own axis leaves a constant offset with no physical meaning.

## Layout

```
shared/      the reusable pieces: mascon geometry and lookup, GLDAS downloaders,
             the region-agnostic decorrelation analysis, figure styling
global/      the global pipeline, its outputs and its report
site/        the interactive page
regions/     six regional studies, each with its scripts, tables, figures and report
```

### The global pipeline, in order

| script | what it does |
|---|---|
| `shared/gldas_download_global.py` | whole GLDAS granules over HTTPS, serial and resumable |
| `global/scripts/01_global_gws.py` | mascon trends for both TWS and GWS |
| `global/scripts/02_basins.py` | aggregate onto HydroBASINS, one level per run |
| `global/scripts/03_maps.py` | the static maps |
| `global/scripts/04_crosscheck.py` | global pipeline against the regional Arabia run |
| `global/scripts/05_level_compare.py` | level 3 against level 4 |
| `global/scripts/06_export_viz.py` | the payload the page reads |

```powershell
cd C:\path\to\dark-water
$env:PYTHONPATH = "src"
$py = ".\.venv\Scripts\python.exe"

& $py shared\gldas_download_global.py E:\Water\Global 2018-06 2026-03
& $py global\scripts\01_global_gws.py
& $py global\scripts\02_basins.py 03
& $py global\scripts\02_basins.py 04
& $py global\scripts\03_maps.py 03
& $py global\scripts\03_maps.py 04
& $py global\scripts\06_export_viz.py
```

### The page

Open `site/index.html`. All six files in that folder have to stay together, because both
pages share one 5 MB `data.js`.

Page one maps a rate: the slope of one line fitted through all 92 monthly solutions, in
millimetres per year. It is not the difference between the first and last year. Page two
does year by year, with three frames, level, change from last year, and first year to last,
plus each basin's deseasonalised record folded one line per calendar year.

## Where the numbers landed

Window 2018-06 to 2026-03, 92 monthly solutions, which is the GRACE-FO era up to the end of
the current GSFC release.

At HydroSHEDS level 3, 247 basins get a value covering 99.7 percent of land area, with a
median 47 mascons each. At level 4 it is 1,283 basins and a median of 12. Level 3 already
explains 66 percent of the area-weighted variance in level-4 total storage trends and 81
percent of the groundwater ones, and the places the two levels genuinely disagree are
Greenland and the Canadian Arctic, where level 4 separates coastal ablation from interior
accumulation.

End to end against the fitted rate: the median level-3 basin fell 22.3 mm from 2018 to 2026,
while its fitted rate over the same 7.75 years implies 9.5 mm. The two correlate at 0.985
and rank basins almost identically, but 39 of 247 disagree on sign. That gap is the point
of reporting both. The endpoint difference rests on the 5 solved months of 2018 and the 3 of
2026, so 8 of the 92 solutions decide it.

## Regional studies

| region | what it settled |
|---|---|
| `regions/saudi` | Arabian Peninsula groundwater at -6.27 mm/yr, steeper than total storage, 213 of 222 mascons declining, and a CSR cross-check that holds |
| `regions/nuevoleon` | the apparent decline is reservoirs and a drought that has largely refilled, not an aquifer; the groundwater term is +0.79 mm/yr with p = 0.07 |
| `regions/oregon` | a null that turned out to be interpretable only after a positive control was run elsewhere |
| `regions/centralvalley` | that positive control, using measured DWR evapotranspiration of applied water |
| `regions/iran`, `regions/mississippi` | decorrelation, and how few independent measurements a region really holds |

The recurring finding across all of them is that neighbouring mascons are not independent.
Effective degrees of freedom come out between 1.2 and 1.8 whatever the region's size, from
Nuevo Leon to a 292-mascon slice of Iran. A count of significant basins is never a count of
independent facts.

## What is not in here

Raw downloads stay out: 2.6 GB of GLDAS granules, the 172 MB GSFC mascon HDF5, CHIRPS,
CONAGUA and DWR archives. Every script that needs them fetches them, and the downloaders
are resumable.

The two GeoPackages of basin geometry with trends attached are also out, at 47 MB and 77 MB.
They are regenerated by `02_basins.py` from the shapefiles and the CSVs that are here.

GLDAS needs an Earthdata Login bearer token, read from the file named by
`EARTHDATA_TOKEN_FILE`. It is never placed on a command line and never written into any
output. The GES DISC OPeNDAP host retired in August 2026 and now returns 410, which is why
the global downloader pulls whole granules over HTTPS instead.

## Dependencies

The trend fitting, the precipitation covariate and the GRACE-minus-GLDAS attribution come
from the `dark_water` package at https://github.com/tristangrupp/dark-water, on the
`grace-preprocessing-fixes` branch. Scripts import it and none of them modify it. Otherwise:
xarray, numpy, pandas, scipy, geopandas, h5py, matplotlib, netCDF4.

## Sources

- GSFC mascons RL06v2.0, https://earth.gsfc.nasa.gov/geo/data/grace-mascons
- CSR RL06.3 mascons, University of Texas Center for Space Research
- GLDAS 2.1 monthly NOAH, VIC and CLSM, NASA GES DISC
- HydroSHEDS HydroBASINS v1c, https://www.hydrosheds.org
- CHIRPS v2.0, Climate Hazards Center
- CONAGUA SINA, TWDB Water Data for Texas, California DWR
