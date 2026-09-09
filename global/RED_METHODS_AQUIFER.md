# Red experiment methods note

Whether a published downscaled GRACE product adds usable information over native
resolution GRACE, on HydroBASINS level 6, with no validation data of any kind.

The experiment produces red flags, not certificates of validity. A red flag
means there is a specific reason not to treat a basin's result as independently
resolved or robust. An unflagged basin does not mean validated: it survived a
set of tests designed to identify specific, detectable failure modes, and that
is the full claim. Nothing here can produce a green basin, and the map and the
page both say so.

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
| one center, one release: JPL RL06.1 to RL06.3 | 0.00034 | 0.9990 |
| two centers, same months: JPL to GSFC | 0.274 | 0.834 |

Cost is the variance of the difference over the variance of the coarse series,
the same quantity test 2a uses. Changing release is 500 times cheaper than
changing center, which is why getting the release right mattered for the
argument and barely moved the answer: GRACE-SeDA's median departure went from
0.4377 against RL06.3 to 0.4349 against
RL06.1.

## Common period

2002-04 to 2022-12, 214 months present in
every product. 214 of those months also have the
predictor fields. GRACE-SeDA ends in 2022-12 and sets the ceiling.

## Basins and aggregation

HydroBASINS v1c level 6: 3,291 basins, 133.2
million square kilometers, median 957 square kilometers.

Every product sits on a different grid, so the basins are rasterized once at
0.05 degrees and every coarser grid inherits its overlap from that raster. A
basin mean is the sum of cell values times the area of each cell inside the
basin, divided by the area inside the basin. That is what a first-order
conservative remap computes, to the 0.05 degree quantization of the overlap.
Nearest neighbour and bilinear do not conserve mass and are used nowhere.

Two checks on the bookkeeping. The rasterized area of a basin against the area
HydroSHEDS publishes for it has a median ratio of
1.0001. A basin mean
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
| 2a | `RED_NO_INDEPENDENT_DEPARTURE` | variance of (downscaled minus coarse) over variance of coarse | 0.05 |
| 2b | `RED_PREDICTOR_DERIVED` | adjusted R squared of the departure on precipitation, soil moisture, and snow | 0.8 |
| 3 | `RED_DISAGREEMENT` | correlation between the two products, or trend gap over trend magnitude | 0.5, 1.0 |
| 3b | `RED_RANK_UNSTABLE` | percentile rank shift between the two products | 20.0 |

Justification for each, in order. Two cells is the smallest number that can
describe a field rather than a point. A basin more than 95 percent inside one
mascon has no within-basin gravimetric information at all, so any structure
drawn there came from somewhere else. Five percent of the coarse variance is
about the level at which a departure stops being distinguishable from the
difference between two processing centers, which is measured here rather than
assumed: see below. An adjusted R squared of 0.8 leaves a fifth of the departure
unexplained by weather, which is a generous bar given that both products are
built from weather fields. Correlation 0.5 and a trend gap equal to the trend
itself are the points at which the two products stop describing the same basin.
Their disagreement does not identify which one is closer to the truth, which
would need outside observations; it establishes that the basin-scale result is
method dependent and puts a lower bound on the uncertainty inferable from the
products themselves. Twenty percentile points is about the width of a decision
band in a ranked list.

Trends are fitted with a slope plus annual and semi-annual harmonics, and
significance discounts serial correlation through the effective sample size of
Dawdy and Matalas (1964). The predictor regression reports the ordinary adjusted
R squared, which is what the 0.8 threshold means, and beside it the same figure
with the effective sample size in the denominator. Median values are
0.255 and 0.011 for GRACE-SeDA, so the
serial-correlation correction removes essentially all of the apparent fit.

No random k-fold cross-validation is used anywhere. Nothing here is fitted for
prediction.

Precipitation is CHIRPS v2.0 where CHIRPS reaches, which is 50S to 50N and
2,050 basins, and the GLDAS-Noah precipitation
forcing for the rest. Which source a basin used travels with the basin.

## Results

1,570 of 3,291 basins have a complete series in every
product and could be tested. The rest are reported as not tested, never as
passing.

| flag | basins | share of tested land area |
|---|---|---|
| RED_GEOMETRY | 656 | 3 |
| RED_NO_INDEPENDENT_DEPARTURE | 1,048 | 88 |
| RED_PREDICTOR_DERIVED | 34 | 2 |
| RED_DISAGREEMENT | 652 | 20 |
| RED_RANK_UNSTABLE | 400 | 11 |
| RED_ANY | 1,472 | 94 |

