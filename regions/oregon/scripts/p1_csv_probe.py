"""Phase 1: DuckDB probe of one yearly CSV -- nodata conventions, ranges, timing."""
import time, duckdb

CSV = (r"E:\Water\Oregan\Appendix_6a_Field_and_HUC_Consumptive_Use_Geodatabase"
       r"\or_openet_ensemble_etdemands_monthly_water_year_shift_1mo_2015_final.csv")

con = duckdb.connect()
t0 = time.time()
q = f"""
SELECT
  count(*) AS n_rows,
  count(DISTINCT OPENET_ID) AS n_ids,
  sum(CASE WHEN "ACRES_FTR_GEOM_15" IS NULL THEN 1 ELSE 0 END) AS null_acres,
  sum(CASE WHEN "%_IRRIGATED_15" IS NULL THEN 1 ELSE 0 END) AS null_pctirr,
  sum(CASE WHEN "%_WETLAND_15" IS NULL THEN 1 ELSE 0 END) AS null_pctwet,
  sum(CASE WHEN "ETOF_IRR_STATUS_15_MODE" IS NULL THEN 1 ELSE 0 END) AS null_status,
  sum(CASE WHEN "srctype" IS NULL THEN 1 ELSE 0 END) AS null_srctype,
  sum(CASE WHEN "IRR_EFF" IS NULL THEN 1 ELSE 0 END) AS null_irreff,
  sum(CASE WHEN "ETa_07_15_in" IS NULL THEN 1 ELSE 0 END) AS null_eta07,
  sum(CASE WHEN "ET_VOLUME_07_15_acft" IS NULL THEN 1 ELSE 0 END) AS null_etvol07,
  sum(CASE WHEN "IRR_CU_VOLUMEadj_07_15_acft" IS NULL THEN 1 ELSE 0 END) AS null_cuadj07,
  sum(CASE WHEN "AW_07_15_acft" IS NULL THEN 1 ELSE 0 END) AS null_aw07,
  min("ETa_07_15_in") AS eta07_min, max("ETa_07_15_in") AS eta07_max,
  min("ETa_01_15_in") AS eta01_min, max("ETa_01_15_in") AS eta01_max,
  min("IRR_CU_VOLUMEadj_07_15_acft") AS cuadj07_min,
  max("IRR_CU_VOLUMEadj_07_15_acft") AS cuadj07_max,
  min("WS_C_07_15_acft") AS wsc_min, max("WS_C_07_15_acft") AS wsc_max,
  min("%_IRRIGATED_15") AS pctirr_min, max("%_IRRIGATED_15") AS pctirr_max,
  sum("ACRES_FTR_GEOM_15") AS tot_acres
FROM read_csv_auto('{CSV}')
"""
r = con.execute(q).fetchdf()
print("elapsed %.1fs" % (time.time() - t0))
for c in r.columns:
    print(f"  {c:16s} {r[c].iloc[0]}")

print("\n--- ETOF_IRR_STATUS_15_MODE distribution ---")
print(con.execute(
    f"""SELECT "ETOF_IRR_STATUS_15_MODE" AS st, count(*) n
        FROM read_csv_auto('{CSV}') GROUP BY 1 ORDER BY 1"""
).fetchdf().to_string(index=False))

print("\n--- consistency: does IRR_CU_VOLUME == ET_VOLUME - EFF_VOLUME? (Jul 2015) ---")
print(con.execute(
    f"""SELECT round(max(abs("IRR_CU_VOLUME_07_15_acft"
             - ("ET_VOLUME_07_15_acft" - "EFF_VOLUME_07_15_acft"))),6) AS max_abs_resid
        FROM read_csv_auto('{CSV}')"""
).fetchdf().to_string(index=False))

print("\n--- does ET_VOLUME == ETa_in/12 * acres? (Jul 2015) ---")
print(con.execute(
    f"""SELECT round(max(abs("ET_VOLUME_07_15_acft"
             - "ETa_07_15_in"/12.0*"ACRES_FTR_GEOM_15")),6) AS max_abs_resid
        FROM read_csv_auto('{CSV}')"""
).fetchdf().to_string(index=False))

print("\n--- AW == CUadj / IRR_EFF ? (Jul 2015, IRR_EFF>0) ---")
print(con.execute(
    f"""SELECT round(max(abs("AW_07_15_acft" - "IRR_CU_VOLUMEadj_07_15_acft"/"IRR_EFF")),6) AS max_abs_resid
        FROM read_csv_auto('{CSV}') WHERE "IRR_EFF" > 0"""
).fetchdf().to_string(index=False))
