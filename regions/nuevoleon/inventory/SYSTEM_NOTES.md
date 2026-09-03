# Nuevo León water-balance system notes

Written before any statistics were run on the GRACE series, to establish what the
components are and how big each is in the units GRACE actually measures.
Analysis date 2026-07-27. All figures below are computed from files on disk unless
explicitly flagged as background knowledge.

---

## 1. The mascon grid this region is measured on

GSFC RL06v2.0 solves for 1-arc-degree equal-area mascons. In the processing window
(22–29 °N, 102.7–97.0 °W) there are **40 land mascons** (`location == 80`; the 14
`location == 90` ocean mascons in the same box, all in the Gulf of Mexico, are
excluded). Median mascon area **12,400.84 km²**, total **495,893 km²**.

The single most important conversion in this whole study:

```
1 hm³ (= 1e6 m³) spread over 12,400.84 km²  =  0.0806 mm equivalent water height
1,000 hm³                                    =  80.6 mm
```

**14 of the 40 mascons intersect the Nuevo León state polygon** (from
`H:\water intelligence\soilmoisture\data\nuevo_leon.geojson`); 9 have more than 20%
of their box inside the state. Weighting each mascon by area × in-state fraction
gives an effective **65,178 km²** of Nuevo León representation — the state's true
area is about 64,200 km², so the weighting is close to right.

Mascons relevant to the human system:

| mascon | centre | box | in NL | what is in it |
|---|---|---|---|---|
| **3151** | 26.0 N, 100.87 W | 25.5–26.5 N, 101.42–100.31 W | 55% | Sierra Madre Oriental; **western Monterrey** |
| **3152** | 26.0 N, 99.75 W | 25.5–26.5 N, 100.31–99.20 W | 97% | **eastern Monterrey conurbation, El Cuchillo, Las Blancas** |
| **3154** | 25.0 N, 99.94 W | 24.5–25.5 N, 100.49–99.39 W | 91% | **Cerro Prieto, La Boca**, Linares, Montemorelos |
| 3150 | 27.0 N, 99.56 W | 26.5–27.5 N, 100.13–99.00 W | 43% | Anáhuac, **Falcón reservoir**, Nuevo Laredo |
| 3153 | 26.0 N, 98.64 W | 25.5–26.5 N, 99.20–98.08 W | 32% | **El Azúcar / Marte R. Gómez**, DR-026 irrigation |
| 3149 | 27.0 N, 100.69 W | 26.5–27.5 N, 101.25–100.13 W | 48% | northern NL, Salinillas |
| 3235 | 24.0 N, 100.12 W | 23.5–24.5 N, 100.67–99.57 W | 82% | southern NL altiplano |

**Monterrey itself straddles a mascon boundary.** The city-centre coordinate
(25.6866 N, 100.3161 W — background knowledge, a standard gazetteer value) falls
0.007° west of the 3151/3152 edge at 100.3096 W, so the city core is in 3151 while
the eastern municipalities of the conurbation (San Nicolás, Guadalupe, Apodaca) are
in 3152. No single mascon "is" the metropolitan area.

---

## 2. The reservoir term — the number that decides the study

### The Monterrey supply system

CONAGUA SINA daily monitoring (`raw/conagua_presas/`, 292 monthly day-15 snapshots
requested, 277 populated, spanning 2002-04-15 .. 2025-04-15) gives, for the three named
reservoirs:

| reservoir | municipality | lat, lon | mascon | NAMO capacity | as mm over its own mascon |
|---|---|---|---|---|---|
| El Cuchillo (Cuchillo Solidaridad) | China, N.L. | 25.712 N, 99.277 W | 3152 | 1,123.14 hm³ | **90.6 mm** |
| Cerro Prieto (José López Portillo) | Linares, N.L. | 24.938 N, 99.400 W | 3154 | 300.00 hm³ | **24.2 mm** |
| La Boca (Rodrigo Gómez) | Santiago, N.L. | 25.428 N, 100.128 W | 3154 | 35.00 hm³ | **2.8 mm** |
| **combined** | | | | **1,458.15 hm³** | **117.6 mm if held in one mascon** |

