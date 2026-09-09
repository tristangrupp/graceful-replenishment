# Graceful replenishment

Satellite gravimetry turned into basin water storage, and then into an estimate of
groundwater. Everything here starts from mascon solutions produced by the Gravity Recovery
and Climate Experiment (GRACE) and its successor, GRACE Follow-On. The code removes the
parts of a storage change that the weather and the land surface explain. Then it asks what
remains.

You get a global map at two basin scales and an interactive page for reading any single
basin's monthly record. Six regional studies go deeper than a global map can.

## What the analysis does

**Preprocessing.** GRACE ships as mascons, equal-area cells of about 12,400 square
kilometers each. The code reads the native HDF5 file from the Goddard Space Flight Center (GSFC),
rather than an interpolated grid. Interpolating GRACE to a finer grid invents structure the
measurement doesn't have. A location code drops ocean mascons. Ice sheets come in or stay
out by choice rather than by accident. Goddard codes Greenland, Antarctica, and the ice caps
as 1, 3, 4, and 5, not as land, so a filter on `location == 80` drops Greenland from a global
map without warning.

**Trend fitting.** The fit takes a slope together with annual and semi-annual harmonics, so
it removes the seasonal cycle rather than smoothing it. Significance discounts serial
correlation through an effective number of independent observations, following the 1964
correction of Dawdy and Matalas. Monthly storage anomalies correlate strongly from one month
to the next, and a naive least-squares p-value overstates confidence by a wide margin.

**Removing precipitation.** A significant decline sits as comfortably with a dry decade as with
over-pumping. The code refits the trend with accumulated precipitation anomaly as a
covariate and reports the surviving part as `fraction_unexplained`. The regressor
accumulates rather than tracking single months, because storage integrates flux. A storage
anomaly answers to accumulated surplus or deficit, not to any one month of rain.

**Removing soil moisture.** Groundwater storage comes from total water storage minus soil
moisture, snow water equivalent, and canopy storage. The code computes that difference once
per land surface model. It then averages three models from the Global Land Data Assimilation
System (GLDAS), namely Noah, Variable Infiltration Capacity (VIC), and the Catchment Land
Surface Model (CLSM). Averaging turns the model spread into a stated uncertainty instead of
an assumption. GLDAS averages up onto each mascon, never the other way round. Baselines come
off over the months the two records share, because GRACE has gaps and GLDAS doesn't.
De-meaning each record over its own axis would leave a constant offset with no physical
meaning.

## Layout

```
shared/      reusable pieces: mascon geometry and lookup, GLDAS downloaders,
             basin rasterization and area weighting, figure styling
global/      the global pipeline, its outputs, and its report
global/red/  the downscaling test, at HydroBASINS level 6
site/        the interactive page
regions/     six regional studies, each with scripts, tables, figures, and a report
```

### The global pipeline, in order

| script | what it does |
|---|---|
| `shared/gldas_download_global.py` | whole GLDAS granules over HTTPS, one at a time, resumable |
| `global/scripts/01_global_gws.py` | mascon trends for both total and groundwater storage |
| `global/scripts/02_basins.py` | combine mascons onto HydroBASINS, one level per run |
| `global/scripts/03_maps.py` | the static maps |
| `global/scripts/04_crosscheck.py` | global pipeline versus the regional Arabia run |
| `global/scripts/05_level_compare.py` | level 3 versus level 4 |
| `global/scripts/06_export_viz.py` | the payload the page reads |
| `global/scripts/08_glacier_fraction.py` | glacier cover per basin, for the ice filter |
| `global/scripts/10_red_geometry.py` | downscaling test 1, whether a level 6 basin is resolved at all |
| `global/scripts/11_red_series.py` | basin-mean monthly series for every product and predictor |
| `global/scripts/12_red_tests.py` | tests 2 and 3, the flag table, the sensitivity table |
| `global/scripts/13_red_map.py` | the red maps and the two diagnostic figures |
| `global/scripts/14_red_export.py` | the payload the downscaling page reads |
| `global/scripts/15_red_methods.py` | the methods note, with the numbers injected |

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

