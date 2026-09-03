# Water storage change in Nuevo Leon, Mexico, from GRACE/GRACE-FO

**Products:** NASA GSFC global mascon RL06 v2.0 (`OBP-ICE6GD`), native 1-arc-degree
equal-area mascons, 2002-04 - 2026-03, and - as an independent check on every headline -
**CSR RL06.3** mascons, 0.25 deg grid, 2002-04 - 2026-05.
**External data:** CONAGUA SINA daily reservoir monitoring, TWDB Water Data for Texas,
CHIRPS v2.0, **GLDAS 2.1 NOAH / VIC / CLSM** monthly land-surface storage.
**Analysis date:** 2026-07-27; **revised 2026-08-10** with the GLDAS attribution
(section 4.4). **All outputs:** `E:\Water\NuevoLeon\`.

---

## 1. Headline

**The reservoir component is not a nuisance term here; it is the signal.** The three
reservoirs supplying Monterrey hold **1,458 hm3** at conservation level, which is
**117.6 mm** of equivalent water height over a single 12,400 km2 GSFC mascon, against a
**16.7 mm** GRACE 2-sigma noise floor - a ratio of **7.0**. Their observed 2002-2026 range,
1,848 hm3, is **149.0 mm**, a ratio of **8.9**. Elsewhere in the window it is worse:
La Amistad, Vicente Guerrero and Falcon are each **265-325 mm** of mascon-mean storage,
larger than the entire post-2020 drying signal this study set out to characterise.

That number decides the study, and it was computed first. **Reservoirs must be removed,
and they can be:** CONAGUA's public API yields a complete monthly reservoir record from
2002-04 (not 2007, as the portal's own description says), which after one substitution -
see section 3.2 - is subtractable from GRACE directly.

**Doing so removes two-thirds of the Nuevo Leon trend and leaves nothing defensible.**
Over the 240 months where both records exist (2002-04 .. 2025-04), area-weighted by each
mascon's share of the state:

| series | trend | p | fraction of TWS trend |
|---|---|---|---|
| GSFC total water storage | **-1.63 mm/yr** | 0.11 | - |
| measured reservoir component | -1.09 mm/yr | 0.06 | **67%** |
| **residual (TWS - reservoirs)** | **-0.54 mm/yr** | **0.51** | 33% |
| CSR total water storage | -2.59 mm/yr | 1.9e-4 | - |
| **CSR residual** | **-1.50 mm/yr** | 0.0025 | 42% |

**Neither residual can be called groundwater.** Three reasons, in order of severity:

1. **GSFC's own leakage-trend uncertainty for these footprints is 3.75 mm/yr**,
   area-weighted over Nuevo Leon. That is larger than the total-storage trend and seven
   times the residual. The state-scale trend is **not resolved above the solution's own
   systematic error**, whatever its p-value says.
2. ~~**Soil moisture was never removed**~~ - **resolved 2026-08-10.** Earthdata
   credentials arrived, GLDAS was subtracted over the full record, and the answer
   sharpens rather than softens the conclusion. See immediately below and section 4.4.
3. The two solutions disagree on whether any residual survives at all: GSFC says
   -0.54 mm/yr (p = 0.51, and +0.32 mm/yr once precipitation is controlled), CSR says
   -1.50 mm/yr (p = 0.003, -0.91 mm/yr after the precipitation control, p = 0.028).

### With soil moisture removed, the residual is not a decline at all

Adding the GLDAS term completes the budget on the same 240 months and the same
state-weighted footprint as the table above:

| term | trend | p |
|---|---|---|
| GSFC total water storage | **-1.63 mm/yr** | 0.11 |
| measured reservoir component | -1.09 mm/yr | 0.06 |
| GLDAS soil moisture + snow + canopy | -1.33 mm/yr | 0.10 |
| **groundwater, what is left** | **+0.79 mm/yr** | **0.07** |

**The sign flips.** Reservoirs and soil moisture between them account for more than the
whole total-storage trend, and the remainder points slightly upward. That is not a claim
that Nuevo Leon is gaining groundwater: the three land-surface models disagree on the
sign of the remainder (**+1.75 NOAH, +0.88 VIC, -0.26 CLSM** mm/yr), and every term in
the table is smaller than the 3.75 mm/yr leakage floor. Nothing here is resolved.

**The 2022-2024 excursion is a drought, and it is refilling.** In the groundwater term
the pre-2020 mean is -0.8 mm, the trough is **-53.8 mm in 2024-09**, and the seven months
after it average -22.4 mm - **59% of the drop already recovered**, with the record ending
at the reservoir cut-off rather than at a settled level. An aquifer being mined does not
do that.

The negative headline therefore stands, and now stands on a completed budget rather than
on a missing term.

**The most defensible statement this study supports is a negative one:** the Monterrey
water crisis of 2022 is visible in GRACE, but once the reservoirs that actually caused it
are subtracted, the remaining storage change over Nuevo Leon is smaller than the
measurement's own systematic uncertainty. **There is no GRACE-detectable groundwater
depletion signal at the state scale in this record.** That is a real result, not a failure
of the method - but it is the opposite of the result the framing anticipated.

### The post-2020 gradient: half confirmed, half an artefact

Panel C of the prior `trends/decorrelation.png` showed mascons distant from the region
centre falling to about -150 mm after 2020 while the central reference held near -60 mm.
That contrast is real in both solutions but **weaker than it looked, and the two solutions
disagree about where it lies.**

| | GSFC | CSR |
|---|---|---|
| mean 2020-2026 anomaly, > 300 km from centre | -107.8 mm | -82.2 mm |
| mean 2020-2026 anomaly, <= 150 km from centre | -42.4 mm | -45.9 mm |
| **far - near** | **-65.4 mm** | **-36.4 mm** |
| variance in post-2020 level explained by distance from centre | r2 = 0.08 (p = 0.07) | r2 = 0.18 (p = 0.007) |
| ... by latitude | **r2 = 0.28 (p = 4e-4)** | r2 = 0.001 (p = 0.85) |
| ... by longitude | r2 = 0.002 (p = 0.77) | **r2 = 0.70 (p = 2e-11)** |

Distance from the centre explains at most 18% of the between-mascon variance in either
solution, so **"distance from centre" is the wrong variable.** In GSFC the pattern is a
north-south one: the nine mascons on the **United States** side of the Rio Grande average
**-10.16 mm/yr** against **-2.88 mm/yr** for the 31 Mexican ones. **CSR does not reproduce
that split at all** - US -2.53 mm/yr, Mexico -3.62 mm/yr, i.e. the sign of the contrast
reverses.

And the split lands exactly on a seam in the GSFC product. GSFC's `mascon/basin` field
takes the value **1004** for every mascon north-east of the Rio Grande in this window and
**2001 / 2004 / 2005** for every mascon south-west of it; the code boundary traces the
river from Del Rio to Rio Grande City. Regularization is applied within those regions.
Quantitatively:

| variance in per-mascon trend explained by | GSFC | CSR |
|---|---|---|
| the GSFC `basin` code | **eta2 = 0.61** | eta2 = 0.40 |
| US vs Mexico | **eta2 = 0.47** | **eta2 = 0.04** |
| latitude | r2 = 0.28 | r2 = 0.005 |

**A contrast that is organised by the processing centre's own region codes at eta2 = 0.47
in one solution and eta2 = 0.04 in another is not safe to publish as hydrology.** The
southern, Mexican limb of the gradient is confirmed by CSR (median per-mascon series
r = 0.82, trends within ~1-2 mm/yr west of 100.3 W). The northern, Texan limb - the
strongest part, and the part that drove the -150 mm in Panel C - is not.

---

## 2. What was produced

```
inventory/  SYSTEM_NOTES.md                     the Phase-1 system description
            reservoir_magnitude.json            the decision number and its inputs
            dams_in_region.csv                  32 dams, geometry, capacity in hm3 and mm
            reservoir_per_mascon.csv            per-mascon reservoir totals vs GRACE noise
            international_reservoir_source_check.json
            mascon_land_fraction.csv
