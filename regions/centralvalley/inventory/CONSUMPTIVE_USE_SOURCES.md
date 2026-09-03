# Phase 3 — where consumptive use came from, and what it actually contains

## Correction to an earlier concern: the DWR water balance is ~42 MB, not ~30 GB

The California Water Plan water-balance archives were flagged as a possible
30 GB download of unverified payload. **They are not.** Measured on disk:

| | |
|---|---|
| files | 21, one per water year WY2002…WY2022 |
| **total size** | **42 MB** (945 KB–3.4 MB each) |
| zero-byte / partial files | **none** — all 21 verified complete and openable |
| WY2012, WY2021 | present (they failed once, were refetched, and are complete) |

The whole series was already on disk and had already been opened and validated
before the concern was raised. Nothing further needed to be fetched from this
source, and nothing was.

## What is inside one archive

`wb_2020.zip` (3.4 MB) contains five members:

```
CDWR-wbqc-wb100-dp1000-2020-DAUCO.csv   21.9 MB uncompressed   <- the one used
CDWR-wbqc-wb100-dp1000-2020-HR.csv       0.27 MB
CDWR-wbqc-wb100-dp1000-2020-PA.csv       1.29 MB
CDWR-wbqc-wb100-dp1000-2020-ST.csv       0.02 MB
Master-OWIA-WaterBalance-2020-DataTables-Verification.pdf
```

The four CSVs are the same water balance aggregated to four nested spatial
units: **DAUCO** (Detailed Analysis Unit by County), **PA** (Planning Area),
**HR** (Hydrologic Region), **ST** (State). DAUCO is the finest.

### Schema

14 columns: `WY, CategoryA, CategoryD, CategoryB, CategoryC, DAUCO, DAU.Name,
HR.Name, HR.Code, PA, Longitude, Latitude, TAF, Source`.

- **Spatial grain: DAUCO.** 486 statewide, **384 of them inside the 40 Central
  Valley mascons** — roughly 10 DAUCOs per mascon, so the mascon footprint is
  resolved about ten times over. Each row carries a representative
  `Longitude`/`Latitude`, so mascon assignment needs no separate boundary layer.
- **Temporal grain: annual, by water year** (Oct–Sep). **Not monthly.** This is
  the source's one real limitation and it is handled explicitly below.
- **Units: TAF** (thousand acre-feet).

### The agricultural categories

| `CategoryD` | `CategoryC` | statewide WY2020 |
|---|---|---|
| AG001 | Applied Water – Crop Production | 29,240 TAF |
| AG002 | Applied Water – Groundwater Recharge | 502 TAF |
| **AG003** | **Evapotranspiration of Applied Water** | **23,506 TAF** |
| AG005 | Deep Percolation of Applied Water | 1,512 TAF |
| AG006 | Deep Percolation of Applied Water to Salt Sink | 614 TAF |
| AG008 | Reuse of Return Flows within DAUCO | 719 TAF |

**AG003, evapotranspiration of applied water (ETAW), is agricultural
consumptive use.** It is the direct analogue of Oregon's `IRR_CU`
(= ETa − effective precipitation): the part of applied irrigation water that
leaves as vapour and does not return to storage. It is **DWR's own published
estimate, taken not derived.**

### Verdict

The source **does** give consumptive use, at a spatial grain ten times finer
than a mascon, for 21 consecutive water years covering GRACE's record. It does
**not** give months. It cost 42 MB. It was kept.

### Physical sanity check (passed)

ETAW divided by the independently measured irrigated-crop area from the DWR
i15 crop maps gives the consumptive-use **depth over irrigated land**:

| mascon | ETAW over irrigated crops, mm/yr (mean, min–max over 21 years) |
|---|---|
| 1850 (36.0 N, 119.38 W — Tulare) | **1,045** (873–1,269) |
| 1834 (40.0 N, 122.40 W) | 986 (702–1,190) |
| 1849 | 991 (687–1,181) |
| 1845 | 925 (631–1,128) |
| 1840 | 880 (710–1,023) |
| 1844 | 787 (657–877) |
| 1837 | 786 (678–893) |
| 1855 | 780 (614–946) |
| **mean over the 20 mascons with crops** | **718** |