Observed 2002–2026 range of the combined system: **1,848 hm³**, i.e. **149.0 mm**
over one mascon footprint. Maximum 2,147 hm³ (Jan 2004), minimum 299 hm³ (Aug 2013);
the 2022 crisis low was 453 hm³ in Aug 2022.

### Against the GRACE noise floor

Median GSFC `uncertainty/noise_2sigma` over these mascons is **16.73 mm**.

```
Monterrey system capacity        117.6 mm  =  7.03 x the 2 sigma noise floor
Monterrey system observed range  149.0 mm  =  8.91 x the 2 sigma noise floor
```

**Conclusion, and it is unambiguous: reservoirs do NOT sit below the noise. They are
roughly seven times it.** They must be removed before any statement about
groundwater. This is the answer to the question the brief said should be answered
first.

### The wider window is worse, not better

32 monitored dams fall inside the 40-mascon window, together **16,728 hm³** of NAMO
capacity — only **33.7 mm** spread over the whole 495,893 km² region, which sounds
harmless. It is not, because reservoirs are point features and GRACE resolves at
mascon scale:

| mascon | reservoirs | capacity as mm over that mascon | reservoir-anomaly range | reservoir s.d. | mascon TWS s.d. | ratio of s.d. |
|---|---|---|---|---|---|---|
| 3140 | La Amistad + 2 | **324.5 mm** | 311.8 mm | 80.8 mm | 55.9 mm | 1.45 |
| 3242 | Vicente Guerrero / Las Adjuntas + 1 | **318.6 mm** | 309.7 mm | 89.0 mm | 47.4 mm | 1.88 |
| 3150 | Falcón | **265.1 mm** | 265.1 mm | 61.2 mm | 60.2 mm | 1.02 |
| 3152 | El Cuchillo + Las Blancas | 97.4 mm | 129.0 mm | 26.6 mm | 41.4 mm | 0.64 |
| 3249 | Tampico + Chicayán | 72.2 mm | 101.2 mm | 19.1 mm | 58.1 mm | 0.33 |
| 3145 | Don Martín | 70.5 mm | 107.4 mm | 27.6 mm | 68.2 mm | 0.40 |
| 3153 | El Azúcar | 63.1 mm | 87.3 mm | 18.5 mm | 45.3 mm | 0.41 |
| 3154 | Cerro Prieto + La Boca | 27.0 mm | 32.2 mm | 9.0 mm | 40.8 mm | 0.22 |

In four mascons the reservoir anomaly's standard deviation exceeds half the total
GRACE variability; in three it exceeds the whole mascon's TWS standard deviation.
**Vicente Guerrero, La Amistad and Falcón are each individually larger, in mm of
mascon-mean equivalent water height, than the entire post-2020 drying signal the
brief asked about.**

---

## 3. Data sources obtained, and one that broke

### CONAGUA SINA — obtained, complete, and further back than documented

The public SINA "Monitoreo de Presas" app is a React front end; reading its bundle
(`tmp/presas_main.js`) exposes the API it calls:

```
https://sinav30.conagua.gob.mx:8080/PresasPG/presas/reporte/YYYY-MM-DD
```

which returns a JSON array, one object per monitored dam, with `namoalmac`
(conservation capacity, hm³), `almacenaactual` (current storage, hm³), `llenano`
(fill fraction), `latitud`, `longitud`, `estado`, `nommunicipio`. **Secondary
descriptions of the module say its history begins in 2007; the endpoint does not
agree — 2002-04-15 returns 193 dams with real storage values**, so the whole GRACE
era is covered. 292 monthly (day-15) snapshots were requested, 277 came back
populated (~200 dams each), and **every date from 2025-04-28 onward returns an
empty array** — checked at 2025-04-28, 2025-05-02, 2025-06-10, 2025-09-15,
2026-01-20 and 2026-07-20. The reservoir correction therefore ends 2025-04-15,
eleven months before GRACE does.

Two data-handling points, both verified rather than assumed:

* **`clavesih` is not a stable key.** 185 of 212 codes appear at more than one
  coordinate over the record, and `nombrecomun` spellings change ("El Cuchillo"
  → "El Cuchillo, N.L."). Dams are therefore keyed by rounded (lat, lon).
