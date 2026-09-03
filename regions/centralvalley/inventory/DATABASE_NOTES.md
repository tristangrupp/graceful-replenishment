# Phase 1 — the California DWR i15 statewide crop-mapping database

Everything below was measured from the files on disk or read from the DWR
metadata shipped inside the zips. Nothing is assumed. Where the released
documentation and the data disagree, the data is reported.

Sources read:
- `raw/crop_mapping/dwr_land_use_legend.pdf` — *Modified Standard Land Use
  Legend*, Land and Water Use Section, DWR, December 2022. Text extracted with
  a stdlib-only PDF reader (`scripts/pdftext.py`) because `pypdf` is absent and
  the shared venv must not be modified; the `Read` tool needs poppler, which is
  not installed.
- the `.shp.xml` sidecar of every survey year — these are **ArcGIS-profile FGDC
  metadata** and carry per-attribute definitions and value domains. This is the
  authoritative documentation, and it resolved the two ambiguities that matter.

---

## 1. What the layers are

Eight discrete survey years, one polygon layer each, no annual series:

| year | polygons | acres mapped | CRS | period of content |
|---|---|---|---|---|
| 2014 | 361,023 | 14,202,468 | EPSG:3857 | **calendar year** 2014-01-01…2014-12-31 |
| 2016 | 390,666 | 14,855,670 | EPSG:3857 | water year 2015-10-01…2016-09-30 |
| 2018 | 408,290 | 14,317,427 | EPSG:3857 | water year |
| 2019 | 411,122 | 14,406,836 | EPSG:4269 | water year |
| 2020 | 423,142 | 14,565,589 | EPSG:4269 | water year |
| 2021 | 431,145 | 14,587,861 | EPSG:4269 | water year 2020-10-01…2021-09-30 |
| 2022 | 438,580 | 14,618,199 | EPSG:4269 | water year |
| 2023 | 446,914 | 14,597,272 | EPSG:4269 | water year 2022-10-01…2023-09-30 |

Geometry type is `Polygon Z` in every year. **2015 and 2017 do not exist** —
the survey ran biennially before 2018 and annually after.

**Trap 1 — the CRS changes.** 2014/2016/2018 are Web Mercator (EPSG:3857),
2019-2023 are NAD83 geographic (EPSG:4269). Web Mercator is not equal-area;
polygon areas computed from the geometry in 3857 would be wrong by a factor of
`sec²(lat)` ≈ 1.5 at 36 °N. The shipped `ACRES`/`Acres` field is used instead
and is documented as "total land acreage for each individual polygon, given in
U.S. acres" — it is not derived from the stored geometry.

**Trap 2 — 2014 is a calendar year, everything else is a water year.** The
`tempEle`/`TM_Period` metadata elements make this explicit. Mixing 2014 into a
water-year series would shift it by three months.

**Trap 3 — 2014 has a completely different schema.** Nine fields, of which only
`Crop2014` (a free-text crop name, 47 distinct values) and
`DWR_Standa` (12 values of the form `"D | DECIDUOUS FRUITS AND NUTS"`) describe
land use. There is **no irrigation-status field at all in 2014**, no subclass,
no multi-crop structure. 2016 onward use the DWR symbol schema below.

---

## 2. The crop-class coding (2016-2023)

From the *Standard Land Use Legend* section II and the FGDC `CLASS1`
definition. Class symbols, with the leading-space justification DWR uses:

```
 G Grain and hay      R Rice           F Field crops     P Pasture
 T Truck/nursery/berry D Deciduous fruit & nuts          C Citrus & subtropical
 V Vineyard            I Idle          X Unclassified fallow   YP Young perennial
S  Semi-agricultural   U/UR/UC/UI/UV Urban   NC/NV/NR/NW/NB Native   NS/E/Z unmapped
```

Subclass is the numeric crop within a class: `D12` = almonds, `D13` = walnuts,
`D14` = pistachios, `V` = grapes (grouped), `F16` = corn + sorghum/Sudan
(grouped for remote sensing), `P1` = alfalfa, `R1` = rice, `T16` = flowers /
nursery / Christmas trees, `C5` = avocados. Many subclasses are explicitly
"grouped for remote sensing" — the legend names which crops were merged.

### The field that actually holds the crop is `CLASS2`, not `CLASS1`

