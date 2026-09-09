# Green experiment methods note

Whether a downscaled GRACE product agrees with a measured groundwater level, and
whether gravimetry of any resolution says something about a well that the
weather fields do not already say.

The red experiment used no outside data, so it could only detect failure.
This one uses wells, so it can in principle show that a value is right. It does
that for the part of the world where the well records are open, and that part is
narrow.

## The wells

Jasechko et al. (2024), annual depth to water, open subset, `10.5281/zenodo.10003697`. Annual depth to water, negated once so that up
means more water, then taken as an anomaly against each well's own mean.

77,556 wells hold at least 10 annual values between
2002 and 2022. 58,010 of them have a
GRACE cell and could be scored. They fall inside 172 mascons.

That last number is the one to hold on to. The well network is far denser than
the measurement it is testing: tens of thousands of wells, a few hundred
independent gravimetric observations. Every test below counts mascons rather
than wells. Counting wells would turn a few hundred facts into tens of
thousands of them and would make almost any difference look certain.

### What the coverage leaves out

The open subset is North America, with France, Germany and Scandinavia, some of
Brazil and New Zealand. Asia is close to absent. The compilation behind it spans
more than 40 countries, but only the share its database managers permitted to be
reposted is public, and that share omits North India, the North China Plain,
Iran and the Arabian Peninsula. Those are where the red experiment found the
largest signals, and nothing here speaks for them.

IGRAC's Global Groundwater Information System hosts the same records, and its
bulk download asks for an email address and replies by mail. The Zenodo copy
needs no registration, so it is the one used.

## No specific yield anywhere

A groundwater level is a head. Storage is a volume. Converting between them
needs a specific yield, which is not known per well and would be the largest
free parameter in the comparison. Nothing here converts. Every score is a
correlation or an out of sample R squared on standardized series, and both are
unchanged by any positive scale factor, so the specific yield never enters and
cannot be tuned.

## How a product reaches a well

Each product's total water storage is read at the cell containing the well.
GLDAS Noah soil moisture, snow and canopy is averaged onto that same cell, a
0.5 degree cell taking the four 0.25 degree GLDAS cells inside it, and
subtracted. What remains is compared with the well.

Each product is scored against the release it names as its input, as in the red
experiment: jpl61 for GRACE-SeDA,
jpl for Li and Kusche.

## Result 1, agreement

Correlation of annual anomalies at the same well.

| solution | median r | wells scored |
|---|---|---|
| JPL RL06.3, coarse | 0.388 | 58,010 |
| JPL RL06.1, coarse | 0.386 | 58,010 |
| GRACE-SeDA | 0.324 | 58,046 |
| Li and Kusche | 0.374 | 55,769 |

The coarse solution tracks the median well better than either downscaled
product. Paired at the same well and counted by mascon:

| product | median change in r | mascons better | sign test p |
|---|---|---|---|
| GRACE-SeDA against its parent | -0.035 | 75 of 152 | 0.94 |
| Li and Kusche against its parent | +0.001 | 73 of 151 | 0.74 |

Neither improves on the release it was built from.

## Result 2, the ablation

Three nested linear models predict a well's annual level anomaly from
standardized annual series. A uses accumulated precipitation anomaly, soil
moisture, and snow plus canopy. B adds the coarse GRACE groundwater term. C adds
a downscaled one instead.

Splits hold out one mascon at a time. Random k-fold is not used anywhere: wells
inside one mascon see the same gravimetric observation, so a random split would
train and test on the same measurement and report memorisation as skill.

All models are fitted and scored on one common panel of
782,186 well-years, so no model is judged on an
easier sample than another.

| model | pooled out of sample R squared | median well r | against B, inside each mascon |
|---|---|---|---|
| A, weather only | 0.0928 | +0.384 | -0.0088, 58/133, p 0.17 |
| B, A plus coarse RL06.3 | 0.1248 | +0.452 | reference |
| B, A plus coarse RL06.1 | 0.1245 | +0.451 |  |
| C, A plus GRACE-SeDA | 0.1217 | +0.429 | +0.0097, 77/133, p 0.08 |
| C, A plus Li and Kusche | 0.1287 | +0.459 | +0.0018, 71/133, p 0.49 |

Two readings, and they differ for a reason worth stating. Pooled, adding the
coarse GRACE term lifts skill from 0.093 to
0.125. Inside each held-out mascon, the same comparison gives a
median change of -0.0088 with
58 of
133 mascons better, sign test p
0.17. The pooled figure includes
getting the level right between mascons, which is where a regional gravimetric
signal helps; the per-mascon figure only measures fit within one footprint. Both
are honest and they answer different questions.

Neither reading supports the finer grid. GRACE-SeDA sits at
0.1217 and Li and Kusche at 0.1287
against 0.1248 for the coarse solution, and per mascon neither
difference is separable from zero.

### Split by how wet the well is

The comparison reads cleanly only where precipitation flux does not dominate the
water balance, so the halves are reported rather than averaged together.
29,889 wells sit under 500 mm per year and
43,946 above it.

| model | dry, under 500 mm/yr | wet, over 500 |
|---|---|---|
| A, weather only | 0.0821 | 0.0853 |
| B, A plus coarse RL06.3 | 0.1249 | 0.1170 |
| C, A plus GRACE-SeDA | 0.0981 | 0.1240 |
| C, A plus Li and Kusche | 0.1321 | 0.1199 |

The two halves disagree about which downscaled product does better, which is
itself a reason not to read either as a validation.

## What this cannot do

A well measures a head at a point in one aquifer. A GRACE cell measures a mass
change over thousands of square kilometers through the whole column. They are
not the same quantity. A poor correlation can mean the product is wrong, the
well is unrepresentative of its cell, or a confined aquifer is responding to
pressure rather than to storage. This is evidence, not adjudication.

The ablation is the stronger of the two tests because it asks what a product
adds rather than how well it agrees. It still rests on a linear model of
annual values, and a product could hold information that a linear model cannot
use.

## Outputs

```
green/well_sites.parquet            one row per well
green/well_level_anomaly_m.parquet  annual level anomalies, wells in columns
green/well_gws_*.parquet            each product's groundwater term at each well
green/well_pred_*.parquet           the weather predictors at each well
green/well_scores.parquet           per well correlations and differences
green/mascon_oos_r2.parquet         out of sample skill inside each mascon
green/green_summary.json            every number quoted above
figures/fig_green_*.png             coverage, the paired test, the ablation
```