* **Large month-to-month jumps in the non-international dams are physical, not
  artefacts.** The largest are 2024-07 (Hurricane Alberto), 2010-07, 2013-10 and
  2022-09 — all rainfall events, all affecting several dams at once.

### The international Rio Grande reservoirs — SINA is unusable, TWDB substituted

`almacenaactual` for **La Amistad and Falcón flips repeatedly between the whole-lake
volume and Mexico's treaty share.** Compared against TWDB's whole-lake
`reservoir_storage`, the SINA/TWDB ratio by year is:

```
Amistad:  2002-2006 ~0.11-0.22 | 2007 1.00 | 2008 0.18 | 2009-2017 ~1.00 | 2018-2025 0.06-0.42
Falcon :  2002-2006 ~0.40-0.58 | 2007 1.00 | 2008 0.16 | 2009-2017 ~1.00 | 2018-2025 0.15-0.54
```

The clearest break is between the 2018-03-15 and 2018-05-15 snapshots: Amistad drops
2,484.7 → 494.5 hm³ and Falcón 1,709.4 → 231.8 hm³, with `namoalmac` switching
4,040.3 → 1,769.7 and 3,264.8 → 1,351.6 in the same step. Those are the Mexican
allotments. GRACE weighs the physical water, so this series cannot be differenced
against GRACE.

**Substituted:** Water Data for Texas daily `reservoir_storage` ("actual storage at
measured lake elevation"), `raw/twdb_amistad.csv` and `raw/twdb_falcon.csv`,
1968–2026. Identified as the whole-lake figure by matching SINA in the periods when
SINA is also whole-lake: on 2018-03-15 TWDB gives 2,013,173 ac-ft = 2,483.2 hm³ at
Amistad against SINA's 2,484.7, and 1,384,408 ac-ft = 1,707.6 hm³ at Falcón against
SINA's 1,709.4 — 0.06% and 0.10%. TWDB's `conservation_storage` column is the *Texas*
share and does not match; it was not used.

### CHIRPS — obtained

`raw/chirps_v2p0_monthly_nuevoleon_0p5deg.nc`, IRI Data Library server-side subset
and 0.5° box-average of CHIRPS v2.0 monthly, 1981–2026, no authentication. Mascon
mean annual rainfall over the window runs **343 mm/yr** (mascon 3151, the Sierra
Madre rain shadow side) to **717 mm/yr** (mascon 3240, the Gulf slope). A single
month at native 0.05° (`raw/chirps_landmask_native.nc`) was pulled separately to
build a land mask for the Gulf-adjacent mascons.

### Not obtained

* **No groundwater level data.** CONAGUA publishes aquifer availability
  determinations (DOF *disponibilidad*) and REPDA extraction registries, but no
  piezometric time series was located or downloaded. Nothing here is ground-truthed
  against a well.
* **No aquifer polygons.** The Cañón del Huajuco / Citrícola Norte / Área
  Metropolitana de Monterrey aquifer boundaries were not obtained, so no result is
  attributed to a named aquifer.
* **No GLDAS/JPL** — no Earthdata credentials on this machine, per the brief. Soil
  moisture is therefore *not* removed anywhere in this study.
* **Municipal abstraction volumes** for Monterrey (SADM) were not obtained.

---

## 4. What the balance therefore looks like

For a Nuevo León mascon, GRACE's total water storage is

```
TWS  =  surface reservoirs  +  soil moisture  +  groundwater  +  small unmonitored storage
```

with snow absent. Of these:

* **surface reservoirs** — measured, to ~1 hm³, from 2002-04; **removable**
* **soil moisture** — not measured here; SMAP root-zone exists for 2016–2025 in
  `H:\water intelligence\soilmoisture` but is not in GRACE-compatible mass units and
  was not converted; **not removable in this study**
* **groundwater** — not measured at all
* **small unmonitored storage** — stock ponds, minor dams below SINA's 200-dam
  monitoring set, channel storage; unquantified

So the most that can be produced here is **TWS minus reservoirs**, which is a
residual containing soil moisture, groundwater and unmonitored surface water. It is
labelled that way throughout and is never called groundwater.
