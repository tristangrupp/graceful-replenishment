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
global/green/ the same products scored against measured groundwater levels
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
| `global/scripts/20_green_wells.py` | every product and predictor at every well |
| `global/scripts/21_green_scores.py` | agreement, and the leave-one-mascon-out ablation |
| `global/scripts/22_green_figures.py` | coverage, the paired test, the ablation |
| `global/scripts/23_green_export.py` | the payload the wells page reads |
| `global/scripts/24_green_methods.py` | the green methods note |

```
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
& $py global\scripts\08_glacier_fraction.py

# the downscaling test, which needs GLDAS back to 2002 and the two downscaled products
& $py shared\gldas_download_global.py E:\Water\Global 2002-04 2018-05
& $py global\scripts\10_red_geometry.py
& $py global\scripts\11_red_series.py
& $py global\scripts\12_red_tests.py
& $py global\scripts\13_red_map.py
& $py global\scripts\14_red_export.py
& $py global\scripts\15_red_methods.py

# against wells, which needs the Jasechko level data from Zenodo 10.5281/zenodo.10003697
& $py global\scripts\20_green_wells.py
& $py global\scripts\21_green_scores.py
& $py global\scripts\22_green_figures.py
& $py global\scripts\23_green_export.py
& $py global\scripts\24_green_methods.py
```

### The page

It's live at https://tristangrupp.github.io/graceful-replenishment/, and it also runs from
disk: open `site/index.html`. Every file in that folder has to stay together. The first two
pages share one 5 MB `data.js`, the third reads `red_data.js` and the fourth reads
`wells_data.js`.

Page one maps a rate. It shows the slope of one line fitted through all 92 monthly
solutions, in millimeters of water per year. That isn't the difference between the first
year and the last. Page two does year by year with three frames: level, change from last
year, and first year to last. It also folds each basin's deseasonalized record into one line
per calendar year. Page three is the downscaling test, and it ships the metrics rather
than the verdicts, so moving any threshold redraws the map and the counts. Page four scores
the same products against wells.

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
other. A basin's rank moves between them. A red flag means there is a specific reason not to
treat that basin's result as independently resolved or robust. An unflagged basin does not
mean validated: it survived tests designed to identify specific, detectable failure modes,
and that is the full claim.

Each product is differenced against the release behind it. GRACE-SeDA v1 names JPL
RL06.1Mv03 CRI, so that is its coarse term; Li and Kusche names no release and gets the
current RL06.3Mv04. One shared reference would push a release change into one product's
residual and score it as added information.

Over the common window 2002-04 to 2022-12, 214 months, 14,444 of the 15,495 testable basins
fail at least one test. That is 90 percent of the tested land area. Judged on its own three
tests alone, without reference to the other product, GRACE-SeDA fails 9,965 basins and Li and
Kusche fails 12,753.

Three findings under that number.

An independent recomputation from the raw files, by a second agent using exact polygon
intersection rather than the 0.05 degree raster, reproduced every quantity: median
`var_ratio_G` 0.4195 against 0.4200, `n_cells_G` median 2, trends within 0.007 mm/yr. It also
caught the release mismatch above, which was real and worth fixing even though correcting it
moved the headline by three basins.

**Level 6 is mostly below the resolution.** 48 of 16,397 basins reach the 63,000
square kilometer reliable unit of Vishwakarma, Devaraju and Sneeuw (2018), which is 3.1
percent of the level's land area. The median basin is 5,318 square kilometers and holds 2
GRACE-SeDA cells. Half of all basins sit more than 97 percent inside a single coarse mascon,
so any structure a product draws inside them came from somewhere other than gravimetry.

**The two products fail in different places.** Geometry catches most GRACE-SeDA failures: it moves away from its parent, and only 62
of its basins fail the departure test. Departure
catches Li and Kusche: 8,992 of its basins move less than 5 percent of the coarse variance
away from the solution behind them. Its finer grid resolves more basins, so it fails the
geometry test less often, 8,522 against 9,834.