This is the single most important structural fact and it is easy to get wrong.
Verified from the FGDC `CLASS1` definition and confirmed against the data:

> "all Main Season summer crop data begins in column CLASS2; only multicropped
> fields (MULTIUSE = 'D', 'T', or 'Q'), or Mixed Use fields (MULTIUSE = 'M')
> will have a code in CLASS1 … all Single cropped fields will have no attribute
> in CLASS1"

Measured: `CLASS1` is the pad value `'**'` in 92-96 % of rows in every year,
while `CLASS2` is populated in 100 %. `SYMB_CLASS == CLASS2` in **100.0000 %**
of rows, in all seven years — checked row by row, not asserted.

`UCF_ATT` is a 37-character concatenation whose byte offsets the metadata
lists: MULTIUSE(1) then four 9-character blocks of
`CLASS(2) SUBCLASS(2) SPECOND(1) IRR_TYP_PA(1) IRR_TYP_PB(1) PCNT(2)`.
`'S********* V*****00…'` therefore reads "single land use, main-season crop V
(vineyard), 100 % of the polygon".

`MULTIUSE`: `S` single (93-96 %), `D` double, `T` triple, `Q` quadruple,
`I` intercropped, `M` mixed. `PCNT2` is `'00'` (meaning 100 %) in ≥ 99 % of rows.

---

## 3. How irrigation status is encoded — resolved

The printed legend says agricultural classes "are considered irrigated" unless
prefixed by a symbol that the PDF text layer loses. In the shapefile the
answer is unambiguous and comes from the FGDC definition of `IRR_TYP1PA`:

> **"This field is the irrigation status for the first land use (either
> irrigated or non-irrigated). All fields are presumed irrigated unless an 'n'
> for non-irrigated has been applied. This code refers to the status of the
> land, so a fallowed field will be mapped as 'irrigated' if the field is
> usually irrigated when a crop has been planted, even if no water has been
> applied this year."**

So:

- **`IRR_TYP2PA`** (block 2 = main-season crop) is the **irrigation status**.
  `'n'` = non-irrigated; `'*'` = pad = irrigated; 2016 and 2018 additionally
  use an explicit `'i'`.
- **`IRR_TYP2PB`** is the **irrigation *method*** (`F` furrow, `B` border strip,
  `H` hand-move sprinkler, `W` wild flooding, `D` surface drip, `M` micro
  sprinkler, `U` unknown, …). It is `'*'` in 98-100 % of rows: **irrigation
  method is effectively unmapped** in these statewide remote-sensing surveys
  and must not be used.
- Reading `IRR_TYP1PA` instead of `IRR_TYP2PA` would have found `'n'` on only
  ~200 of 440,000 polygons and produced a ~0 % non-irrigated share. That is the
  trap that block-1/block-2 confusion sets.

**There is no water-source field.** The legend defines source-of-irrigation
codes 1 = surface, 2 = mixed, 3 = groundwater, 4 = unknown, 5 = recycled, but
**no column in any survey year carries them**. Groundwater versus surface-water
supply therefore cannot be separated from this database — which matters,
because it is the groundwater share that GRACE could in principle see.

### What "irrigated" therefore means here

Because the flag describes the *land*, not the water applied in that year,
`irr == True` counts **irrigable** land including idle and fallow fields with
irrigation infrastructure. Two coverage numbers are carried through the whole
analysis and never conflated:

- `irr_frac_pct` — all irrigable ag land (classes G R F P T D C V YP I X)
- `irr_crop_frac_pct` — irrigable **and** carrying a crop this year
  (classes G R F P T D C V only; excludes I, X, YP)

Oregon's rule (`pct_irr>40 OR …`) was an actively-irrigated test, so
`irr_crop_frac_pct` is the like-for-like comparison and
`irr_frac_pct` is the ceiling.

Measured non-irrigated share of agricultural acreage:
0.8 % (2016), 1.4 % (2018), 3.8 % (2019), 2.8 % (2020), 2.2 % (2021),
2.9 % (2022), **4.6 % (2023)**. The upward drift may be real (drought
fallowing, SGMA) or may be increasing mapping effort; it is not separable here.

---

## 4. Schema changes between years — verified, not assumed

