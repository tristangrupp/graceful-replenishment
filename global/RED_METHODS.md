# Red experiment methods note

Whether a published downscaled GRACE product adds usable information over native
resolution GRACE, on HydroBASINS level 6, with no validation data of any kind.

The experiment produces red only. A basin flagged red has been shown to add
nothing usable. A basin not flagged has survived a set of tests built to catch
obvious failure, which is a different statement from being correct. Nothing here
can produce a green basin, and the map and the page both say so.

## Products under test

| product | version | grid | coverage in file | units in file | baseline |
|---|---|---|---|---|---|
| GRACE-SeDA | v1, 2024-05-16 | 0.5 deg | 2002-04 to 2022-12 | mm | temporal mean 2004.000 to 2009.999 removed (`twsa_baseline` in the file) |
| Li and Kusche | v2.0 | 0.25 deg | 2002-04 to 2025-03 | cm, converted to mm here | not stated in the file |

DOIs: GRACE-SeDA `10.3929/ethz-b-000648738`, Li and Kusche `10.5281/zenodo.17265162`
(md5 `7d51f349bf74543d3bcd73e504502073`, checked after download).

Two things were verified rather than assumed, because either would have produced
a silently wrong answer. Li and Kusche stores centimeters where GRACE-SeDA
stores millimeters. Li and Kusche stores time as a decimal year at mid-month,
where GRACE-SeDA stores a Modified Julian Date. Neither is stated anywhere
except in the file.

Because Li and Kusche does not state a baseline, every series is re-centered on
the common months before anything is differenced. A difference of two baselines
survives a subtraction as a constant offset with no physical meaning.

## Coarse reference

Each product is differenced against the release it was built from, not against
one shared reference. GRACE-SeDA v1 names JPL RL06.1Mv03 CRI in its readme, so
that is its coarse term. Li and Kusche names no release, so it gets the current
one, RL06.3Mv04 CRI, with the alternative reported beside it as
`var_ratio_L_alt_release`. Using one release for both would push a release
change into one product's residual and score it as information the downscaling
added.

The RL06.1_V3 collection is retired from the data catalogue. The file is still
served under `podaac-ops-cumulus-protected/`, and a HEAD request to it returns
403 while a GET returns the file, which is worth knowing before concluding it
has gone.

Gain factors are deliberately not applied. They are a model-derived correction,
and applying one would add the model structure this experiment is looking for.

Two floors sit under any departure, and both are measured here rather than
assumed:

| what changes | cost, median basin | rank agreement |
|---|---|---|
| one center, one release: JPL RL06.1 to RL06.3 | 0.00048 | 0.9985 |
| two centers, same months: JPL to GSFC | 0.255 | 0.798 |

Cost is the variance of the difference over the variance of the coarse series,
the same quantity test 2a uses. Changing release is 500 times cheaper than
changing center, which is why getting the release right mattered for the
argument and barely moved the answer: GRACE-SeDA's median departure went from
0.4200 against RL06.3 to 0.4168 against
RL06.1.

## Common period

2002-04 to 2022-12, 214 months present in
every product. 214 of those months also have the
predictor fields. GRACE-SeDA ends in 2022-12 and sets the ceiling.

## Basins and aggregation

HydroBASINS v1c level 6: 16,397 basins, 135.0
million square kilometers, median 5,318 square kilometers.

Every product sits on a different grid, so the basins are rasterized once at
0.05 degrees and every coarser grid inherits its overlap from that raster. A
basin mean is the sum of cell values times the area of each cell inside the
basin, divided by the area inside the basin. That is what a first-order
conservative remap computes, to the 0.05 degree quantization of the overlap.
Nearest neighbour and bilinear do not conserve mass and are used nowhere.

Two checks on the bookkeeping. The rasterized area of a basin against the area
HydroSHEDS publishes for it has a median ratio of
0.9999. A basin mean
computed through the weight table against the same mean computed cell by cell
over the master raster agrees to 1.7e-13 mm.

