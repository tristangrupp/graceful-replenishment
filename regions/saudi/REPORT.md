# GRACE/GRACE-FO groundwater abstraction signal, Arabian Peninsula

**Product:** NASA GSFC global mascon solution RL06 v2.0 (`OBP-ICE6GD`), 1-arc-degree
equal-area mascons, April 2002 - March 2026.
**Cadence:** monthly. **Analysis date:** 2026-07-26.
**All outputs:** `E:\Water\Saudi\`

---

## 1. Headline

Over the Arabian Peninsula (222 GSFC land mascons, 2.752 million km^2) total water storage is
falling at an area-weighted **-0.546 cm equivalent water height per year** (p = 4e-62, trend
fitted jointly with annual + semi-annual harmonics, significance corrected for lag-1 residual
autocorrelation). That is **-15.0 km^3/yr**, and a cumulative **-13.4 cm** (about -360 km^3)
over the 24-year record.

The loss is not spread evenly. It concentrates in a coherent belt across north-central Saudi
Arabia, roughly **25-30 N, 37-45 E**, peaking at **-2.13 cm/yr** (mascon 9238, 27 N 43.31 E),
i.e. **-51 cm cumulative** at a single mascon. **163 mascons are flagged as abstraction
candidates**, together -14.2 km^3/yr.

The depletion belt coincides with the Saq/Saq-Ram sandstone outcrop and the Umm er Radhuma
carbonate system beneath the Qassim, Hail, Al Jawf and Tabuk centre-pivot irrigation districts.
**That coincidence is background knowledge, not something computed here** - see caveat C6.

Precipitation does not explain it. CHIRPS gives a median **93 mm/yr** over these mascons, and
refitting each trend with cumulative CHIRPS precipitation anomaly as a covariate leaves
**98% of the trend unexplained** (median `fraction_unexplained` = 0.98; > 0.97 for every one of
the top 20). Figure 3 shows the signature directly: storage falls in a near-perfect straight
line while the cumulative precipitation anomaly falls to about -25 cm by 2018 and then
*recovers to roughly zero* by 2026 - and storage keeps dropping at the same rate through the
recovery. A drought explanation would require storage to stabilise or rebound. It does not.

---

## 2. What was actually produced

### `raw/` (unmodified downloads)

| file | bytes | source |
|---|---|---|
| `gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd_halfdegree.nc` | 530,877,840 | `earth.gsfc.nasa.gov/sites/default/files/geo/` |
| `gsfc.glb_.200204_202603_rl06v2.0_obp-ice6gd.h5` | 172,188,426 | same host - **the native product, primary source here** |
| `gsfc_mascons_hdf5_format_rl06v2.pdf` | 519 KB | `earth.gsfc.nasa.gov/sites/default/files/2022-05/` |
| `chirps_v2p0_monthly_arabia_0p5deg.nc` | 2,387,884 | IRI Data Library, CHIRPS v2.0, server-side subset + 0.5 deg box-average |

Byte counts match the servers' `Content-Length`. No authentication was used or needed anywhere.

### `processed/`

- **`dataset_inventory.md`** - full inspection: variables, dims, coordinate conventions, units,
  attributes, time axis, fill values, masks, uncertainty fields, plus the interpolation finding
  and the scale-factor determination. Read this before using any of the data.
- **`arabia_mascons.nc`** - the per-mascon product (379 land mascons x 288 months).
- `arabia_halfdegree_landmasked.nc` - clipped, ocean-masked half-degree field, **secondary /
  cartographic only** (see C2).
- `signal_build_summary.json` - gap list, merge record, region definitions.

### `signals/` - the primary deliverable

- **`mascon_monthly_long.parquet`** - tidy: `mascon_id, month, solution_mid_date, decimal_year,
  observed, mission, lwe_cm, noise_2sigma_cm, dSdt_cm_per_yr`.
- `mascon_monthly_cmwe_wide.csv`, `mascon_monthly_noise2sigma_wide.csv` - months x mascons.
- `mascon_metadata.csv` - geometry, area, country, land/peninsula area fractions, leakage and
  noise terms, signal/noise variance per mascon.
- `regional_mean_series.csv` - area-weighted peninsula mean with GSFC's regional 95% uncertainty.

### `trends/`

- **`abstraction_candidates.csv`** - the machine-readable flagged table (163 rows).
- `all_mascons_flags.csv` - same columns for all 379, so exclusions are auditable.
- `mascon_trends_and_quality.csv` - every fitted and diagnostic quantity.
- `summary_stats.json`, `candidate_summary.json`
- `figures/fig1_trend_and_snr_map.png` ... `fig4_signal_quality.png`

---

## 3. Method, and the judgement calls in it

### 3.1 Clipping - the brief's box is not the Peninsula, so membership is by polygon

The brief's box (12-32 N, 34-60 E) was kept as the *processing* extent, but inspection showed it
is not a description of the Arabian Peninsula. Of the 379 GSFC land mascons whose centres fall
inside it, only 222 are actually on the Peninsula. The rest are **Iran (53), Sudan (26),
Ethiopia (17), Iraq (14), Eritrea (10), Egypt (7), Jordan (7), Israel (2), Djibouti (1)**.

This matters, not pedantically: **the five most strongly declining mascons in the box are all in
Iran** (-2.21 to -2.50 cm/yr, Fars/Kerman), stronger than anything in Saudi Arabia. A box-only
clip would have put Iranian groundwater depletion at the top of an "Arabian Peninsula" candidate
list. So Peninsula membership is defined by **> 50% of mascon area inside the union of Saudi
Arabia, Yemen, Oman, UAE, Qatar, Bahrain and Kuwait** (Natural Earth 10m). The box was not
shrunk - the non-peninsular mascons are retained in `all_mascons_flags.csv`, labelled, and
excluded from candidacy. Fig 1 shows both hotspots; only the Arabian one is outlined.

### 3.2 Land masking

The GSFC file carries **its own** `land_mask`, and the native product classifies every mascon
with a `location` code. Only `location == 80` (Land) mascons were used. JPL's land mask and
JPL's gain grid were **not** touched - different mascon geometry. This is why nothing in the
Red Sea, Persian Gulf or Arabian Sea enters any statistic, which matters given the Peninsula is
water on three sides. As a further check, GSFC adds the GAD ocean/atmosphere de-aliasing model
back **to ocean pixels only**, so ocean and land pixels are not even on the same footing.

### 3.3 Units

None needed. `solution/cmwe` and `lwe_thickness` are both already **cm equivalent water height**,
confirmed by the variable attribute (`units='cm'`) and the global attribute
`Water density used to convert to equivalent water height: 1000 kg/m^3`. Verified independently:
the mean over 2004-01..2009-12 is **exactly zero** at every land mascon, matching the stated
2004.0-2010.0 baseline, which also pins the sign convention (negative = water lost).

### 3.4 Scale / gain factor - GSFC distributes none, so amplitudes are biased low

**No gain factor was applied because GSFC does not publish one.** GSFC instead ships leakage as
an *uncertainty*: `leakage_2sigma` (cm) and `leakage_trend` (cm/yr), combined per the format
document as `|l_trend| + 2*sigma_l + 2*sigma_noise` for a single mascon, with only the stochastic
terms reduced by `sqrt(N/Z)`, Z = 22 mascons (~300 km), for a region.

Two consequences, stated plainly:

- **Mascon and basin amplitudes reported here are biased low** by an unquantified
  leakage-damping factor. Every trend below should be read as a magnitude floor.
- `leakage_trend` is a **symmetric uncertainty, not a signed bias**, so it was *not* subtracted.
  Area-weighted over the Peninsula it is **0.249 cm/yr**, and being systematic it does *not*
  shrink with region size. That is the dominant term in the peninsula trend uncertainty -
  larger than anything stochastic.

### 3.5 Sub-monthly duplicates and gaps

Exactly one calendar month, **2018-11**, contains two solutions, with non-overlapping windows
(2018-10-22..11-09 and 2018-11-10..11-30). They were **averaged, weighted by
`n_ref_days_solution`**, not truncated - so no duplicate month label exists. Their noise terms
were combined by the same weighted mean and deliberately **not** reduced by sqrt(2): the two
sub-monthly solutions share systematic error, so claiming error reduction would be unjustified.

**34 of the 288 calendar months are absent and were never interpolated.** They are carried as
explicit NaN on a complete monthly axis, with an `observed` boolean in every output. The largest
gap runs **2017-06-11 -> 2018-06-16, 370 days** - wider than the nominal GRACE/GRACE-FO gap
because 2018-05, 2018-08, 2018-09 and 2018-10 are missing too. Trends are fitted on the 254
observed epochs at their **true solution midpoints**, not at month centres - several early GRACE
windows are only 13-17 days long (e.g. 2002-05 covers May 3-17 only).

### 3.6 Flux form (dS/dt)

GRACE measures a storage *state*; its time derivative is the flux that closes
`dS/dt = P - ET - runoff - net abstraction`. `dSdt_cm_per_yr` is a centred difference across
observed neighbours, computed **only** where both neighbours are within 80 days - so no
derivative is manufactured across the mission gap or any missing month. Fig 2 (lower panel)
shows it. Note the honest caveat visible there: month-to-month differencing amplifies noise
enormously (monthly dS/dt scatters +/-20 cm/yr around a -0.5 cm/yr trend), so the 13-month
centred mean is the interpretable curve. Smoothed, it sits at about **-0.89 cm/yr during the
GRACE era and -0.67 cm/yr during GRACE-FO.**

### 3.7 Precipitation control - CHIRPS, actually run

GLDAS was unavailable (no Earthdata credentials), so `precipitation.py` could not be run on its
intended input. **CHIRPS v2.0 was substituted and the control was genuinely executed** - this is
not an unrun claim. CHIRPS monthly was pulled through the IRI Data Library with server-side
spatial subsetting and 0.5-degree box-averaging (2.4 MB instead of a 7.7 GB global file),
converted mm/month -> cm, averaged onto each mascon footprint, and accumulated with
`precipitation.cumulative_anomaly`.

One detail that matters: the running sum is computed on the **complete** CHIRPS monthly axis and
only then sampled at the GRACE epochs. Accumulating over GRACE's 34 missing months would have
corrupted the integral, because storage integrates flux continuously whether or not a satellite
solution exists. `precipitation.adjusted_trend` then refit each mascon with that covariate.
It succeeded for 356 of 379 mascons (23 have no CHIRPS land cell in footprint).

---

## 4. Signal quality - the part that was prioritised

| diagnostic | Peninsula median | reading |
|---|---|---|
| variance SNR (signal var / GSFC noise var) | **14.5** (min 2.4, max 421) | solution noise is not the limiting factor anywhere |
| GSFC noise sigma | 0.75 cm | |
| residual sd after trend + harmonics | 1.47 cm | |
| **residual / noise sd** | **1.99** | residuals are ~2x reported noise - real unmodelled *interannual* signal, not instrument noise |
| residual lag-1 autocorrelation | **0.41** | substantial; a naive OLS p-value would badly overstate confidence, which is exactly why `fit_trend`'s Dawdy-Matalas correction is used |
| annual amplitude | **0.95 cm** | tiny - hyper-arid, almost no seasonal cycle to confound the trend |
| regional 95% uncertainty (GSFC formula, Z=22) | 0.79 cm | vs a 13.4 cm cumulative signal |

The ratio of 1.99 is the useful number: after removing trend + annual + semi-annual, what is left
is about twice the formal noise. GRACE is not noise-limited here; it is limited by real
interannual variability we are not modelling. And the annual amplitude of 0.95 cm against a
13.4 cm cumulative drawdown is why the Arabian Peninsula is an unusually clean case - in a
monsoon or snowmelt basin the seasonal cycle is often larger than the entire depletion signal.

### Inter-mission offset - measured, reported, deliberately **not** applied

Fitting a GRACE-FO indicator alongside the trend gives a median absolute step of **1.38 cm**,
nominally significant at 5% for 150 of 222 mascons. **This was not corrected for**, because with
a 370-day gap the step and the trend are substantially collinear - a fitted step is as consistent
with genuine storage change during the unobserved year as with an instrument bias, and the data
cannot distinguish them. The honest cross-check is fitting each mission separately:

| segment | Peninsula regional trend |
|---|---|
| GRACE era (2002-04 .. 2017-06, n=163) | **-0.649 cm/yr** (p = 9e-49) |
| GRACE-FO era (2018-06 .. 2026-03, n=91) | **-0.503 cm/yr** (p = 8e-07) |
| full record | **-0.546 cm/yr** (p = 4e-62) |

Both eras decline strongly and independently, so the headline is not an artefact of splicing two
missions. The apparent **~22% slowdown** is consistent in direction with Saudi Arabia's phase-out
of domestic wheat production (2008-2016), but per the revised brief no changepoint or piecewise
fit was performed, and **a two-segment comparison across an 11-month gap cannot establish a
changepoint.** Treat the slowdown as suggestive, not demonstrated.

---

## 5. Flagged mascons

**`trends/abstraction_candidates.csv`** - 163 rows. Criteria, all four required:

1. `> 50%` of mascon area on the Arabian Peninsula;
2. `significant_decline` - trend < 0 and p < 0.05 from `fit_trend` (harmonics + autocorrelation correction);
3. `|trend| > leakage_trend` - the decline exceeds GSFC's own leakage trend uncertainty for that mascon;
4. `fraction_unexplained_by_precip > 0.5` - CHIRPS does not account for it.

Of 222 Peninsula mascons: 200 pass (2), and 163 pass all four. Total **-14.17 km^3/yr** over
2.020 million km^2. By country: **Saudi Arabia 127, Yemen 20, Oman 12, UAE 4.**

### Top 12

| mascon | lat | lon | country | trend (cm/yr) | GSFC leakage trend uncert (cm/yr) | cum. 2002-2026 (cm) | CHIRPS (mm/yr) | frac. unexpl. by precip | var SNR |
|---|---|---|---|---|---|---|---|---|---|
| 9238 | 27.0 | 43.31 | Saudi Arabia | **-2.129** | 0.974 | -50.9 | 153 | 0.99 | 355 |
| 9246 | 26.0 | 42.91 | Saudi Arabia | **-2.128** | 0.993 | -50.9 | 138 | 0.99 | 349 |
| 9247 | 26.0 | 44.02 | Saudi Arabia | **-2.115** | 1.009 | -50.6 | 167 | 0.98 | 381 |
| 9237 | 27.0 | 42.19 | Saudi Arabia | **-2.104** | 0.918 | -50.3 | 111 | 0.99 | 366 |
| 9239 | 27.0 | 44.44 | Saudi Arabia | -1.876 | 0.776 | -44.9 | 154 | 0.97 | 282 |
| 9158 | 30.0 | 37.62 | Saudi Arabia | -1.869 | 0.746 | -44.7 | 87 | 1.00 | 257 |
| 9228 | 28.0 | 41.45 | Saudi Arabia | -1.854 | 0.662 | -44.4 | 101 | 1.00 | 328 |
| 9245 | 26.0 | 41.80 | Saudi Arabia | -1.841 | 0.710 | -44.0 | 108 | 0.99 | 271 |
| 9161 | 29.0 | 38.41 | Saudi Arabia | -1.840 | 0.666 | -44.0 | 97 | 1.00 | 264 |
| 9236 | 27.0 | 41.06 | Saudi Arabia | -1.832 | 0.627 | -43.8 | 98 | 1.00 | 272 |
| 9248 | 26.0 | 45.14 | Saudi Arabia | -1.814 | 0.766 | -43.4 | 146 | 0.97 | 307 |
| 9220 | 29.0 | 39.55 | Saudi Arabia | -1.801 | 0.619 | -43.1 | 114 | 1.00 | 297 |

Every one of these has |trend| roughly **2-3x** its own leakage trend uncertainty, variance SNR
in the hundreds, and essentially nothing explained by precipitation.

**Excluded but worth recording** (outside the Peninsula, in `all_mascons_flags.csv`): the box's
strongest declines are Iranian - 9401 (29 N, 55.61 E) **-2.499 cm/yr**, 9400 **-2.469**,
9405 **-2.276**, 9467 **-2.207**, 9462 **-2.207**.

---

## 6. Sanity check against published GRACE literature

| quantity | this analysis | published | agreement |
|---|---|---|---|
| Peninsula-wide storage trend | **-5.46 mm/yr** (TWS) | **-4.90 +/- 0.32 mm/yr** (groundwater storage), peninsula-wide GRACE assessments | **agrees**; mine is TWS not GWS, and should be slightly more negative |
| Saq aquifer core | **-1.6 to -2.13 cm/yr** at mascon scale (~12,400 km^2) | Fallatah et al.: Saq TWS **-9.05 mm/yr**, GWS **-6.52 mm/yr**, averaged over the whole 520,000 km^2 Saq-Ram domain | **consistent** - a 12,400 km^2 hotspot running 2-3x the 520,000 km^2 basin mean is expected, not a discrepancy |
| Saq-Ram net storage change | ~-1.1 to -2.1 cm/yr over the belt | HESS 26, 5757 (2022) budget: pumping 15.7 +/- 1.1 mm/yr, natural recharge 2.4 +/- 1.4, artificial recharge 2.2, natural discharge 0.3 -> **net ~-11.4 mm/yr** | **agrees** |
| Peninsula volume | **-15.0 km^3/yr** | one search result quotes "-2 +/- 0.13 km^3/yr for the Arabian Peninsula region" | **does not agree** - but that figure is mutually inconsistent with the -4.90 mm/yr areal rate above unless it refers to a ~40,000 km^2 sub-basin. -0.49 cm/yr over 2.75 Mkm^2 is 13.5 km^3/yr, which matches mine. I judge the -2 km^3/yr to be a sub-domain figure, and flag that I did not resolve it from the abstract alone. |

**A material adverse finding I am obliged to report:** the HESS 2022 Saq-Ram study
**explicitly excluded the GSFC solution** - the product used here - stating "The negative natural
recharge, i.e. evaporation losses from the water table, obtained with the GRACE-GSFC solution is
not realistic", implying ~1.1 mm/yr of implausible groundwater evaporation against a theoretical
~0.07 mm/yr for a 150 m vadose zone. They attribute it to "differences in the treatment of the
raw GRACE data" and note the three centres diverge increasingly after 2012 owing to "diverse
shape and size of the Mascons, and the various methods of eliminating signal leakage effects".

Read literally, that implies **GSFC may run ~0.11 cm/yr more negative than JPL/CSR over this
specific domain.** That is ~5% of the -2.1 cm/yr hotspot values (immaterial) but ~20-30% of the
-0.34 cm/yr Peninsula *median* (material). **I did not run a JPL or CSR cross-check** - see U1.

---

## 7. Caveats

**C1 - These are TWS trends, not groundwater trends.** No land-surface model was subtracted, so
soil moisture, surface water and (negligible here) snow remain in the signal. Every published
comparison above that quotes "GWS" removed a model; I could not, because that needs GLDAS and
therefore Earthdata credentials. In hyper-arid Arabia the soil-moisture trend is small, which is
why the numbers still line up - but **"groundwater" is an inference, not a measurement, here.**

**C2 - Do not use the half-degree grid for quantitative per-mascon work.** Every land cell in it
has a unique time series, i.e. it is interpolated from the 1-arc-degree mascons and does not
preserve mascon identity. An SVD of its 1533 core land cells needs only **4 modes for 95%** of
variance. `arabia_halfdegree_landmasked.nc` is provided for maps only; all numbers here come
from the native HDF5.

**C3 - Amplitudes are biased low.** No gain factor exists for GSFC (section 3.4). All magnitudes
are floors.

**C4 - Leakage uncertainty is systematic and does not average down.** At 0.249 cm/yr
(area-weighted) it dominates the Peninsula trend uncertainty. A defensible statement of the
headline is **-0.546 +/- 0.249 cm/yr**, uncertainty-dominated by leakage.

**C5 - Recharge is NOT zero, and I did not assume it was.** The temptation in a fossil-aquifer
region is to treat storage decline as pure accumulated withdrawal. The published Saq-Ram budget
says otherwise: natural recharge **2.4 +/- 1.4 mm/yr** plus irrigation return flow
**~2.2 mm/yr** against **15.7 mm/yr** pumping - recharge is ~30% of abstraction, small but not
negligible. Therefore **the observed dS/dt is a lower bound on gross abstraction**, not an
estimate of it. Gross pumping in the depletion belt is plausibly ~30-40% larger than the storage
loss I measure. Recharge to the deep Saq/Umm er Radhuma is near-zero *on human timescales*, but
"near-zero" is an assumption about the deep system, not a measurement, and the shallow/return-flow
component is demonstrably non-zero.

**C6 - Aquifer attribution is background knowledge, not computed.** No aquifer polygon layer was
used (WHYMAP/IGRAC transboundary aquifer shapefiles were not pursued). The Saq / Umm er Radhuma
association rests on the coincidence of the mapped hotspot with published aquifer extents and
irrigation districts, which I did not verify geometrically. `abstraction_candidates.csv`
therefore carries coordinates and countries, not aquifer names.

**C7 - CHIRPS caveat.** CHIRPS blends satellite thermal-IR with station data. Gauge density in
the Arabian interior is very low, so CHIRPS there is largely satellite-inferred and its
*interannual* skill over the Rub al Khali and Nafud is not independently validated here. The
control is real and it was run, but it is a weaker instrument in this region than it would be in,
say, East Africa. Also note the control's own logic: with `fraction_unexplained ~0.98`, CHIRPS
is telling us precipitation has almost no explanatory power - which in a place with 93 mm/yr and
low interannual variance is nearly a null test by construction. The stronger evidence is the
qualitative one in Fig 3 (storage falls monotonically *through* a precipitation recovery).

**C8 - p-values are absurdly small and should not be read literally.** Values like 4e-62 come
from a model that assumes the autocorrelation correction fully captures the error structure. It
does not. Read them as "highly significant", nothing more precise.

**C9 - Inter-mission step not corrected** (section 4). If a genuine ~1.4 cm bias exists, the
full-record trend is affected at roughly 0.06 cm/yr.

**C10 - Country assignment is by mascon-centre point-in-polygon**, while Peninsula membership is
by area fraction. A ~12,400 km^2 mascon straddles borders; `frac_area_arabian_peninsula` is in
the metadata so any user can re-threshold.

**C11 - Monthly is the only meaningful cadence** and no attempt was made at weekly. All mascon
products are monthly; sub-monthly GRACE solutions are ~degree-40 Kalman-smoothed fields that
cannot resolve a 1-degree mascon. Nothing here was interpolated to weekly.

---

## 8. What I could not complete

**U1 - No inter-product cross-check (the most important gap).** Given the HESS 2022 finding in
section 6, the single most valuable next step is repeating this with **CSR RL06.3 mascons**,
which are downloadable without login from
`https://www2.csr.utexas.edu/grace/RL0603_mascons.html`. Per the brief I did not guess a URL, and
I did not spend the budget fetching one. JPL is out of reach entirely without Earthdata
credentials. **Every number here rests on a single mascon solution**, one that at least one
peer-reviewed study rejected for this exact aquifer.

