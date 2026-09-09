# Green experiment methods note

Whether a downscaled GRACE product agrees with a measured groundwater level, and
whether gravimetry of any resolution says something about a well that the
weather fields do not already say.

The red experiment used no outside data, so it could only detect failure.
This one uses wells, so it can in principle show that a value is right. It does
that for the part of the world where the well records are open, and that part is
narrow.

## The wells

Two sources, both annual depth to water in metres, both positive downward, and
both negated once here so that up means more water. Each well is then taken as
an anomaly against its own mean.

| source | reference |
|---|---|
| Jasechko et al. (2024), annual depth to water, open subset | 10.5281/zenodo.10003697 |
| CONAGUA, Mediciones Piezometricas, national network | https://sigagis.conagua.gob.mx/rp20/ |

Wells by source: CONAGUA 3,535, Jasechko 77,556.

They are held in one table with a source tag rather than merged blindly. The two
do not overlap: the closest CONAGUA well to any Jasechko well is 668 metres away
and only one pair falls within a kilometre, which is checked in the code rather
than assumed. The Jasechko wells that sit inside a Mexican bounding box are all
between 25.9 and 32.7 degrees north, which is the United States side of the
border.

81,091 wells hold at least 10 annual values between
2002 and 2022. 60,844 of them have a
GRACE cell and could be scored. They fall inside 195 mascons.

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
| JPL RL06.3, coarse | 0.380 | 60,844 |
| JPL RL06.1, coarse | 0.379 | 60,844 |
| GRACE-SeDA | 0.320 | 60,880 |
| Li and Kusche | 0.364 | 58,965 |

The coarse solution tracks the median well better than either downscaled
product. Paired at the same well and counted by mascon:

| product | median change in r | mascons better | sign test p |
|---|---|---|---|
| GRACE-SeDA against its parent | -0.033 | 83 of 172 | 0.70 |
| Li and Kusche against its parent | +0.001 | 84 of 170 | 0.94 |

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
819,731 well-years, so no model is judged on an
easier sample than another.

| model | pooled out of sample R squared | median well r | against B, inside each mascon |
|---|---|---|---|
| A, weather only | 0.0862 | +0.369 | -0.0115, 63/152, p 0.04 |
| B, A plus coarse RL06.3 | 0.1211 | +0.442 | reference |
| B, A plus coarse RL06.1 | 0.1208 | +0.442 |  |
| C, A plus GRACE-SeDA | 0.1173 | +0.421 | +0.0054, 82/152, p 0.37 |
| C, A plus Li and Kusche | 0.1245 | +0.446 | +0.0022, 87/152, p 0.09 |

Two readings, and they differ for a reason worth stating. Pooled, adding the
coarse GRACE term lifts skill from 0.086 to
0.121. Inside each held-out mascon, the same comparison gives a
median change of -0.0115 with
63 of
152 mascons better, sign test p
0.04. The pooled figure includes
getting the level right between mascons, which is where a regional gravimetric
signal helps; the per-mascon figure only measures fit within one footprint. Both
are honest and they answer different questions.

Neither reading supports the finer grid. GRACE-SeDA sits at
0.1173 and Li and Kusche at 0.1245
against 0.1211 for the coarse solution, and per mascon neither
difference is separable from zero.

### Split by how wet the well is

The comparison reads cleanly only where precipitation flux does not dominate the
water balance, so the halves are reported rather than averaged together.
30,690 wells sit under 500 mm per year and
46,620 above it.

| model | dry, under 500 mm/yr | wet, over 500 |
|---|---|---|
| A, weather only | 0.0742 | 0.0796 |
| B, A plus coarse RL06.3 | 0.1229 | 0.1133 |
| C, A plus GRACE-SeDA | 0.0949 | 0.1192 |
| C, A plus Li and Kusche | 0.1296 | 0.1158 |

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
