# Central Valley positive control — findings

## Headline: the method works, and the test now has power

Oregon's consumptive-use coefficient was **+3.1 ± 3.6**, an interval containing both 0 and the
−1 that physics predicts if consumed water came out of storage. Uninterpretable.

At Central Valley's best mascon (52.1% irrigated) the same regression returns:

> **b(CU) = −0.035 ± 0.236**, which **excludes −1 at 4.1σ**

SNR is **0.648 against Oregon's 0.150**, a factor of 16.

**Oregon's null is therefore a real finding about Oregon**, not a broken method. At 3.3%
coverage no basin could have produced a usable result.

---

## The deliverable — the detection threshold

> **D = f_irr × CU_irr ≥ 130 mm/yr** for a 2σ constraint over ~20 years of GRACE at native
> mascon resolution.

| CU over irrigated land | Minimum irrigated fraction |
|---|---|
| 1,000 mm/yr (Central Valley orchards) | **13.0%** |
| 700 mm/yr (mixed irrigated agriculture) | **18.5%** |
| 620 mm/yr (Oregon) | **20.9%** |
| 400 mm/yr (short season) | **32.4%** |

Scales as `D ∝ 1/√n_eff`, with `n_eff ≈ 0.66 × n_months`.

### Built from three measured relations

1. **Signal.** `σ(CU′) = γ · CU_annual / 12`, with **γ = 0.305** (Central Valley, 4 footprints,
   sd 0.012) and **γ = 0.292** (Oregon, independent). Two basins, different crops, different
   consumptive-use sources, agreeing to 4%.
2. **Noise.** The dS/dt noise floor belongs to GRACE, not the basin: Central Valley 40-mascon
   **10.61 mm/month** against Oregon's **10.46**. Critically, averaging 40 mascons reduces noise
   by **×0.90, not ×0.16** — the 1.20 effective spatial degrees of freedom made visible.
   *Aggregation buys almost nothing.*
3. **Power.** `se(b_CU) = κ / (SNR · √n_eff)`, with κ = 1.41 measured and stable across
   1.36–1.48 in all four regressions before being used.

### It classifies all six measured footprints correctly

| Footprint | f_irr % | D mm/yr | SNR | Verdict | Observed se(b_CU) |
|---|---|---|---|---|---|
| CV mascon 1850 | 52.1 | 318.5 | 0.648 | PASS | ±0.24 ✓ |
| CV core (8 mascons) | 29.0 | 160.6 | 0.328 | PASS | ±0.37 ✓ |
| CV 300 km | 19.5 | 111.0 | 0.257 | marginal | ±0.53 ✓ |
| CV all 40 | 7.0 | 44.8 | 0.109 | fail | ±1.07 ✓ |
| **Oregon best mascon** | 14.5 | 79.2 | 0.150 | **fail** | — |
| **Oregon 300 km** | 3.3 | 17.7 | 0.041 | **fail** | ±3.55 ✓ |

Oregon at 300 km needed **392 effective years**. Central Valley mascon 1850 needed **1.6**.

---

## Coverage (Phase 2)

40 land mascons. Best is **1850 (36.0°N, 119.38°W, Tulare): 52.08% irrigable, 42.68%
irrigated-and-cropped, 56.35% all farmland**, stable at 50.8–53.0% across seven surveys.

**Eight Central Valley mascons beat Oregon's single best of 14.5%.** Median across the 40 is
1.82%. Total irrigable area 34,694 km².

Both columns are carried separately throughout, because DWR's flag describes *the land*: the
52.08% figure includes idle and fallow ground with irrigation infrastructure, while 42.68% is
the like-for-like match to Oregon's actively-irrigated rule.

---

## Consumptive use — obtained, not derived

The DWR Water Plan water-balance archives total **42 MB**. All 21 water years WY2002–2022
downloaded and verified complete, no zero-byte files.

They carry `AG003 Evapotranspiration of Applied Water`, the direct analogue of Oregon's
`IRR_CU`, at **DAUCO grain** (384 units inside the 40 mascons, roughly 10 per mascon), annual
by water year.

**Independent validation passed.** DWR's ETAW divided by Land IQ's separately measured
irrigated area gives **1,045 mm/yr** at mascon 1850 (range 873–1,269 over 21 years) and
**725 mm/yr** mean across mascons. Two unrelated datasets landing exactly where Central Valley
crop ET must be, with the orchard-heavy mascon at the top. Nothing tuned.

**Monthly disaggregation is derived.** Annual ETAW × weight `max(0, ETo − P)` from Spatial
CIMIS (2 km daily) and PRISM (4 km monthly). The annual total is DWR's and is never altered.
Sensitivity tested: swapping year-specific for fixed climatological weights moves the partial
correlation from +0.014 to −0.116. Both are approximately zero and neither is near −1, so the
disaggregation is not driving the answer.

**Not obtained:** OpenET (403 Not authenticated, no API key — the most valuable gap); SGMA
groundwater levels (host refuses connections); 5 of 21 CIMIS years; 3 of 294 PRISM months.

