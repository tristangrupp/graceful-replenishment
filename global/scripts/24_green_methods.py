"""Write the methods note for the green experiment, numbers injected."""

import json
import sys

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

GREEN = rg.ROOT / "green"
s = json.load(open(GREEN / "green_summary.json"))
src = json.load(open(GREEN / "wells_sources.json"))
a = s["ablation"]
p = s["ablation_paired_by_mascon"]
w = s["ablation_by_wetness"]
sg = s["paired_against_parent"]
base = "B_plus_coarse_RL0603"


def n(x):
    return f"{x:,}"


LAB = {"A_predictors_only": "A, weather only",
       base: "B, A plus coarse RL06.3",
       "B_plus_coarse_RL0601": "B, A plus coarse RL06.1",
       "C_plus_seda": "C, A plus GRACE-SeDA",
       "C_plus_liku": "C, A plus Li and Kusche"}

abl_rows = "\n".join(
    f"| {LAB[k]} | {a[k]['oos_r2']:.4f} | {a[k]['median_well_r']:+.3f} | "
    + (("reference") if k == base else
       (f"{p[k + '_minus_' + base]['median_delta_r2']:+.4f}, "
        f"{p[k + '_minus_' + base]['mascons_better']}/{p[k + '_minus_' + base]['n_mascons']}, "
        f"p {p[k + '_minus_' + base]['sign_test_p']:.2f}")
       if (k + "_minus_" + base) in p else "")
    + " |"
    for k in LAB if k in a)

wet_rows = "\n".join(
    f"| {LAB[k]} | {w['dry_under_500mm']['models'].get(k, {}).get('oos_r2', float('nan')):.4f} "
    f"| {w['wet_over_500mm']['models'].get(k, {}).get('oos_r2', float('nan')):.4f} |"
    for k in LAB if k in w["dry_under_500mm"]["models"])

doc = f"""# Green experiment methods note

Whether a downscaled GRACE product agrees with a measured groundwater level, and
whether gravimetry of any resolution says something about a well that the
weather fields do not already say.

The red experiment used no outside data, so it could only detect failure.
This one uses wells, so it can in principle show that a value is right. It does
that for the part of the world where the well records are open, and that part is
narrow.

## The wells

{src['source']}, `{src['doi']}`. Annual depth to water, negated once so that up
means more water, then taken as an anomaly against each well's own mean.

{n(s['n_wells'])} wells hold at least {src['min_years']} annual values between
{s['window'][0]} and {s['window'][1]}. {n(s['n_scored']['jpl'])} of them have a
GRACE cell and could be scored. They fall inside {s['n_mascons']} mascons.

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
experiment: {s['parent_release']['seda']} for GRACE-SeDA,
{s['parent_release']['liku']} for Li and Kusche.

## Result 1, agreement

Correlation of annual anomalies at the same well.

| solution | median r | wells scored |
|---|---|---|
| JPL RL06.3, coarse | {s['median_r']['jpl']:.3f} | {n(s['n_scored']['jpl'])} |
| JPL RL06.1, coarse | {s['median_r']['jpl61']:.3f} | {n(s['n_scored']['jpl61'])} |
| GRACE-SeDA | {s['median_r']['seda']:.3f} | {n(s['n_scored']['seda'])} |
| Li and Kusche | {s['median_r']['liku']:.3f} | {n(s['n_scored']['liku'])} |

The coarse solution tracks the median well better than either downscaled
product. Paired at the same well and counted by mascon:

| product | median change in r | mascons better | sign test p |
|---|---|---|---|
| GRACE-SeDA against its parent | {sg['seda']['median_delta_r']:+.3f} | {sg['seda']['mascons_improved']} of {sg['seda']['n_mascons']} | {sg['seda']['p_value_by_mascon']:.2f} |
| Li and Kusche against its parent | {sg['liku']['median_delta_r']:+.3f} | {sg['liku']['mascons_improved']} of {sg['liku']['n_mascons']} | {sg['liku']['p_value_by_mascon']:.2f} |

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
{n(a['A_predictors_only']['n_rows'])} well-years, so no model is judged on an
easier sample than another.

| model | pooled out of sample R squared | median well r | against B, inside each mascon |
|---|---|---|---|
{abl_rows}

Two readings, and they differ for a reason worth stating. Pooled, adding the
coarse GRACE term lifts skill from {a['A_predictors_only']['oos_r2']:.3f} to
{a[base]['oos_r2']:.3f}. Inside each held-out mascon, the same comparison gives a
median change of {p['A_predictors_only_minus_' + base]['median_delta_r2']:+.4f} with
{p['A_predictors_only_minus_' + base]['mascons_better']} of
{p['A_predictors_only_minus_' + base]['n_mascons']} mascons better, sign test p
{p['A_predictors_only_minus_' + base]['sign_test_p']:.2f}. The pooled figure includes
getting the level right between mascons, which is where a regional gravimetric
signal helps; the per-mascon figure only measures fit within one footprint. Both
are honest and they answer different questions.

Neither reading supports the finer grid. GRACE-SeDA sits at
{a['C_plus_seda']['oos_r2']:.4f} and Li and Kusche at {a['C_plus_liku']['oos_r2']:.4f}
against {a[base]['oos_r2']:.4f} for the coarse solution, and per mascon neither
difference is separable from zero.

### Split by how wet the well is

The comparison reads cleanly only where precipitation flux does not dominate the
water balance, so the halves are reported rather than averaged together.
{n(w['dry_under_500mm']['n_wells'])} wells sit under 500 mm per year and
{n(w['wet_over_500mm']['n_wells'])} above it.

| model | dry, under 500 mm/yr | wet, over 500 |
|---|---|---|
{wet_rows}

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
"""

out = GREEN / "METHODS.md"
out.write_text(doc, encoding="utf-8")
print("wrote", out, len(doc), "chars")