It's live at https://tristangrupp.github.io/graceful-replenishment/, and it also runs from
disk: open `site/index.html`. Every file in that folder has to stay together. The first two
pages share one 5 MB `data.js`, and the third reads its own `red_data.js`.

Page one maps a rate. It shows the slope of one line fitted through all 92 monthly
solutions, in millimeters of water per year. That isn't the difference between the first
year and the last. Page two does year by year with three frames: level, change from last
year, and first year to last. It also folds each basin's deseasonalized record into one line
per calendar year. Page three is the downscaling test below, and it ships the metrics rather
than the verdicts, so moving any threshold redraws the map and the counts.

## Where the numbers landed

The window runs 2018-06 to 2026-03 and holds 92 monthly solutions. That covers the GRACE
Follow-On era up to the end of the current Goddard release.

At HydroSHEDS level 3, 247 basins get a value covering 99.7 percent of land area, with a
median of 47 mascons each. Level 4 gives 1,283 basins and a median of 12. Level 3 already
explains 66 percent of the area-weighted variance in level-4 total storage trends and 81
percent of the groundwater ones. The two levels part company over Greenland and the Canadian
Arctic, where level 4 separates coastal ablation from interior accumulation.

The median level-3 basin fell 22.3 mm end to end, from 2018 to 2026. Its fitted rate over
the same 7.75 years implies only 9.5 mm. The two measures correlate at 0.985 and rank basins
almost identically, yet 39 of 247 disagree on sign. That gap is why the page reports both.
The endpoint difference rests on the 5 solved months of 2018 and the 3 of 2026, so 8 of the
92 solutions decide it.

## The downscaling test

Two published global products claim to resolve storage finer than GRACE measures it.
GRACE-SeDA runs at 0.5 degrees, from Gou and Soja. Li and Kusche runs at 0.25 degrees.
Both are built from JPL mascons and neither was trained on wells. The question is whether either one
adds usable information at HydroBASINS level 6, and the test answers it with no validation
data at all. Full write-up in `global/RED_METHODS.md`.

The design is one-sided on purpose. Five tests each detect one way of failing. The coarse
footprint does not resolve the basin. The product barely departs from the coarse series.
Precipitation and soil moisture explain the departure. The two products disagree with each
other. A basin's rank moves between them. A basin that trips one has been shown to
add nothing usable. A basin that trips none has only survived, and the map calls it "not
tested as failing" rather than green.

Over the common window 2002-04 to 2022-12, 214 months, 14,441 of the 15,495 testable basins
fail at least one test. That is 90 percent of the tested land area.

Three findings under that number.

**Level 6 is mostly below the resolution.** 48 of 16,397 basins reach the roughly 63,000
square kilometer reliable unit of Vishwakarma, Devaraju and Sneeuw (2018), which is 3.1
percent of the level's land area. The median basin is 5,318 square kilometers and holds 2
GRACE-SeDA cells. Half of all basins sit more than 97 percent inside a single coarse mascon,
so any structure a product draws inside them came from somewhere other than gravimetry.

**The two products fail in opposite ways.** Li and Kusche stays close to its parent: the
median basin's departure is 4 percent of the coarse variance, and its depletion ranking
matches the coarse ranking at Spearman 0.972. GRACE-SeDA departs by 42 percent and ranks
basins differently, at 0.675. Neither is automatically the better behavior. Switching
processing center, from JPL to GSFC, already moves the median basin by 25 percent of its
variance and reorders the ranking to 0.798. So GRACE-SeDA disagrees with its own parent solution by more than two centers
disagree with each other, and Li and Kusche disagrees by less than the rounding.

**Downscaling changed the resolution, not the priority order.** The two downscaled products
agree with each other at 0.699, worse than either agrees with a coarse solution. Where two
products built from the same measurements disagree, at least one is wrong, and establishing
that needs no outside data.

The departure is not mostly a weather field: only 342 basins regress on precipitation, soil
moisture and snow above an adjusted R squared of 0.8. That test was the weakest of the five,
and its result is reported rather than buried.