Cells that are missing in a given month drop out of both the numerator and the
denominator, so a partly covered basin is renormalized rather than scored as
zero over the part that did not report.

## Tests and thresholds

Every threshold is a judgment call. They all sit in one block at the top of
`12_red_tests.py`, and the page lets a reader move each one and watch the map
redraw.

| test | flag | rule | threshold |
|---|---|---|---|
| 1 | `RED_GEOMETRY` | fewer product cells than this, or more of the basin than this inside one mascon | 2 cells, 0.95 |
| 2a | `RED_NO_DEPARTURE` | variance of (downscaled minus coarse) over variance of coarse | 0.05 |
| 2b | `RED_PREDICTOR_DERIVED` | adjusted R squared of the departure on precipitation, soil moisture, and snow | 0.8 |
| 3 | `RED_DISAGREEMENT` | correlation between the two products, or trend difference over trend size | 0.5, 1.0 |
| 3b | `RED_RANK_UNSTABLE` | percentile rank shift between the two products | 20.0 |

Justification for each, in order. Two cells is the smallest number that can
describe a field rather than a point. A basin more than 95 percent inside one
mascon has no within-basin gravimetric information at all, so any structure
drawn there came from somewhere else. Five percent of the coarse variance is
about the level at which a departure stops being distinguishable from the
difference between two processing centers, which is measured here rather than
assumed: see below. An adjusted R squared of 0.8 leaves a fifth of the departure
unexplained by weather, which is a generous bar given that both products are
built from weather fields. Correlation 0.5 and a trend difference equal to the
trend itself are the points at which two products stop describing the same
basin. Twenty percentile points is roughly the width of a decision band in a
ranked list.

Trends are fitted with a slope plus annual and semi-annual harmonics, and
significance discounts serial correlation through the effective sample size of
Dawdy and Matalas (1964). The predictor regression reports the ordinary adjusted
R squared, which is what the 0.8 threshold means, and beside it the same figure
with the effective sample size in the denominator. Median values are
0.250 and -0.006 for GRACE-SeDA, so the
serial-correlation correction removes essentially all of the apparent fit.

No random k-fold cross-validation is used anywhere. Nothing here is fitted for
prediction.

Precipitation is CHIRPS v2.0 where CHIRPS reaches, which is 50S to 50N and
12,311 basins, and the GLDAS-Noah precipitation
forcing for the rest. Which source a basin used travels with the basin.

## Results

15,495 of 16,397 basins have a complete series in every
product and could be tested. The rest are reported as not tested, never as
passing.

| flag | basins | share of tested land area |
|---|---|---|
| RED_GEOMETRY | 9,833 | 38 |
| RED_NO_DEPARTURE | 9,008 | 67 |
| RED_PREDICTOR_DERIVED | 332 | 2 |
| RED_DISAGREEMENT | 6,822 | 43 |
| RED_RANK_UNSTABLE | 4,272 | 26 |
| RED_ANY | 14,444 | 90 |

Each product also has a verdict of its own, on its own three tests, with the two
comparison tests left out. A reader judging one product without reference to the
other needs a count that does not quietly fold the other one in.
`RED_ANY_OWN_G` and `RED_ANY_OWN_L` are those counts.

| flag | basins | share of tested land area |
|---|---|---|
| RED_GEOMETRY_G | 9,830 | 38 |
| RED_NO_DEPARTURE_G | 59 | 1 |
| RED_PREDICTOR_DERIVED_G | 274 | 2 |
| RED_ANY_OWN_G | 9,965 | 40 |
| RED_GEOMETRY_L | 8,522 | 35 |
| RED_NO_DEPARTURE_L | 8,992 | 67 |
| RED_PREDICTOR_DERIVED_L | 105 | 1 |
| RED_ANY_OWN_L | 12,753 | 79 |

The two fail in different places. Geometry catches most GRACE-SeDA failures: it moves away from its parent
solution, and only
59 of its basins fail the departure test. Departure
catches Li and Kusche: 8,992 of its basins move less
than 5 percent of the coarse variance away from the solution behind it. Its finer
grid does resolve more basins geometrically, which is why it fails that test less
often.