---

## Was the signal detectable?

**SNR yes, causal attribution no.** The Oregon pattern reproduces exactly:

| Stage | r |
|---|---|
| Raw | +0.78 (shared seasonality) |
| Deseasonalised | +0.345 |
| Induced through precipitation | +0.336 |
| **Partial, controlling for P** | **+0.014 (p = 0.88)** |

Same at every footprint, and at annual scale (b_CU = −0.018 ± 0.206, n = 16 years).

### CSR RL06.3 cross-check

Deseasonalised correlation with GSFC runs **+0.81 to +0.88**. Both solutions agree the signal
exists and agree on sign.

They do **not** agree quantitatively. CSR's noise floor is twice GSFC's, its trend is half
(−5.81 against −11.35 mm/yr), and **CSR's coefficient interval still contains −1**
(−0.508 ± 0.399).

**The 4.1σ exclusion is a GSFC result, not a GRACE result.** The SNR advantage over Oregon is
robust across both centres.

### Trend robustness

Unlike Oregon, the trend holds here: **−11.37 ± 1.88 mm/yr** across all 40 mascons and
**−15.54 ± 2.34** in the core, barely moving when an inter-mission step is fitted. Oregon's
−4.28 collapsed to +0.06 ± 1.09 under the same test.

---

## Why b(CU) ≈ 0 rather than −1, and why that is not a failure

A coefficient of −1 holds only if the consumed water came from storage *inside* the footprint.
Three reasons it did not:

- **Imports.** The CVP and SWP move water up to 400 km into Tulare.
- **Recharge.** DWR's own AG005 deep percolation is 27.6 mm/yr against 224.7 mm/yr ETAW, a 12%
  direct return before any managed recharge.
- **Aquifer buffering.**

The crop database **defines water-source codes 1–5 but populates none of them**, so groundwater
cannot be separated from surface supply. That is the specific gap blocking the causal question.

---

## What remains unverified

- **−1 is the wrong null for an import-fed basin.** A closed basin would be the cleaner
  control, and none was tested.
- **The DWR water balance contains a methodology step**: core ETAW jumps **+28.1 mm/yr**
  between WY ≤ 2011 and WY ≥ 2013, and deep percolation halves. It sits inside the record and
  was **not removed**. Deseasonalisation does not remove a step. This is the largest
  unquantified error in the consumptive-use series.
- Runoff Q not obtained, as in Oregon.
- No gain factor exists for GSFC, so amplitudes are biased low. That biases *against* detection,
  so true SNR is if anything better than reported.
- Consumptive use assigned by DAUCO centroid (point-in-box rather than area overlay). This is
  the likely cause of the inflated per-mascon γ = 0.46 against the footprint value of 0.305;
  the conservative footprint value was used.
- Irrigated fraction is a 2016–2023 mean applied back to 2002. 2014 has no irrigation-status
  field at all.
- **Not attempted:** GLDAS/LSM removal (Sierra snowpack sits inside several mascons,
  unseparated); lagged regressions; a second import-free control basin.

---

## Three database traps resolved

Full detail in `inventory/DATABASE_NOTES.md`.

1. **The crop lives in `CLASS2`, not `CLASS1`.** `SYMB_CLASS == CLASS2` in 100.0000% of rows,
   all seven years, verified.
2. **`IRR_TYP2PA` is irrigation *status*; `IRR_TYP2PB` is *method*.** Reading block 1 would have
   returned roughly 0% non-irrigated across 440,000 polygons.
3. **2014 is a calendar year with a different schema**; 2016 onward are water years. The
   idle/fallow code changes meaning between vintages (`I` → `X` → both), pooled here to avoid a
   spurious 2021 step.

No interpolation between survey years. Irrigated extent moves 4% relative over eight years, so
interpolating 8 points onto 255 months would have manufactured structure.

---

## Outputs

- `inventory/` — **DATABASE_NOTES.md**, **CONSUMPTIVE_USE_SOURCES.md**,
  `detection_threshold.json` (the deliverable, machine-readable), `grace_signal_quality.json`,
  `flux_comparison.json`, plus schema, domain and coverage JSONs
- `processed/` — 27 files including `fields_all_years.parquet` (3.31M field-years),
  `mascon_coverage.csv`, `waterbalance_dauco.parquet`, `cu_monthly_mascon.parquet`,
  `flux_results_*.csv`, `threshold_*.csv`
- `trends/` — `fig1_coverage.png`, `fig2_threshold.png` (the deliverable figure),
  `fig3_series.png`, `fig4_coefficient.png`
- `signals/flux_series.parquet`, `scripts/` (31 scripts), `raw/` (4.2 GB)

Source data untouched. `tifffile` and `imagecodecs` were installed to `tmp/pylibs` rather than
the protected venv, because no raster reader was available and both PRISM and CIMIS ship
GeoTIFFs.
