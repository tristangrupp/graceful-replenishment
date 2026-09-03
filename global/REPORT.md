# Global GRACE-FO storage trends on HydroSHEDS basins

**Window:** 2018-06 to 2026-03, 92 monthly solutions. That start is the first
GRACE-FO month; the end is where the current GSFC RL06v2.0 release stops. There
is no newer release -- `..._202604_...` through `..._202606_...` all 404 -- so
2026-03 is "today" for GRACE. GLDAS runs to 2026-05 and was cut to match.

**Products:** GSFC global mascons RL06v2.0 (`OBP-ICE6GD`, GIA-corrected) and
GLDAS 2.1 NOAH 0.25 deg, VIC 1.0 deg and CLSM 1.0 deg.
**Basins:** HydroSHEDS HydroBASINS v1c, levels 3 and 4, all nine regions.
**Analysis date:** 2026-09-02. **Outputs:** `E:\Water\Global\`.

## What was made

Four maps, two per level, on one shared colour scale so all of them can be read
against each other:

| file | level | product |
|---|---|---|
| `figures/fig1_global_tws_lev03.png` | 3 | total water storage |
| `figures/fig2_global_gws_lev03.png` | 3 | minus GLDAS land surface |
| `figures/fig1_global_tws_lev04.png` | 4 | total water storage |
| `figures/fig2_global_gws_lev04.png` | 4 | minus GLDAS land surface |

Plus `trends/basins_lev0{3,4}_trends.gpkg` and `.csv` with per-basin trend,
p-value, mascon count, GLDAS coverage, ice fraction and three-model spread, and
`trends/mascon_trends_gracefo.parquet` with all 41,168 mascons underneath.

## Method

Everything is computed in native mascon space. GSFC mascons are ~1 degree
equal-area cells and are the real resolution element, so GLDAS is averaged *up*
onto them rather than GRACE being interpolated *down*: interpolating up invents
structure the measurement does not have.

`GWS = TWS - (soil moisture + snow water equivalent + canopy)`, per model, using
the storage definitions in `depletion/attribution.py`, then averaged over the
three models. Baselines are removed only over the months the two records share.

Mascons are mapped onto basins on a 0.1 degree grid: each terrestrial cell
inherits the trend of the mascon containing it and is assigned to the basin it
falls inside, then each basin is a cos(lat)-weighted mean. That is an
area-weighted overlap without polygon intersection. The basin *series* is built
the same way and the trend fitted on it, rather than averaging per-mascon
trends -- both give the same slope, since the fit is linear in the data, but only
fitting the series gives an honest p-value. Trends use the package's
trend-plus-harmonics model with the Dawdy-Matalas autocorrelation correction.

## Results

Level 3: 292 basins, 247 with a value, covering 99.7% of level-3 land area.
Median 47 mascons per basin. Median TWS trend -1.23 mm/yr, median GWS
-1.27 mm/yr. 45% of basins have a TWS trend separable from zero.

Level 4: 1,342 basins, 1,283 with a value, 99.7% of area. Median 12 mascons per
basin. Median TWS -0.98, GWS -1.14 mm/yr. 50% separable.

Level 3 already explains 66% of the area-weighted variance in level-4 total
storage trends and 81% of the groundwater ones. The median level-4 basin sits
3.9 mm/yr from its level-3 parent, the 90th percentile 15.4 mm/yr. The largest
child-parent gaps are all in Greenland and the Canadian Arctic, where level 4
separates coastal ablation from interior accumulation that level 3 averages
together.

## Two things that would have been silent errors

**GSFC does not code ice as land.** Location codes are 90 ocean, 80 ice-free
land, and 1, 3, 4, 5 for Greenland, Antarctica and the ice caps. The regional
scripts in this project filter on `location == 80`, which on a global map drops
Greenland entirely. The filter here is "not ocean".

**A coverage test is not an ice test.** GLDAS carries snow water equivalent over
Greenland, so a "does GLDAS have a value here" check passes, and the groundwater
map happily rendered ice-sheet mass loss minus modelled snowpack as though it
were groundwater. Basins more than a fifth glacier or ice sheet are now withheld
from the groundwater map by what they are, not by whether a number exists:
5 basins at level 3, 47 at level 4.

## Validation

The mascon lookup was checked three ways: every one of the 41,168 mascons is hit
exactly once by a global grid, each mascon's own centre maps back to itself, and
the implied land fraction of the sphere is 0.282 against a truth near 0.29.

The whole GLDAS chain was cross-checked against the earlier Arabia work, which
built the same quantity by a different code path (OPeNDAP subsets, box-mean per
mascon, versus whole granules and a searchsorted assignment). Over 379 shared
mascons and 94 shared months the two agree to **0.0002 mm** worst case.

That check first appeared to fail badly, at 9.6% mean difference, because the
regional metadata numbers mascons from 1 and this pipeline indexes from 0. The
comparison was reading neighbouring mascons. Worth knowing before anyone joins
the regional tables to the global ones.

## Caveats

**7.7 years is short for a trend.** Half the basins are not separable from zero
and are hatched on the maps. A GRACE-FO-era trend is a decadal fluctuation as
much as a secular one; the 2018-2026 window opens near the end of a strong
Australian drought and closes after several wet years, which is most of why
Australia reads blue.

**The three land-surface models disagree by more than most of the signal.**
Median three-model spread is 4.2 mm/yr at level 3, against a median absolute
groundwater trend of 6.2. The groundwater map is a difference between a
measurement and a model ensemble, not a measurement.

**Neighbouring basins are not independent.** Adjacent mascons in this project
have consistently shown effective degrees of freedom of 1.2-1.8 regardless of
region size. At level 4 the median basin holds 12 mascons and 80 basins rest on
fewer than 3, so a level-4 basin is often reporting its mascon's number rather
than its own. The mascon count travels with every row for that reason.

**Leakage is not corrected.** GSFC ships leakage as an uncertainty, not a
correction, so every magnitude here is a floor and small trends are not resolved
above the solution's own systematic error.

**No Antarctica.** HydroBASINS does not cover it.

## Reproducing

```powershell
cd C:\Users\grupp\dark-water-extract\dark-water-main
$env:PYTHONPATH = "src"
$py = ".\.venv\Scripts\python.exe"