### Red follows basin size

| area decile | km2 | basins | flagged red |
|---|---|---|---|
| 1 | 0 to 986 | 1,550 | 100 |
| 2 | 986 to 2,062 | 1,549 | 100 |
| 3 | 2,062 to 3,091 | 1,549 | 98 |
| 4 | 3,091 to 4,221 | 1,550 | 95 |
| 5 | 4,221 to 5,559 | 1,549 | 92 |
| 6 | 5,559 to 7,321 | 1,550 | 91 |
| 7 | 7,321 to 9,717 | 1,549 | 89 |
| 8 | 9,717 to 13,456 | 1,550 | 88 |
| 9 | 13,456 to 19,680 | 1,549 | 90 |
| 10 | 19,680 to 217,174 | 1,550 | 89 |

That dependence is expected and is the main thing the geometry test measures.
Only 48 of 16,397 level 6 basins
reach the roughly 63,000 square kilometre reliable unit of Vishwakarma, Devaraju
and Sneeuw (2018), which is
3.1 percent of the level's land
area.

### A floor under the departure

The median basin's departure from coarse GRACE is 0.417 of the
coarse variance for GRACE-SeDA and 0.041 for Li and Kusche. Two
coarse solutions of the same months, JPL and GSFC, already differ by
0.255. A departure below that number is not
distinguishable from the choice of processing center.

### Ranking

Ranked by depletion trend across all tested level 6 basins:

| pair | Spearman |
|---|---|
| GRACE-SeDA against coarse | 0.675 |
| Li and Kusche against coarse | 0.972 |
| the two downscaled products against each other | 0.699 |
| JPL against GSFC, both coarse | 0.798 |

### Sensitivity

Count of basins flagged by the test each threshold governs, as the threshold
moves across a plausible range.

| threshold | value : basins flagged |
|---|---|
| `min_cells` | 1 : 8,829 | 2 : 9,833 | 3 : 10,926 | 4 : 11,783 |
| `max_frac_dominant` | 0.8 : 11,695 | 0.9 : 10,537 | 0.95 : 9,833 | 0.99 : 9,017 |
| `min_var_ratio` | 0.02 : 3,625 | 0.05 : 9,008 | 0.1 : 12,394 | 0.2 : 14,318 |
| `max_pred_r2` | 0.7 : 883 | 0.8 : 332 | 0.9 : 73 | 0.95 : 13 |
| `min_r_GL` | 0.3 : 6,634 | 0.5 : 6,822 | 0.7 : 7,450 | 0.9 : 11,512 |
| `max_trend_diff_ratio` | 0.5 : 10,338 | 1.0 : 6,822 | 2.0 : 1,741 | 5.0 : 1,741 |
| `max_rank_shift` | 10.0 : 7,955 | 20.0 : 4,272 | 30.0 : 2,357 | 50.0 : 769 |

Moving one cut at a time understates how much of the map is a choice, so both
corners are computed too. With every threshold at the most generous end of its
range at once, 10,156 basins stay flagged, 66
percent of those tested and 55 percent of the tested
land area. With every threshold at the strictest end, all
15,495 of them are.

## What this does not do

It cannot say whether a downscaled value is correct anywhere, whether fine
structure reflects groundwater rather than total storage, or whether apparent
skill in a wet region is real rather than a shared response to rainfall. Those
need wells, evapotranspiration or InSAR, and an ablation of predictor-only
against predictor-plus-GRACE scored against them. That is a separate piece of
work, and it is only cleanly interpretable where precipitation flux does not
dominate the water balance.

## Outputs

```
red/level6_geometry.parquet        test 1, geometry only
red/level6_red_flags.parquet       the full table, one row per basin
red/level6_red_flags.gpkg          the same with polygons, for GIS
red/level6_red_summary.json        counts, medians, sensitivity
red/sources.json                   what was read, with units and versions
red/series_*.parquet               basin-mean monthly series, one file per source
figures/fig_red_*.png              the maps and the two diagnostic figures
```