These are two entirely independent datasets — DWR's water accounting and Land
IQ's remote-sensed field polygons — and their ratio lands squarely in the
500–1,100 mm/yr range that Central Valley crop ET must occupy. Almond and
pistachio country (mascon 1850) sits at the top of the range, as it should.
Nothing was tuned to make this happen.

---

## Monthly disaggregation — what is derived, and the uncertainty it adds

DWR gives a water-year total; GRACE needs months. The annual total is spread
across the twelve months of its water year by

    D_m  = max(0, ETo_m − P_m)         atmospheric demand not met by rain
    w_m  = D_m / Σ_{water year} D
    CU_m = ETAW_WY × w_m

**The annual total is DWR's and is never altered.** Only the within-year
distribution is derived, and it is derived from two *measured* fields rather
than from crop coefficients:

- **ETo** — Spatial CIMIS daily reference evapotranspiration, 2 km,
  EPSG:3310, mm/day, summed to months over each mascon footprint.
  CNRA dataset `cimis-spatial-eto-maps`.
- **P** — PRISM AN81m monthly precipitation, 4 km, EPSG:4269, mm/month,
  averaged (cos-latitude weighted) over the same footprint.

### Uncertainty this introduces

1. **The seasonal shape is a proxy, not a measurement.** `max(0, ETo − P)` is
   not the true irrigation schedule: it ignores soil-moisture carryover,
   pre-irrigation, crop-specific phenology and orchard dormancy.
2. **The error is largely removed by deseasonalisation.** The analysis
   deseasonalises before claiming any correlation. A *fixed* seasonal shape
   contributes only to the climatological mean, which is subtracted. What
   survives is (a) the interannual variation in ETAW, which is DWR's, and
   (b) the year-to-year modulation of the weights, which is measured ETo and P.
3. **Both variants are computed and compared.** `cu_mm` uses year-specific
   weights; `cu_clim_mm` uses one fixed climatological set of twelve weights.
   If the two give the same signal amplitude and the same SNR, the
   disaggregation is not driving the answer. This comparison is reported, not
   assumed.

### Coverage of the inputs actually obtained

| input | obtained | missing |
|---|---|---|
| DWR water balance | **21/21 water years** WY2002–2022 | none |
| PRISM monthly ppt | **291/294 months** 2002-01…2026-06 | 2007-04, 2023-09, 2023-12 — the service returns a 186-byte error page for these three, twice each; abandoned as unobtainable, not retried further |
| Spatial CIMIS ETo | **16/21 years**: 2004–2006, 2008, 2012–2016, 2018–2024 | 2007, 2009, 2010, 2011, 2017 |

Missing CIMIS years fall back to that mascon's **climatological monthly ETo**
computed from the 16 years present. ETo interannual variability in California
is small (a few per cent) next to precipitation variability, and ETo enters
only the weight, so this is a minor approximation — but it is an approximation
and the affected months are flagged in `inventory/reduction_coverage.json`.

---

## Sources considered and rejected

- **OpenET** (`https://openet-api.org`) — would have given actual, measured
  monthly field-scale ET, the ideal product. The API is reachable
  (`GET /openapi.json` returns 200) but every data endpoint requires an API
  key: `POST /raster/timeseries/point` returns
  `403 {"detail":"Not authenticated"}`. **No key exists on this machine, so
  OpenET could not be used.** This is the single most valuable thing that was
  not obtained.
- **CIMIS station Web API** (`et.water.ca.gov/api/data`) — also requires an
  `appKey`; the connection is refused without one. The *Spatial* CIMIS product
  was used instead, which needs no key.
- **SGMA groundwater level data** (`sgma.water.ca.gov`) — the host refuses
  connections from this machine (`ConnectionResetError 10054`) with and without
  a browser user agent. The independent groundwater-level ground truth was
  therefore **not obtained**. This is a real gap: it would have let GRACE be
  checked against in-situ heads.
- **Crop-coefficient (Kc × ETo) derivation** — not used as the primary series.
  It would have required Kc values for ~60 DWR crop subclasses from a source
  not on this machine, and would have produced an estimate *less* authoritative
  than DWR's own published ETAW while adding a second layer of derivation.
  DWR's AG003 already embeds California-specific crop coefficients applied by
  the agency that defines them.
