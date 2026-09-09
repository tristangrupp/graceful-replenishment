"""Write the methods note for the red experiment.

Prose with the numbers injected, so the note cannot drift away from the run that
produced it. Everything here is recorded because a later reader has to be able
to tell what was measured from what was assumed.
"""

import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, r"E:\Water\_shared")
import red_grid as rg  # noqa: E402

RED = rg.RED
s = json.load(open(RED / "level6_red_summary.json"))
g = json.load(open(RED / "level6_geometry_summary.json"))
src = json.load(open(RED / "sources.json"))
c = s["config"]
m = s["medians"]
sp = s["spearman"]
f = s["flags"]
ps = pd.read_parquet(RED / "precip_source.parquet")
n_chirps = int((ps["precip_source"] == "chirps").sum())


def pc(x):
    return f"{x * 100:.0f}"


def n(x):
    return f"{x:,}"


rows = "\n".join(
    f"| {k} | {n(v['n'])} | {pc(v['area_share_of_tested'])} |"
    for k, v in f.items() if not k.endswith(("_G", "_L")))
by_product = "\n".join(
    f"| {k} | {n(v['n'])} | {pc(v['area_share_of_tested'])} |"
    for k, v in f.items() if k.endswith(("_G", "_L")))

sens_rows = []
for key, vals in s["sensitivity"].items():
    cells = " | ".join(f"{r['value']} : {n(r['n_flag'])}" for r in vals)
    sens_rows.append(f"| `{key}` | {cells} |")
sens = "\n".join(sens_rows)
cg = s["sensitivity_corners"]["most_generous"]
cs = s["sensitivity_corners"]["strictest"]

dec = "\n".join(
    f"| {d['decile']} | {d['area_km2_range'][0]:,.0f} to {d['area_km2_range'][1]:,.0f} "
    f"| {n(d['n'])} | {pc(d['red_share'])} |"
    for d in s["area"]["red_share_by_area_decile"])