& $py E:\Water\_shared\gldas_download_global.py E:\Water\Global 2018-06 2026-03
& $py E:\Water\Global\tmp\01_global_gws.py        # mascon trends, TWS and GWS
& $py E:\Water\Global\tmp\02_basins.py 03         # basin aggregation
& $py E:\Water\Global\tmp\02_basins.py 04
& $py E:\Water\Global\tmp\03_maps.py 03           # the maps
& $py E:\Water\Global\tmp\03_maps.py 04
& $py E:\Water\Global\tmp\04_crosscheck.py        # against the Arabia run
& $py E:\Water\Global\tmp\05_level_compare.py     # level 3 vs level 4
```

HydroBASINS came from `data.hydrosheds.org/file/hydrobasins/standard/`, one
`hybas_<region>_lev0{3,4}_v1c.zip` per region, no credentials.

GES DISC retired the `hydro1` OPeNDAP endpoint some time after 2026-08-10; it now
returns 410 Gone, so `_shared/gldas_download.py`'s subsetting no longer works and
`gldas_download_global.py` pulls whole granules over HTTPS instead. The Earthdata
bearer token is read from the file named by `EARTHDATA_TOKEN_FILE`, never placed
on a command line and never written into any output.

## Sources

- GSFC mascon RL06v2.0 - https://earth.gsfc.nasa.gov/geo/data/grace-mascons
- GLDAS 2.1 monthly (NOAH025, VIC10, CLSM10) - NASA GES DISC
- HydroSHEDS HydroBASINS v1c - https://www.hydrosheds.org