| change | years |
|---|---|
| whole schema differs (text crop names, no irrigation status) | 2014 only |
| `CLASS4`/`SUBCLASS4`/`PCNT4` (quadruple crop) added | 2018+ |
| `UniqueID` added | 2018+ |
| `EMRG_CROP`, `MAIN_CROP` added | 2019+ |
| `YR_PLANTED`, `SEN_CROP`, `HYDRO_RGN` added | 2020+ |
| `DataStatus`, `CTYP*_NOTE`, `ADOY_SEN`, `ADOY_EMRG` added | 2021+ |
| `Shape_STAr`/`Shape_STLe` present | 2016, 2018, 2019, 2021 — **absent 2020, 2022, 2023** |
| field names lower-case (`Symb_class`, `DWR_revise`, `Region`, `Acres`) | 2016 only |
| 2022 ships a bare shapefile with no legend/metadata PDF | 2022 |

**Trap 4 — the idle/fallow class code changes meaning between vintages.**
Statewide acreage by class (thousands of acres):

| class | 2014 | 2016 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 |
|---|---|---|---|---|---|---|---|---|
| `I` idle | 1,215 | 0 | 0 | — | — | 814 | 958 | 757 |
| `X` unclassified fallow | — | 949 | 995 | 818 | 1,103 | 601 | 504 | 327 |

2014 uses `I` only; 2016-2020 use `X` only; 2021-2023 use both. Any series that
treats `I` and `X` as distinct categories will show a spurious step at 2021.
They are pooled here.

`NR` (riparian vegetation) is mapped in 2014 and 2016 and absent from 2018 on;
`UL` (urban landscape) appears only from 2021. Neither is agricultural, but
both change the "all mapped acres" denominator, which is why the coverage table
reports agricultural fractions and not "fraction of mapped area".

---

## 5. Area field and CRS handling used downstream

- Area: the shipped `ACRES` (2018+) / `Acres` (2014, 2016, 2019-2021) field,
  converted at 1 acre = 0.00404686 km².
- Position: `representative_point()` of each polygon, reprojected to EPSG:4326.
  Median polygon is **9.1-11.9 acres** (0.037-0.048 km²) against a
  12,390 km² mascon, so assigning a whole polygon to the mascon containing its
  representative point mis-places at most ~4 × 10⁻⁶ of a mascon per polygon.
- Total mapped extent lon −124.37…−114.13, lat 32.44…42.00 — the survey is
  statewide, so no mascon in the study region is truncated by a survey boundary
  (unlike Oregon, where mascons crossed the state line).

Output: `processed/fields_all_years.parquet`, 3,310,882 rows
(year, lon, lat, acres, cls, subclass, crop, irr, multiuse), 85 MB.

---

## 6. The interpolation decision

**No interpolation between survey years is performed.** The eight years are
treated as eight independent snapshots and used only for:

1. **Coverage** (Phase 2) — the mean over 2016-2023 with the per-mascon min/max
   reported alongside, so the reader sees how little it moves. For mascon 1850
   the irrigated fraction ranges 50.8-53.0 % across seven surveys: a **4 %
   relative spread over eight years**. Irrigated *extent* is close to a
   constant on GRACE's timescale, so nothing is gained by interpolating it.
2. **Crop mix**, likewise as a slowly varying background.

The time-varying consumptive-use signal is taken from a different source with
annual coverage back to WY2002 (Phase 3), not from interpolating crop maps.
Interpolating an 8-point series onto 255 GRACE months would have manufactured
month-to-month structure that the survey does not contain — the exact failure
mode this test is supposed to detect, not commit.

---

## 7. What could not be established from this database

- **Water source (groundwater vs surface).** Legend-defined, never populated.
- **Consumptive use.** Not present in any form; there is no ET, applied-water
  or crop-coefficient field. It must come from elsewhere (Phase 3).
- **Irrigation method.** Field exists, ≥98 % unpopulated.
- **Sub-annual timing.** `ADOY1..ADOY4` give an "acquisition day of year" per
  crop slot, not a growth or irrigation schedule.
- **Accuracy.** The metadata claims "overall accuracies exceeding 95 %" for the
  Land IQ product but ships no confusion matrix in these zips, so per-class
  error is unquantified.
- **2014 irrigation status**, which simply does not exist, so 2014 is excluded
  from every irrigated-fraction statistic and used only for the all-farmland
  ceiling and the class-code cross-check.