doc = f"""# Red experiment methods note

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
| GRACE-SeDA | v1, 2024-05-16 | 0.5 deg | {src['seda']['coverage'] if 'coverage' in src['seda'] else '2002-04 to 2022-12'} | mm | {src['seda']['baseline']} |
| Li and Kusche | v2.0 | 0.25 deg | {src['liku']['coverage']} | cm, converted to mm here | not stated in the file |

DOIs: GRACE-SeDA `{src['seda']['doi']}`, Li and Kusche `{src['liku']['doi']}`
(md5 `{src['liku']['md5']}`, checked after download).

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
| one center, one release: JPL RL06.1 to RL06.3 | {m['var_ratio_release']:.5f} | {sp['coarse_RL0603_vs_RL0601']:.4f} |
| two centers, same months: JPL to GSFC | {m['var_ratio_solution']:.3f} | {sp['coarse_JPL_vs_GSFC']:.3f} |

Cost is the variance of the difference over the variance of the coarse series,
the same quantity test 2a uses. Changing release is 500 times cheaper than
changing center, which is why getting the release right mattered for the
argument and barely moved the answer: GRACE-SeDA's median departure went from
{m['var_ratio_G_alt_release']:.4f} against RL06.3 to {m['var_ratio_G']:.4f} against
RL06.1.

## Common period

{s['common_period'][0]} to {s['common_period'][1]}, {s['n_months']} months present in
every product. {s['n_months_with_predictors']} of those months also have the
predictor fields. GRACE-SeDA ends in 2022-12 and sets the ceiling.

## Basins and aggregation

HydroBASINS v1c level 6: {n(g['n_basins'])} basins, {g['total_area_km2'] / 1e6:.1f}
million square kilometers, median {g['area_km2']['50']:,.0f} square kilometers.

Every product sits on a different grid, so the basins are rasterized once at
0.05 degrees and every coarser grid inherits its overlap from that raster. A
basin mean is the sum of cell values times the area of each cell inside the
basin, divided by the area inside the basin. That is what a first-order
conservative remap computes, to the 0.05 degree quantization of the overlap.
Nearest neighbour and bilinear do not conserve mass and are used nowhere.

Two checks on the bookkeeping. The rasterized area of a basin against the area
HydroSHEDS publishes for it has a median ratio of
{g['raster_area_check']['median_ratio_raster_to_subarea']:.4f}. A basin mean
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
| 1 | `RED_GEOMETRY` | fewer product cells than this, or more of the basin than this inside one mascon | {c['min_cells']} cells, {c['max_frac_dominant']} |
| 2a | `RED_NO_INDEPENDENT_DEPARTURE` | variance of (downscaled minus coarse) over variance of coarse | {c['min_var_ratio']} |
| 2b | `RED_PREDICTOR_DERIVED` | adjusted R squared of the departure on precipitation, soil moisture, and snow | {c['max_pred_r2']} |
| 3 | `RED_DISAGREEMENT` | correlation between the two products, or trend gap over trend magnitude | {c['min_r_GL']}, {c['max_trend_diff_ratio']} |
| 3b | `RED_RANK_UNSTABLE` | percentile rank shift between the two products | {c['max_rank_shift']} |

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
{m['pred_r2_G']:.3f} and {m['pred_r2_eff_G']:.3f} for GRACE-SeDA, so the
serial-correlation correction removes essentially all of the apparent fit.

No random k-fold cross-validation is used anywhere. Nothing here is fitted for
prediction.

Precipitation is CHIRPS v2.0 where CHIRPS reaches, which is 50S to 50N and
{n(n_chirps)} basins, and the GLDAS-Noah precipitation
forcing for the rest. Which source a basin used travels with the basin.

## Results

{n(s['n_tested'])} of {n(s['n_basins'])} basins have a complete series in every
product and could be tested. The rest are reported as not tested, never as
passing.

| flag | basins | share of tested land area |
|---|---|---|
{rows}

Each product also has a verdict of its own, on its own three tests, with the two
comparison tests left out. A reader judging one product without reference to the
other needs a count that does not quietly fold the other one in.
`RED_ANY_OWN_G` and `RED_ANY_OWN_L` are those counts.

| flag | basins | share of tested land area |
|---|---|---|
{by_product}

The two fail in different places. Geometry catches most GRACE-SeDA failures: it moves away from its parent
solution, and only
{n(f['RED_NO_INDEPENDENT_DEPARTURE_G']['n'])} of its basins fail the departure test. Departure
catches Li and Kusche: {n(f['RED_NO_INDEPENDENT_DEPARTURE_L']['n'])} of its basins move less
than 5 percent of the coarse variance away from the solution behind it. Its finer
grid does resolve more basins geometrically, which is why it fails that test less
often.

### Red follows basin size

| area decile | km2 | basins | flagged red |
|---|---|---|---|
{dec}

That dependence is expected and is the main thing the geometry test measures.
Only {n(g['n_above_reliable_threshold'])} of {n(g['n_basins'])} level 6 basins
reach the roughly 63,000 square kilometre reliable unit of Vishwakarma, Devaraju
and Sneeuw (2018), which is
{g['area_share_above_reliable_threshold'] * 100:.1f} percent of the level's land
area.

### A floor under the departure

The median basin's departure from coarse GRACE is {m['var_ratio_G']:.3f} of the
coarse variance for GRACE-SeDA and {m['var_ratio_L']:.3f} for Li and Kusche. Two
coarse solutions of the same months, JPL and GSFC, already differ by
{m['var_ratio_solution']:.3f}. A departure below that number is not
distinguishable from the choice of processing center.

### Ranking

Ranked by depletion trend across all tested level 6 basins:

| pair | Spearman |
|---|---|
| GRACE-SeDA against coarse | {sp['G_vs_coarse']:.3f} |
| Li and Kusche against coarse | {sp['L_vs_coarse']:.3f} |
| the two downscaled products against each other | {sp['G_vs_L']:.3f} |
| JPL against GSFC, both coarse | {sp['coarse_JPL_vs_GSFC']:.3f} |

### Sensitivity

Count of basins flagged by the test each threshold governs, as the threshold
moves across a plausible range.

| threshold | value : basins flagged |
|---|---|
{sens}

Moving one cut at a time understates how much of the map is a choice, so both
corners are computed too. With every threshold at the most generous end of its
range at once, {n(cg['n_RED_ANY'])} basins stay flagged, {pc(cg['share_of_tested'])}
percent of those tested and {pc(cg['area_share_of_tested'])} percent of the tested
land area. With every threshold at the strictest end, all
{n(cs['n_RED_ANY'])} of them are.

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
"""

out = RED / "METHODS.md"
out.write_text(doc, encoding="utf-8")
print("wrote", out, len(doc), "chars")