**U2 - No GLDAS, so no TWS -> GWS separation** (C1). `attribution.py` in the reference package
was not run at all.

**U3 - `precipitation.py` was run on CHIRPS, not its intended GLDAS input.** The module's
`precipitation_depth()` (which converts GLDAS kg/m^2/s rates) was bypassed; only
`cumulative_anomaly()` and `adjusted_trend()` were used, fed CHIRPS depths converted to cm
directly. Same statistical model, different data source.

**U4 - No changepoint / piecewise analysis.** Explicitly dropped on instruction. The
GRACE-vs-GRACE-FO segment comparison in section 4 is a byproduct of the mission split, not a
changepoint test, and must not be cited as one.

**U5 - No aquifer polygons** (C6).

**U6 - No in-situ well validation** - no piezometric data was sought, so nothing here is
independently ground-truthed.

**U7 - `zonal.py` was not used.** It aggregates a lat/lon-gridded trend Dataset to polygons; the
per-mascon product has a `mascon` dimension instead, and with no aquifer polygons to aggregate to
there was nothing for it to do. Country-level aggregation was done directly.

---

## 9. Reproducing

```powershell
cd C:\Users\grupp\dark-water-extract\dark-water-main
$env:PYTHONPATH="src;E:\Water\Saudi\tmp\pylibs"
.\.venv\Scripts\python.exe E:\Water\Saudi\tmp\01_inspect.py             # inventory
.\.venv\Scripts\python.exe E:\Water\Saudi\tmp\02_recon.py               # mascon-identity recon
.\.venv\Scripts\python.exe E:\Water\Saudi\tmp\03_recon2.py              # interpolation proof + SVD
.\.venv\Scripts\python.exe E:\Water\Saudi\tmp\06_build_signals.py       # per-mascon signals
.\.venv\Scripts\python.exe E:\Water\Saudi\tmp\07_quality_trend_precip.py
.\.venv\Scripts\python.exe E:\Water\Saudi\tmp\08_grid_candidates_figs.py
.\.venv\Scripts\python.exe E:\Water\Saudi\tmp\09_figs_fix.py
```

`h5py` and `pypdf` were installed to `E:\Water\Saudi\tmp\pylibs` via `pip --target`, deliberately
**not** into the reference package's `.venv`. Nothing under `C:\Users\grupp\dark-water-extract`
was modified. `trend.fit_trend`, `precipitation.cumulative_anomaly` and
`precipitation.adjusted_trend` were imported and used unmodified.

## References consulted

- Loomis, Luthcke & Sabaka (2019), *Regularization and error characterization of GRACE mascons*, J. Geod. 93, 1381-1398. https://doi.org/10.1007/s00190-019-01252-y
- GSFC mascon HDF5 format description RL06v2.0 - https://earth.gsfc.nasa.gov/sites/default/files/2022-05/gsfc_mascons_hdf5_format_rl06v2.pdf
- HESS 26, 5757 (2022), *Influence of intensive agriculture and geological heterogeneity on the recharge of an arid aquifer system (Saq-Ram, Arabian Peninsula) inferred from GRACE data* - https://hess.copernicus.org/articles/26/5757/2022/
- Funk et al., CHIRPS v2.0, via IRI Data Library - https://iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/