Each product also has a verdict of its own, on its own three tests, with the two
comparison tests left out. A reader judging one product without reference to the
other needs a count that does not quietly fold the other one in.
`RED_ANY_OWN_G` and `RED_ANY_OWN_L` are those counts.

| flag | basins | share of tested land area |
|---|---|---|
| RED_GEOMETRY_G | 656 | 3 |
| RED_NO_INDEPENDENT_DEPARTURE_G | 26 | 19 |
| RED_PREDICTOR_DERIVED_G | 27 | 1 |
| RED_ANY_OWN_G | 692 | 22 |
| RED_GEOMETRY_L | 609 | 3 |
| RED_NO_INDEPENDENT_DEPARTURE_L | 1,047 | 88 |
| RED_PREDICTOR_DERIVED_L | 11 | 1 |
| RED_ANY_OWN_L | 1,324 | 89 |

The two fail in different places. Geometry catches most GRACE-SeDA failures: it moves away from its parent
solution, and only
26 of its basins fail the departure test. Departure
catches Li and Kusche: 1,047 of its basins move less
than 5 percent of the coarse variance away from the solution behind it. Its finer
grid does resolve more basins geometrically, which is why it fails that test less
often.

### Red follows basin size

| area decile | km2 | basins | flagged red |
|---|---|---|---|
| 1 | 23 to 373 | 157 | 100 |
| 2 | 373 to 2,963 | 157 | 98 |
| 3 | 2,963 to 5,442 | 157 | 93 |
| 4 | 5,442 to 8,609 | 157 | 90 |
| 5 | 8,609 to 12,835 | 157 | 92 |
| 6 | 12,835 to 20,054 | 157 | 91 |
| 7 | 20,054 to 32,281 | 157 | 91 |
| 8 | 32,281 to 55,323 | 157 | 96 |
| 9 | 55,323 to 146,130 | 157 | 93 |
| 10 | 146,130 to 14,590,175 | 157 | 94 |

That dependence is expected and is the main thing the geometry test measures.
Only 288 of 3,291 level 6 basins
reach the roughly 63,000 square kilometre reliable unit of Vishwakarma, Devaraju
and Sneeuw (2018), which is
84.9 percent of the level's land
area.

### A floor under the departure

The median basin's departure from coarse GRACE is 0.435 of the
coarse variance for GRACE-SeDA and 0.032 for Li and Kusche. Two
coarse solutions of the same months, JPL and GSFC, already differ by
0.274. A departure below that number is not
distinguishable from the choice of processing center.

### Ranking

Ranked by depletion trend across all tested level 6 basins:

| pair | Spearman |
|---|---|
| GRACE-SeDA against coarse | 0.719 |
| Li and Kusche against coarse | 0.982 |
| the two downscaled products against each other | 0.736 |
| JPL against GSFC, both coarse | 0.834 |

### Sensitivity

Count of basins flagged by the test each threshold governs, as the threshold
moves across a plausible range.

| threshold | value : basins flagged |
|---|---|
| `min_cells` | 1 : 613 | 2 : 656 | 3 : 731 | 4 : 774 |
| `max_frac_dominant` | 0.8 : 812 | 0.9 : 713 | 0.95 : 656 | 0.99 : 589 |
| `min_var_ratio` | 0.02 : 502 | 0.05 : 1,048 | 0.1 : 1,340 | 0.2 : 1,490 |
| `max_pred_r2` | 0.7 : 87 | 0.8 : 34 | 0.9 : 7 | 0.95 : 1 |
| `min_r_GL` | 0.3 : 636 | 0.5 : 652 | 0.7 : 726 | 0.9 : 1,049 |
| `max_trend_diff_ratio` | 0.5 : 992 | 1.0 : 652 | 2.0 : 175 | 5.0 : 175 |
| `max_rank_shift` | 10.0 : 746 | 20.0 : 400 | 30.0 : 213 | 50.0 : 54 |

Moving one cut at a time understates how much of the map is a choice, so both
corners are computed too. With every threshold at the most generous end of its
range at once, 985 basins stay flagged, 63
percent of those tested and 55 percent of the tested
land area. With every threshold at the strictest end, all
1,570 of them are.

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