raw/        conagua_presas/*.json               292 monthly snapshots (277 populated)
            twdb_amistad.csv, twdb_falcon.csv   whole-lake storage, 1968-2026
            chirps_v2p0_monthly_nuevoleon_0p5deg.nc
            chirps_landmask_native.nc
            gldas/{noah,vic,clsm}/*.nc4         288 monthly subsets each, 2002-04..2026-03
processed/  gldas_{noah,vic,clsm}_monthly.nc    the same, concatenated
signals/    mascon_monthly_long.parquet         tidy per-mascon monthly GRACE product
            mascon_metadata.csv, gaps.json
            reservoir_absolute_mm.parquet, reservoir_anomaly_mm.parquet
            reservoir_dams_reporting.parquet, reservoir_defined_mask.parquet
            tws_mm.parquet, tws_minus_reservoir_mm.parquet, csr_tws_mm.parquet
            chirps_monthly_cm.parquet, chirps_cumulative_anomaly_cm.parquet
            regional_series.csv, regional_series_with_csr.csv, nuevo_leon_series.csv
            monterrey_system_storage_hm3.csv, dsdt_nuevo_leon.csv
            gldas_decomposition_series.csv      the four terms, state-weighted
            gldas_groundwater_by_model.csv      the residual per land-surface model
trends/     mascon_decomposition.csv            per-mascon decomposition, all 40
            post2020_gradient.csv               the Phase-4 table, GSFC + CSR + basin code
            nuevo_leon_headline.json, decomposition_summary.json
            gradient_summary.json, basin_block_check.json, dsdt_summary.json
            gldas_decomposition_summary.json    all terms, per model, both windows
            figures/fig1..fig6 .png
scripts/    01, 01b (CONAGUA), 02 (signals), 03, 04 (TWDB), 05 (reservoir series),
            06 (decomposition), 07 (gradient + CSR), 08 (basin check), 09 (headline),
            10 (figures), 11 (dS/dt), 12 (this report), 13 (SMAP), 14 (SMAP figure),
            15 (GLDAS decomposition), 16 (GLDAS figure)
```

The GLDAS downloader is shared across regions and lives at
`E:\Water\_shared\gldas_download.py`.

Figures: **fig1** the Phase-1 magnitude calculation; **fig2** the decomposition;
**fig3** GSFC vs CSR and the basin seam; **fig4** timing against the drought window;
**fig5** the SMAP decomposition; **fig6** the GLDAS decomposition and the recovering
excursion.

---

## 3. Method

### 3.1 GRACE handling

Native HDF5 only; the interpolated half-degree grid was never opened. `location == 80`
selects the 40 land mascons in 22-29 N, 102.7-97.0 W; the 14 Gulf mascons in the same box
are excluded. `solution/cmwe` is already cm equivalent water height on a 2004-01 .. 2009-12
baseline; converted to mm, no other unit work. **33 of the 288 calendar months are absent
and were never interpolated** - carried as explicit NaN with an `observed` flag. The
largest gap is 2017-07 .. 2018-05. No calendar month in this window contains two solutions,
so the duplicate-weighting path never fires.

`dSdt_cm_per_yr` is a centred difference at the **true solution midpoints**, computed only
where both neighbours are within 80 days, so no derivative crosses the mission gap. It
exists for 241 of 255 observed months. Monthly dS/dt has a standard deviation of
**184 mm/yr** about a -1.6 mm/yr trend, so only the 13-month centred mean is interpretable:
it runs -158 to +112 mm/yr, averages **-22.5 mm/yr through the drought window** and
-4.8 mm/yr over 2020 onward.

Trends everywhere use `depletion/trend.py::fit_trend` - trend fitted jointly with annual
and semi-annual harmonics, p-value corrected for lag-1 residual autocorrelation
(Dawdy & Matalas). No raw OLS was used.

### 3.2 The reservoir series, and the one place the official data breaks

CONAGUA SINA's public app calls
`https://sinav30.conagua.gob.mx:8080/PresasPG/presas/reporte/YYYY-MM-DD`, discovered by
reading the app's JavaScript bundle rather than guessed. It returns per-dam
`almacenaactual` (hm3) with coordinates. 292 monthly snapshots were pulled; **277 are
populated, spanning 2002-04-15 to 2025-04-15.** Every date after that returns an empty
array - verified at 2025-04-28, 2025-05-02, 2025-06-10, 2025-09-15, 2026-01-20 and
2026-07-20 - so **the reservoir correction stops 11 months before GRACE does.** Every
paired statistic in this report is computed on the months where the reservoir record
exists, and the unadjusted trend is refitted on exactly those months so the two are never
compared over different records.

**The two international Rio Grande reservoirs cannot be taken from SINA.** Its
`almacenaactual` for La Amistad and Falcon alternates between the whole-lake volume and
Mexico's treaty share: the ratio to TWDB's whole-lake figure is ~1.00 in 2007 and
2009-2017 but 0.06-0.58 in 2002-2006, 2008 and 2018-2025, with the clearest step between
the 2018-03-15 and 2018-05-15 snapshots (Amistad 2,484.7 -> 494.5 hm3; Falcon
1,709.4 -> 231.8). GRACE weighs the physical water, not an accounting balance. **TWDB
`reservoir_storage` was substituted for both**, identified as the whole-lake quantity by
matching SINA to 0.06% and 0.10% on 2018-03-15 in the period when SINA is also whole-lake.
(TWDB's `conservation_storage` column is the *Texas* share and does not match; it was not
used.)

Dams are keyed by rounded coordinate, not by `clavesih` - 185 of 212 SINA codes appear at
more than one coordinate over the record. A mascon-month is used only if **every** dam in
that mascon reported; zero-filling a non-reporting dam would have manufactured a cliff at
2025-05 that looked like every reservoir in Mexico emptying at once.

Reservoir volumes are converted to mm over each mascon's own area and re-referenced to the
**same 2004-01 .. 2009-12 baseline GSFC uses**, then subtracted month by month.

### 3.3 Precipitation control

CHIRPS v2.0 monthly, pulled through the IRI Data Library with server-side subsetting and
0.5 deg box-averaging (no authentication, 462 KB). Averaged onto each mascon box,
converted to cm, accumulated with `precipitation.cumulative_anomaly` **on the complete
CHIRPS monthly axis** and only then sampled at GRACE epochs - accumulating over GRACE's
missing months would corrupt the integral. `precipitation.adjusted_trend` then refits each
series with that covariate. Because `adjusted_trend` drops any column containing a NaN, it
is called **one mascon at a time** on that mascon's own complete months; passing the whole
frame would have silently deleted every mascon with a short reservoir record.

Mascon-mean rainfall over the window runs 300-1,182 mm/yr, and 343-717 mm/yr across the
Nuevo Leon mascons - this is a semi-arid to sub-humid region with a real seasonal cycle,
not a hyper-arid one.

### 3.4 CSR cross-check

CSR's time attribute is spelled `Units` with a capital U, so xarray's CF decoder skips it
and every timestamp collapses to 1970. Opened with `decode_times=False` and rebuilt from
"days since 2002-01-01". CSR is then cosine- and **land-fraction-weighted** onto the
identical GSFC mascon boxes, using a 0.05 deg land mask derived from CHIRPS' own ocean
NaNs, because the eastern boxes straddle the Gulf coastline. The mask changed the coastal
CSR values by less than 10 mm and **did not** remove the GSFC/CSR disagreement there, so
ocean contamination is not the explanation for it. CSR was re-referenced to the GSFC
baseline before comparison.

### 3.5 Region definition

Results are reported **weighted by each mascon's area fraction inside the Nuevo Leon state
polygon** (`H:\water intelligence\soilmoisture\data\nuevo_leon.geojson`), not by the
processing box. This matters: 15 mascons contribute, effective area 65,178 km2 against the
state's ~64,200 km2, and the box-wide trend (-4.52 mm/yr) is four times the state trend
because the box is dominated by Texas and Coahuila mascons that behave differently.

### 3.6 GLDAS attribution

Earthdata credentials arrived on 2026-08-10, so the subtraction
`depletion/attribution.py` implements could finally be run. GLDAS 2.1 was pulled through
GES DISC OPeNDAP, subset to lat 20.5-30.5, lon -104.5 to -95.5 and to the variables the
package needs, which makes the whole three-model 24-year record 12 MB rather than several
gigabytes. All three models cover **2002-04 .. 2026-03**, matching GRACE month for month.

Non-groundwater storage is the package's own definition per model: NOAH sums four soil
layers to 200 cm, VIC three, CLSM its root-zone field, each plus snow water equivalent
and canopy interception. Fields are averaged onto each mascon box with cos(lat) weights
rather than GRACE being interpolated onto the finer GLDAS grid - the mascon is the native
resolution element, and interpolating up would invent structure the measurement does not
have. Baselines are removed only over the months the two records share, per the fix in
`groundwater_storage_anomaly`.

Reservoirs are still subtracted separately. GLDAS models no reservoir storage, so without
that step the Monterrey system's drawdown would sit inside the "groundwater" term.

Two constraints on the window. Mascons with no monitored dam enter with a reservoir
anomaly of **zero**, which is a value rather than a gap, so the footprint stays the 15
state mascons and the total remains comparable with section 1. And a month is used only
when the mascons that reported carry **at least 90% of the total weight** - which holds
from 2002-10 to 2025-04, the same 240 months the reservoir work used, and excludes the
post-cutoff months where only one dam of seven still reports.

### 4.1 Per mascon, Nuevo Leon

| mascon | centre | in NL | TWS | reservoir | residual | p | frac. unexpl. by precip | CSR TWS | GSFC-CSR r |
|---|---|---|---|---|---|---|---|---|---|
| 3152 | 26 N, 99.8 W | 97% | -1.76 | -1.92 | **+0.66** | 0.44 | 2.16 | -2.23 | 0.79 |
| 3154 | 25 N, 99.9 W | 91% | +1.15 | -0.67 | **+1.97** | 0.046 | 1.40 | -2.04 | 0.64 |
| 3235 | 24 N, 100.1 W | 82% | +0.26 | 0 | +0.26 | 0.79 | 2.24 | -2.44 | 0.72 |
| 3151 | 26 N, 100.9 W | 55% | -2.10 | 0 | **-2.10** | 0.028 | 1.23 | -3.35 | 0.81 |
| 3149 | 27 N, 100.7 W | 48% | -4.87 | +0.01 | **-4.88** | 1e-5 | 0.94 | -4.19 | 0.86 |
| 3150 | 27 N, 99.6 W | 43% | -6.57 | -4.44 | -1.76 | 0.32 | 1.36 | -2.97 | 0.83 |
| 3240 | 25 N, 98.8 W | 34% | +1.86 | 0 | +1.86 | 0.075 | 2.18 | -0.81 | 0.64 |
| 3153 | 26 N, 98.6 W | 32% | -1.86 | -0.48 | -1.14 | 0.14 | 0.49 | -1.10 | 0.73 |
| 3231 | 25 N, 101.0 W | 20% | -0.92 | 0 | -0.92 | 0.35 | 1.12 | -3.34 | 0.76 |

(mm/yr; residual = TWS - reservoir; full table with all 40 mascons in
`trends/mascon_decomposition.csv`.)

Three things stand out.

* **The Monterrey mascon's whole decline is its reservoir.** Mascon 3152 (97% in Nuevo
  Leon, containing El Cuchillo and the eastern conurbation) has a TWS trend of -1.76 mm/yr
  and a reservoir trend of -1.92 mm/yr. The residual is **+0.66 mm/yr**, not significant.
  Storage under Monterrey is not measurably falling once the reservoir is accounted for.
* **The two mascons with a significant residual have no dams in them.** 3151 (western
  Monterrey / Sierra Madre, -2.10 mm/yr, p = 0.028) and 3149 (northern Nuevo Leon,
  -4.88 mm/yr, p = 1e-5). Both are confirmed in sign and rough magnitude by CSR
  (-3.35 and -4.19 mm/yr), and CHIRPS explains little of either (fraction unexplained 1.23
  and 0.94). **These are the only two places in Nuevo Leon where this analysis finds an
  unexplained storage decline** - and both are still far smaller than the reservoir signal
  next door. 3151's decline is smaller than its own leakage-trend uncertainty (3.28 mm/yr)
  and cannot be resolved; 3149's (0.67 mm/yr) is exceeded by a factor of seven, making it
  **the single most defensible candidate in the region** - and it is not the Monterrey
  mascon.
* **Fractions unexplained above 1** (3152, 3154, 3235, 3151, 3240) mean storage fell - or
  failed to rise - *through* a wet period. That is normally a strong abstraction signature.
  Here it should not be read that way, because the trends concerned are small and mostly
  insignificant, and because CHIRPS' interannual skill in this region is not validated here.

### 4.2 The 2022 crisis, and its timing

The drought window used is **2022-07 to 2023-04**, taken unchanged from the independent
SPI-12 / SMAP study in `H:\water intelligence\soilmoisture` (CHIRPS 1990-2010 baseline,
Thom-MLE gamma, onset at regional-mean SPI-12 < -1). **It was not computed here.**

Measured reservoir behaviour through it, from CONAGUA:

| reservoir | minimum | date | % of NAMO capacity |
|---|---|---|---|
| Cerro Prieto | 1.8 hm3 | 2022-07-15 | **0.6%** |
| La Boca | 2.9 hm3 | 2022-06-15 | **8.2%** |
| El Cuchillo | 447.6 hm3 | 2022-08-15 | 39.9% |
| **combined system** | **453.4 hm3** | **2022-08** | **31.1%** |

GRACE's response is consistent in timing and lags as physics requires:

| quantity | value |
|---|---|
| Nuevo Leon TWS drawdown during the window, vs the 2015-2019 mean | **-40.7 mm** (GSFC), -53.9 mm (CSR) |
| of which measured reservoir drawdown | **-15.7 mm (39%)** |
| residual drawdown (soil moisture + groundwater + unmonitored) | -25.0 mm (GSFC), -38.6 mm (CSR) |
| storage minimum | **2023-09, -105.1 mm** (GSFC); 2024-05, -114.9 mm (CSR) |
| 13-month smoothed dS/dt through the window | **-22.5 mm/yr** |

**Storage bottoms out five months after the SPI-12 window closes**, and CSR puts the
minimum a further eight months later still. That is the expected behaviour of an integrator
driven by a flux deficit, and it is a useful independent corroboration that the GRACE
series is responding to the same event the soil-moisture study identified. It is also a
warning against reading a storage minimum as a drought date.

**Note the reservoir contribution during the crisis (39%) against its contribution to the
long-term trend (67%).** Over the crisis specifically, most of the storage loss was *not*
reservoirs - 25 mm of the 41 mm was something else. Over the full record, most of it was.
Those are compatible: the reservoirs were already low before the drought and refilled
sharply in September 2022 and again in 2024.

### 4.3 Signal quality

| diagnostic | Nuevo Leon value |
|---|---|
| GSFC noise 2-sigma, area-weighted | 16.5 mm |
| GSFC leakage 2-sigma, area-weighted | 13.7 mm |
| **GSFC leakage-trend uncertainty, area-weighted** | **3.75 mm/yr** |
| GSFC vs CSR median per-mascon series correlation | 0.82 |
| GSFC vs CSR per-mascon trend correlation | 0.43 |
| GSFC - CSR mean trend difference | CSR is 1.15 mm/yr *less* negative |
| mascons where the two disagree in sign | 7 of 40 |
| land mascons / effective degrees of freedom (prior work) | 40 / 1.53 |

The leakage-trend line governs everything above. **3.75 mm/yr is larger than the state's
total-storage trend.** In the Arabian Peninsula run the equivalent figure was 2.49 mm/yr
against a -5.46 mm/yr signal, a ratio of 0.46; here the ratio is 2.3. That single
comparison explains why the Arabian result was publishable and this one is not: the signal
is four times smaller and the systematic uncertainty is half again as large.

### 4.4 GLDAS: the completed budget

On the 240 reservoir-covered months, state-weighted, three-model ensemble:

| term | trend (mm/yr) | p | share of the TWS trend |
|---|---|---|---|
| total water storage | **-1.63** | 0.11 | - |
| reservoirs | -1.09 | 0.06 | 67% |
| soil moisture + snow + canopy | -1.33 | 0.10 | 82% |
| **groundwater** | **+0.79** | 0.07 | -49% |

Per model, the groundwater term is **+1.75 NOAH, +0.88 VIC, -0.26 CLSM** mm/yr. The models
do not agree on its sign, and the full ensemble spread (2.01 mm/yr) is itself half the
leakage floor. Read the +0.79 as "no detectable trend", not as recharge.

**The excursion.** Restricting the trough search to the drought window rather than the
whole record - the series also dips in 2003 - gives a pre-2020 mean of -0.8 mm, a trough
of **-53.8 mm at 2024-09**, and a post-trough mean of -22.4 mm over the seven months
before the reservoir record ends: **59% of the drop recovered**. The SMAP work put the
same figure at 63% on a different window with a different soil product. Both say the same
thing about shape.

**Fitting a line to that shape is what produced the earlier -4.40 mm/yr residual.** On the
SMAP window alone, GLDAS gives a groundwater trend of -3.70 mm/yr (p = 0.040), the same
order. The number is not wrong; it is a description of the down-leg of an excursion that
had not yet turned when that window closed. Over the full record it is +0.79.

**SMAP against GLDAS, the first independent check on the soil term.** On their 95 shared
months, SMAP L4 root-zone gives -0.75 mm/yr (p = 0.60) and GLDAS -2.37 mm/yr (p = 0.25),
with a series correlation of **r = 0.80**. Two products built on different physics and
different observations track each other closely and agree that the soil trend is not
significant. Neither is an observation of soil moisture - both are model assimilations -
so this rules out a one-model artefact rather than establishing the truth of the term.

---

## 5. Answers to the questions asked

**Can reservoirs be separated from groundwater?** *Reservoirs can be separated from total
storage* - cleanly, with measured daily data, over 2002-04 to 2025-04. They account for 67%
of the GSFC trend and 42% of the CSR trend over Nuevo Leon. **Groundwater can now also be
separated** - GLDAS soil moisture, snow and canopy account for a further 82% of the trend
(section 4.4) - **but what is left cannot be resolved**: +0.79 mm/yr, p = 0.07, the three
models disagreeing on its sign, against a leakage-trend uncertainty of 3.75 mm/yr. The
reviewer's reservation was correct, and stronger than anticipated: the mixing problem is
not marginal, the reservoir term is seven times the noise floor, and after removing it and
soil moisture there is no signal left to attribute.

**What does the post-2020 gradient show?** A real far-from-centre drying of -65 mm (GSFC) /
-36 mm (CSR), but organised by neither distance (r2 <= 0.18 in both) nor any variable the
two solutions agree on. GSFC organises it by the US/Mexico split (eta2 = 0.47) that
coincides with its own `basin` region boundary; CSR shows that split at eta2 = 0.04 and
organises the field east-west instead. **The Mexican limb of the gradient replicates; the
Texan limb, which is the large one, does not.** It should not be published as hydrology
without a third solution.

**What remains unverified?** Section 7.

---

## 6. Caveats

**C1 - The groundwater term is GRACE minus three models, not an observation.** As of
2026-08-10 a land-surface model *is* subtracted (section 3.6), so the residual is a
groundwater estimate rather than a total-storage leftover. What it is not is a
measurement of groundwater: NOAH, VIC and CLSM disagree on its sign, and any error in
their soil moisture transfers one-for-one into it. Unmonitored small surface storage and
channel storage are still inside it (C6). Elsewhere in this report the phrase
"residual (TWS - reservoirs)" refers to the pre-GLDAS quantity and still contains soil
moisture; section 4.4 is the version that does not.

**C2 - No gain or scale factor exists for GSFC, so all amplitudes are biased low.** GSFC
ships leakage as an uncertainty (`leakage_2sigma`, `leakage_trend`), not a correction.
Every magnitude here is a floor. `leakage_trend` is a symmetric uncertainty, not a signed
bias, and was **not** subtracted.

**C3 - The leakage-trend uncertainty exceeds the signal** (section 4.3). A defensible
statement of the Nuevo Leon headline is **-1.6 +/- 3.8 mm/yr**, systematic-dominated.
Small p-values in this report describe the fit's internal consistency, not the accuracy of
the underlying solution.

**C4 - The GSFC basin-block finding is a coincidence of geometry, quantified but not
diagnosed.** I established that GSFC's `basin` code partitions this window along the Rio
Grande, that per-mascon trend variance is strongly organised by it (eta2 = 0.61), and that
CSR is not. I did **not** establish causation: GSFC's regularization scheme is described in
Loomis et al. (2019) but I did not read the RL06v2 constraint construction or test it
synthetically. The border is also a genuine hydrological and administrative boundary - the
Texas side of the Lower Rio Grande Valley is heavily irrigated and drew down through the
same drought. **Both explanations are live. The finding is that the two solutions disagree
by a factor of 4, not that GSFC is wrong.**

**C5 - The reservoir record stops 11 months before GRACE does** (2025-04-15). Everything
paired is computed on the overlap; the unpaired GSFC trend (-1.65 mm/yr, p = 0.086) is
given alongside the paired one (-1.63 mm/yr, p = 0.11) so the effect of the truncation is
visible.

**C6 - Only monitored dams are removed.** SINA covers ~200 dams nationally, 32 in this
window. Small dams, stock ponds and channel storage are not in the correction and remain in
the residual. Their aggregate is unquantified; in a ranching region it is not obviously
zero.

**C7 - The SINA/TWDB splice for the international reservoirs rests on a two-date agreement
check** (section 3.2) plus a year-by-year ratio series. It is well evidenced but it is a
splice, and the two lakes dominate mascons 3140 and 3150. Mascon 3150 is 43% inside Nuevo
Leon and contributes to the state aggregate.

**C8 - CHIRPS is a weaker instrument here than the fraction-unexplained numbers imply.**
Values above 1 (five Nuevo Leon mascons) mean storage fell through a wet period, which is
normally strong evidence; but with trends of +/-2 mm/yr and p-values of 0.3-0.8 the ratio
is mostly dividing noise by noise. The qualitative statement in fig4 panel C - a cumulative
rainfall deficit developing steadily from 2021 and never recovering - is the more robust
reading.

**C9 - The drought window is imported, not computed.** 2022-07 .. 2023-04 comes from the
SMAP/SPI-12 study on `H:`. If that window is wrong, the drawdown numbers in section 4.2
move. Independently, both GRACE solutions place their minimum *after* it, which is
consistent but is not a validation of the window itself.

**C10 - The 40 mascons are not 40 measurements.** Prior work in
`processed/decorrelation_summary.json`: adjacent-mascon r = 0.93, first EOF 79% of
variance, **effective degrees of freedom 1.53**. Per-mascon p-values in section 4.1 are not
corrected for multiplicity and should be read as descriptive.

**C11 - No in-situ validation.** No piezometric data, no SADM abstraction volumes, no
aquifer polygons. Aquifer names are deliberately absent from this report.

**C12 - Two bugs were found and fixed during this run, and both are worth recording.**
(i) A weighted mean of solution midpoints was silently mis-scaled by
`np.average(...).astype("datetime64[ns]")` on a `datetime64[us]` index, putting every epoch
in January 1970 and making dS/dt meaningless (storage values were unaffected). (ii) A
`nansum(x*w)/w.sum()` regional mean scored GRACE's 33 missing months as exactly 0 mm and
fed them into every trend fit; correcting it moved the Nuevo Leon TWS p-value from 0.028 to
0.086 - i.e. **the state trend was only "significant" because of the bug.** Both are fixed
in `scripts/` and every number above post-dates the fix.

(iii) The same class of bug appeared a third time, in the GLDAS work, and was caught
before it reached this report. Script 15 initially normalised the weighted mean by the
full weight sum regardless of how many mascons reported, so the eleven months after
CONAGUA's 2025-04 cut-off - where one dam of seven still reports - were scored as though
the missing reservoirs were at zero anomaly. Those are precisely the months the recovery
percentage depends on. The fix normalises against the weight that actually reported and
drops months below 90% coverage. **A missing value silently read as zero has now caused
three separate errors in this project**, which is worth stating as a pattern rather than
as three incidents.

---

## 7. What could not be completed

**U1 - No soil-moisture removal, so no TWS -> GWS conversion.** ~~No Earthdata
credentials, so no GLDAS.~~ **Closed 2026-08-10.** Credentials arrived, GLDAS 2.1 NOAH,
VIC and CLSM were subtracted over the full record, and `depletion/attribution.py`'s
storage definitions were used directly. Sections 3.6 and 4.4. SMAP was done first
(scripts 13-14) on its shorter window and the two products agree at r = 0.80.

What this did **not** settle is the CSR question. The GLDAS work runs on GSFC only, so
whether CSR's -1.50 mm/yr residual is soil moisture remains open - though the GSFC answer
(soil moisture accounts for 82% of a -1.63 mm/yr trend) makes it the obvious first
hypothesis.

**U2 - No JPL solution.** Two solutions disagree by a factor of 4 over the Texas mascons
and there is no third to break the tie. JPL RL06.3M mascons would do it, and the Earthdata
credentials that closed U1 also unblock them - this is now the highest-value remaining
step, not a blocked one.

**U3 - The GSFC basin-block hypothesis was not tested against the product documentation or
synthetically** (C4).

**U4 - No groundwater level data was sought or obtained.** CONAGUA's aquifer availability
determinations (DOF) and the REPDA extraction registry exist; neither was pursued.

**U5 - No aquifer polygons**, so no result is attached to a named aquifer.

**U6 - Municipal abstraction volumes for Monterrey (SADM) were not obtained**, so the
residual cannot be checked against a known pumping rate.

**U7 - Pre-2018 SINA definitional flips for Amistad and Falcon were characterised but not
explained.** The ratio series in `inventory/international_reservoir_source_check.json`
shows the field switching definition at least four times; TWDB sidesteps it rather than
resolving it.

**U8 - No changepoint or piecewise analysis**, and none should be inferred from the
GRACE/GRACE-FO era split.

---

## 8. Reproducing

```powershell
cd C:\Users\grupp\dark-water-extract\dark-water-main
$env:PYTHONPATH = "src"
$py = ".\.venv\Scripts\python.exe"

& $py E:\Water\NuevoLeon\scripts\01b_download_conagua_par.py   # CONAGUA SINA, resumable
& $py E:\Water\NuevoLeon\scripts\04_download_twdb.py           # Amistad + Falcon whole-lake
& $py E:\Water\NuevoLeon\scripts\02_build_signals.py           # GRACE per-mascon product
& $py E:\Water\NuevoLeon\scripts\05_reservoir_series.py        # Phase 1 number + reservoir mm
& $py E:\Water\NuevoLeon\scripts\06_decompose.py               # Phase 3 decomposition
& $py E:\Water\NuevoLeon\scripts\07_gradient_and_csr.py        # Phase 4 + CSR cross-check
& $py E:\Water\NuevoLeon\scripts\08_basin_block_check.py       # the basin-seam diagnostic
& $py E:\Water\NuevoLeon\scripts\09_headline.py                # Nuevo Leon headline numbers
& $py E:\Water\NuevoLeon\scripts\11_dsdt.py                    # gap-aware dS/dt
& $py E:\Water\NuevoLeon\scripts\10_figures.py                 # figures
& $py E:\Water\NuevoLeon\scripts\12_write_report.py            # this file

# added 2026-08-10, needs an Earthdata token (see below)
& $py E:\Water\_shared\gldas_download.py E:\Water\NuevoLeon `
      --lat 20.5 30.5 --lon -104.5 -95.5                       # GLDAS subsets, resumable
& $py E:\Water\NuevoLeon\scripts\15_gldas_decomposition.py     # the completed budget
& $py E:\Water\NuevoLeon\scripts\16_gldas_figure.py            # fig6
```

The downloader reads an Earthdata Login bearer token from the file named by
`EARTHDATA_TOKEN_FILE`. Tokens expire after 60 days and the GESDISC DATA ARCHIVE
application must be authorised on the Earthdata profile, or every request returns 401
with otherwise valid credentials. The token is never passed on a command line and never
written to any output in this folder.

`03_reservoir_inventory.py` is the first-pass Phase-1 calculation, superseded by `05`
(which adds the TWDB splice and the reporting mask) but kept because it is what produced
the decision number before the international-reservoir problem was found. CHIRPS was
fetched with two `curl` calls to the IRI Data Library, recorded in `raw/`. Nothing under
`C:\Users\grupp\dark-water-extract` was modified; `trend.fit_trend`,
`precipitation.cumulative_anomaly`, `precipitation.adjusted_trend`,
`attribution.monthly_mean` and `attribution._NON_GW_STORAGE` were imported and used
unmodified.

## Sources

- GSFC mascon RL06v2.0 - https://earth.gsfc.nasa.gov/geo/data/grace-mascons
- GLDAS 2.1 monthly (NOAH025, VIC10, CLSM10) - NASA GES DISC, via OPeNDAP
- Loomis, Luthcke & Sabaka (2019), Regularization and error characterization of GRACE mascons, J. Geod. 93, 1381-1398 - https://doi.org/10.1007/s00190-019-01252-y
- CSR GRACE/GRACE-FO RL06.3 mascons - https://doi.org/10.15781/cgq9-nh24
- CONAGUA, Sistema Nacional de Informacion del Agua, Monitoreo de Presas - https://sinav30.conagua.gob.mx:8080/Presas/
- Texas Water Development Board, Water Data for Texas - https://waterdatafortexas.org/reservoirs/individual/amistad and /falcon
- CHIRPS v2.0 via the IRI Data Library - https://iridl.ldeo.columbia.edu/SOURCES/.UCSB/.CHIRPS/.v2p0/
- Drought window and Nuevo Leon state boundary: prior SMAP/SPI-12 study, `H:\water intelligence\soilmoisture`