**They also disagree with the coarse solution in opposite directions.** Li and Kusche stays close to its parent: the
median basin's departure is 4 percent of the coarse variance, and its depletion ranking
matches the coarse ranking at Spearman 0.972. GRACE-SeDA departs by 42 percent and ranks
basins differently, at 0.675. Neither is automatically the better behavior. Two floors say how to read
those numbers, and both are measured rather than assumed. Moving one center across one
release, JPL RL06.1 to RL06.3, costs 0.0005 of the variance and leaves the ranking at
Spearman 0.9985. Moving between two centers, JPL to GSFC, costs 0.25 and drops the ranking to
0.798. GRACE-SeDA moves away from its own parent by more than two centers move apart from
each other, and the whole of Li and Kusche's departure is about a fifth of what changing
center does to the same months.

**Downscaling changed the resolution without reordering the priority list.** The two
downscaled products agree with each other at 0.699, worse than either agrees with a coarse
solution. That does not identify which one is closer to the truth, which would need outside
observations. It does establish that the basin-scale result is method dependent, and it puts
a lower bound on the uncertainty inferable from the products themselves.

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

## Against wells

The downscaling test used no outside data, so it could only detect failure. This half brings
in the reference that can say whether a value is right: measured groundwater levels, from the
open subset of the compilation behind Jasechko et al. (2024), on Zenodo at
`10.5281/zenodo.10003697`. The same records are browsable through IGRAC's Global Groundwater
Information System, whose bulk download asks for an email address and replies by mail; the
Zenodo copy needs no registration. Full write-up in `global/GREEN_METHODS.md`.

77,556 wells hold at least 10 annual values between 2002 and 2022, and 58,010 of them have a
GRACE cell. They fall inside 172 mascons. That ratio is the frame for everything below: the
well network is far denser than the measurement it is testing, so every test counts mascons
rather than wells.

**The coverage is not global.** It is North America, with France, Germany and Scandinavia,
some of Brazil and New Zealand. Asia is close to absent. North India, the North China Plain,
Iran and the Arabian Peninsula, which is where the downscaling test found the most, have no
open well records here at all.

**Neither downscaled product agrees with a well better than the coarse solution behind it.**
The coarse JPL solution tracks the median well at r 0.388. Li and Kusche reaches 0.374 and
GRACE-SeDA 0.324. Paired at the same well and counted by mascon, GRACE-SeDA is worse by 0.035
at p 0.94 and Li and Kusche is unchanged at p 0.74.

**Gravimetry does add something a well can see; the finer grid does not.** Three nested models
predict a well's annual level anomaly, scored out of sample by holding out one mascon at a
time over 782,186 well-years. Weather alone reaches 0.093. Adding the coarse GRACE
groundwater term lifts it to 0.125. Substituting a downscaled term gives 0.122 for GRACE-SeDA
and 0.129 for Li and Kusche. Judged inside each of 133 held-out mascons, which is the unit
that can carry a p-value here, none of those three differences is separable from zero.

The dry and wet halves disagree about which downscaled product does better, which is itself a
reason not to read either as a validation.

No specific yield is applied anywhere. A level is a head and storage is a volume, and
converting between them would introduce the largest free parameter in the comparison. Every
score is a correlation or an out of sample R squared on standardized series, both unchanged
by any positive scale factor.

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
- Annual groundwater levels, Jasechko et al. (2024), https://doi.org/10.5281/zenodo.10003697
- IGRAC Global Groundwater Information System, https://ggis.un-igrac.org/view/ggmn/
- GRACE-SeDA v1, Gou and Soja, https://doi.org/10.3929/ethz-b-000648738
- Downscaled JPL mascons, Li and Kusche, https://doi.org/10.5281/zenodo.17265162
- JPL mascons RL06.3Mv04 CRI, `TELLUS_GRAC-GRFO_MASCON_CRI_GRID_RL06.3_V4`, from PO.DAAC
- Reservoir and water-balance records from Mexico's national water commission, the Texas
  Water Development Board, and California's Department of Water Resources
