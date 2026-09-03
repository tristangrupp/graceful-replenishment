"""Phase 1/4: aggregate 259k field-level monthly volumes to 0.5-deg cells.

One DuckDB pass per water-year CSV. Grouping key is
(grid_i, grid_j, HUC8, is_irrigated) so the result can be re-aggregated
later either to mascon cells (grid_i/grid_j) or to HUC-8 (for validation
against DRI's published HUC-8 annual totals).

Water-year convention (verified from column names, not assumed): file
`..._1mo_<Y>_final.csv` holds months 11/(Y-1), 12/(Y-1), 01/Y ... 10/Y.
The column suffix `_MM_YY_` is the TRUE CALENDAR month and 2-digit year, so
every value is emitted on its own calendar timestamp and the "water year
shift" never has to be undone.

Irrigation status reproduces README step 3:
  irrigated = pct_irr > 40
           OR (pct_wet > 40 AND srctype > 0 AND etof_status <> 1)
`srctype`/`IRR_EFF` are 0 (not NULL) in the CSVs where the shapefile has NaN.

Half-degree cell indexing matches the GSFC grid: cell centers at
-180 + (i+0.5)*0.5, i.e. ..., -124.75, -124.25, ...
"""
import sys, time
import duckdb
import pandas as pd

SRC = (r"E:\Water\Oregan\Appendix_6a_Field_and_HUC_Consumptive_Use_Geodatabase"
       r"\or_openet_ensemble_etdemands_monthly_water_year_shift_1mo_%d_final.csv")
CENT = r"E:\Water\Oregan\analysis\processed\field_centroids.parquet"
OUT = r"E:\Water\Oregan\analysis\processed\cell_monthly.parquet"

# (out_name, csv column template) -- all acre-feet
VARS = [
    ("eta_af",    'ET_VOLUME_{mm}_{yy}_acft'),
    ("eto_af",    'ETO_VOLUME_{mm}_{yy}_acft'),
    ("etc_af",    'ETDa_VOLUME_{mm}_{yy}_acft'),
    ("ppt_af",    'PPT_VOLUME_{mm}_{yy}_acft'),
    ("eff_af",    'EFF_VOLUME_{mm}_{yy}_acft'),
    ("effadj_af", 'EFF_VOLUMEadj_{mm}_{yy}_acft'),
    ("cu_af",     'IRR_CU_VOLUME_{mm}_{yy}_acft'),
    ("cuadj_af",  'IRR_CU_VOLUMEadj_{mm}_{yy}_acft'),
    ("niwr_af",   'NIWR_VOLUME_{mm}_{yy}_acft'),
    ("aw_af",     'AW_{mm}_{yy}_acft'),
]


def months_of(wy):
    """[(cal_year, cal_month), ...] for water year wy: Nov(wy-1)..Oct(wy)."""
    return [(wy - 1, 11), (wy - 1, 12)] + [(wy, m) for m in range(1, 11)]


def build_sql(wy):
    yy = f"{wy % 100:02d}"
    csv = SRC % wy
    aggs = []
    for cy, mo in months_of(wy):
        mm, yy2 = f"{mo:02d}", f"{cy % 100:02d}"
        for out, tmpl in VARS:
            col = tmpl.format(mm=mm, yy=yy2)
            aggs.append(f'sum(c."{col}") AS "{out}|{cy}-{mo:02d}"')
    agg_sql = ",\n    ".join(aggs)
    return f"""
WITH c AS (
  SELECT * FROM read_csv_auto('{csv}')
),
j AS (
  SELECT c.*, f.lon, f.lat
  FROM c JOIN read_parquet('{CENT}') f USING (OPENET_ID)
)
SELECT
    CAST(floor((lon + 180) * 2) AS INT) AS grid_i,
    CAST(floor((lat + 90) * 2) AS INT)  AS grid_j,
    c."HUC8" AS huc8,
    (c."%_IRRIGATED_{yy}" > 40
     OR (c."%_WETLAND_{yy}" > 40 AND c."srctype" > 0
         AND c."ETOF_IRR_STATUS_{yy}_MODE" <> 1)) AS is_irrigated,
    count(*) AS n_fields,
    sum(c."ACRES_FTR_GEOM_{yy}") AS acres,
    {agg_sql}
FROM j c
GROUP BY 1, 2, 3, 4
"""


def main():
    years = list(range(1985, 2023))
    con = duckdb.connect()
    frames = []
    for wy in years:
        t0 = time.time()
        wide = con.execute(build_sql(wy)).fetchdf()
        idc = ["grid_i", "grid_j", "huc8", "is_irrigated", "n_fields", "acres"]
        long = wide.melt(id_vars=idc, var_name="vk", value_name="value")
        long[["var", "ym"]] = long["vk"].str.split("|", expand=True)
        long = long.drop(columns="vk")
        tidy = long.pivot_table(index=idc + ["ym"], columns="var",
                                values="value", aggfunc="sum").reset_index()
        tidy["water_year"] = wy
        tidy["time"] = pd.to_datetime(tidy["ym"] + "-01")
        frames.append(tidy.drop(columns="ym"))
        print(f"WY{wy}: {len(wide)} groups -> {len(tidy)} rows  "
              f"acres={wide['acres'].sum():,.0f}  {time.time()-t0:.1f}s", flush=True)

    out = pd.concat(frames, ignore_index=True)
    out.to_parquet(OUT, index=False)
    print("\nwrote", OUT, out.shape)
    print(out.dtypes.to_string())


if __name__ == "__main__":
    main()