Every threshold is a judgment call, so `12_red_tests.py` emits a sensitivity table and the
page lets a reader move each cut. Moving one cut at a time never takes the headline below
13,194 basins or above 15,380. Setting all seven to the most generous end of their range at
once leaves 10,170 flagged, 66 percent of those tested and 55 percent of the tested land
area. Setting all seven to the strictest end flags every tested basin.

What this cannot do is say that any downscaled value is right. That needs wells,
evapotranspiration or InSAR, and an ablation of predictor-only against
predictor-plus-GRACE scored against them.

## Regional studies

| region | what it settled |
|---|---|
| `regions/saudi` | Arabian Peninsula groundwater losing 6.27 mm/yr, steeper than total storage, with 213 of 222 mascons declining and a cross-check with a second solution that holds |
| `regions/nuevoleon` | the decline is reservoirs plus a drought that has largely refilled, not an aquifer. The groundwater term reads +0.79 mm/yr at p = 0.07 |
| `regions/oregon` | a null result that became interpretable only after a positive control ran elsewhere |
| `regions/centralvalley` | that positive control, using measured evapotranspiration of applied water from California's Department of Water Resources |
| `regions/iran`, `regions/mississippi` | decorrelation, and how few independent measurements a region holds |

One finding recurs across them all: neighboring mascons aren't independent. Effective
degrees of freedom land between 1.2 and 1.8 whatever the region's size, from Nuevo Leon to a
292-mascon slice of Iran. A count of significant basins is never a count of independent
facts.

## What you won't find here

Raw downloads stay out: 7.7 GB of GLDAS granules, the 172 MB Goddard mascon HDF5, the 3.6 GB
of CHIRPS yearly files, the 2.5 GB of downscaled products, and the rainfall, reservoir, and
water-balance archives. Every script that needs them fetches them,
and the downloaders resume.

The two GeoPackages of basin geometry with trends attached also stay out, at 47 MB and
77 MB, and so does the 208 MB level 6 one from the downscaling test. `02_basins.py` and
`13_red_map.py` regenerate them from the shapefiles and the tables that are here. The basin
series behind the downscaling test are 400 MB of parquet and stay out too; `11_red_series.py`
rebuilds them.

GLDAS needs an Earthdata Login bearer token. The downloader reads it from the file named by
`EARTHDATA_TOKEN_FILE`. It never appears on a command line and never reaches any output. The
data center's OPeNDAP host retired in August 2026 and now returns 410, which is why the
global downloader pulls whole granules over HTTPS instead.

## Dependencies

The trend fitting, the precipitation covariate, and the attribution step come from the
`dark_water` package at https://github.com/tristangrupp/dark-water, on the
`grace-preprocessing-fixes` branch. That repository forks
https://github.com/rlrognstad/dark-water, the original Dark Depletion Watchlist by
rlrognstad. The fork branch adds the preprocessing fixes and the precipitation covariate
this analysis depends on. Scripts here import the package and none of them change it.
Otherwise: xarray, numpy, pandas, scipy, geopandas, h5py, matplotlib, and netCDF4.

## Prose linting

`.vale.ini` configures [Vale](https://vale.sh) over the Markdown and the page's HTML, using
the write-good, Microsoft, and Google style packages. Run it with `vale README.md site/`.

## Sources

- Goddard mascons RL06v2.0, https://earth.gsfc.nasa.gov/geo/data/grace-mascons
- Center for Space Research RL06.3 mascons, University of Texas
- GLDAS 2.1 monthly Noah, VIC, and CLSM, from the Goddard Earth Sciences data center
- HydroSHEDS HydroBASINS v1c, https://www.hydrosheds.org
- CHIRPS v2.0, Climate Hazards Center
- Natural Earth 10m glaciated areas, public domain, https://www.naturalearthdata.com
- GRACE-SeDA v1, Gou and Soja, https://doi.org/10.3929/ethz-b-000648738
- Downscaled JPL mascons, Li and Kusche, https://doi.org/10.5281/zenodo.17265162
- JPL mascons RL06.3Mv04 CRI, `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4`, from PO.DAAC
- Reservoir and water-balance records from Mexico's national water commission, the Texas
  Water Development Board, and California's Department of Water Resources
