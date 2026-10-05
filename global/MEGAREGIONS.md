# The mega-drying definition, applied to basins and aquifers

Chandanpurkar et al., "Unprecedented continental drying, shrinking freshwater
availability, and increasing land contributions to sea level rise", *Science
Advances* 11(30) eadx0298, doi 10.1126/sciadv.adx0298, maps terrestrial water
storage trends and outlines "mega-regions": areas drying faster than
-0.2 cm/yr that join hot spots previously reported as separate. Four are named,
all in the Northern Hemisphere.

The paper releases no gridded product. Its Figure 1 is JPL mascon RL06 v3,
about 3 degrees of real gravimetric resolution on a 0.5 degree grid, bias
corrected against GLDAS-2.2-DA and downscaled to 0.25 degrees. The data
availability statement points to the repositories of the inputs, not to that
field. So the map cannot be summarized on our units. The definition can.

## What this is

`global/scripts/41_megaregions.py` applies the -0.2 cm/yr cut, and the rule
that joins touching areas into one region, to the JPL mascon series this
project already aggregates onto 16,397 HydroBASINS level 6 catchments and 3,291
WHYMAP hydrogeological units.

## What this is not

This is not their figure reproduced. Three differences, each stated rather than
absorbed:

- **No bias correction and no downscaling.** This starts from JPL RL06.3Mv04
  CRI as published. The downscaling tab measures what that step adds at basin
  scale, and for Li and Kusche it is about 4 percent of the coarse variance.
- **Polygons, not cells.** Their outlines follow 0.25 degree cells; these
  follow basin boundaries, so an edge can move by the width of a basin.
- **A looser merge rule.** They contour a continuous field. This joins any two
  flagged units whose polygons touch, which lets one chain run further than a
  contour would.

## Method

Trends use the estimator the rest of the project uses: one least squares fit
per unit with annual and semi-annual harmonics beside the slope, significance
on an effective sample size for lag-1 autocorrelation. A unit is flagged when
its trend is at or below -2.0 mm/yr, which is the paper's -0.2 cm/yr.

Units over one fifth glacier or ice sheet are excluded, since the paper works
on the continents without Greenland and Antarctica and ice loss is not drying.
Natural Earth 10m glaciated areas supply the mask, built for level 6 by
`08b_glacier_level06.py`. The all-land number is reported beside the ice-free
one and the two differ by about one point.

Two windows run: the paper's, 2003-02 to 2024-04, and the full record this
project holds, 2002-04 to 2026-07.

## What came out, paper window

| | level 6 | aquifers |
|---|---|---|
| units with a trend, ice free | 15,633 | 2,039 |
| flagged at -0.2 cm/yr | 6,450 | 1,012 |
| share of ice-free land area | 39.4% | 43.9% |
| of those, significant at p 0.05 | 4,625 | 725 |
| of those, significant under Benjamini-Yekutieli | 3,080 | 492 |
| median trend, all units | -0.78 mm/yr | -2.43 mm/yr |
| median trend, flagged units | -5.83 mm/yr | -8.95 mm/yr |

The full record gives 37.6 and 44.4 percent, so the share is not an artifact of
the end date.

Clusters at level 6, by area, with the paper's region that holds most of each:

| area | span | matches |
|---|---|---|
| 21.45 Mkm2 | lon -8 to 122, lat 2 to 61 | region 4, MENA and Pan-Eurasia, 70% |
| 7.59 Mkm2 | lon -137 to -83, lat 9 to 70 | region 3, southwest North America, 58% |
| 4.56 Mkm2 | lon 67 to 161, lat 50 to 76 | region 2, northern Russia, 99% |
| 3.75 Mkm2 | lon -63 to -35, lat -25 to -3 | none: Amazon and Cerrado |
| 2.99 Mkm2 | lon -11 to 21, lat 23 to 37 | region 4, 100% |
| 1.14 Mkm2 | lon 115 to 135, lat -28 to -20 | none: western Australia |
| 0.96 Mkm2 | lon 26 to 37, lat -28 to -11 | none: southern Africa |

By aquifer class, the share of units flagged runs local and shallow 58 percent,
major groundwater basin 47 percent, complex structure 41 percent.

## Reading it

Three things to hold onto.

**The share is robust, the clusters are not.** Between 37 and 44 percent of
ice-free land area passes the cut on every combination of unit and window. The
cluster geometry is another matter: at level 6 one chain spans 21 Mkm2 from the
Atlantic to east Asia, and on WHYMAP units, which are larger and sprawl, a
single cluster reaches 34 Mkm2 and matches no single region. Touching polygons
chain further than a contour does. Cluster boundaries here are weaker evidence
than the counts.

**The Southern Hemisphere clusters are not a contradiction.** The paper names
four Northern Hemisphere mega-regions. The Amazon and Cerrado, western
Australia and southern Africa appear here as their own clusters because nothing
in this method restricts it to one hemisphere.

**Significance thins the map.** Of 6,450 flagged level 6 units, 4,625 have a
trend separable from zero at a flat p 0.05, and 3,080 survive
Benjamini-Yekutieli, which holds under the spatial dependence measured in
`40_spatial_autocorr.py`. Half the flagged area is drying at a rate this record
cannot separate from zero.

## Outputs

- `global/trends/megaregions_level06.json`, `megaregions_aquifer.json`: counts,
  areas, shares, cluster list.
- `global/trends/megaregions_level06.parquet`, `megaregions_aquifer.parquet`:
  one row per unit with trend, p-value, glacier share and the flag.
