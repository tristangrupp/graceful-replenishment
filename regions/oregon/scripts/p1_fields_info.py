"""Phase 1: field boundary schema/CRS + CSV row-grain sanity checks."""
import pyogrio, pandas as pd, numpy as np

SHP = (r"E:\Water\Oregan\Appendix_6a_Field_and_HUC_Consumptive_Use_Geodatabase"
       r"\Oregon_Hyd_Area_Ag_Boundaries_20241016"
       r"\Oregon_Hyd_Area_Ag_Boundaries_20241016.shp")

info = pyogrio.read_info(SHP)
print("FEATURES:", info["features"])
print("GEOMETRY:", info["geometry_type"])
print("CRS:", info["crs"])
print("\nFIELDS (name, dtype):")
for n, d in zip(info["fields"], info["dtypes"]):
    print(f"   {n:20s} {d}")

print("\n--- head of attribute table (no geometry) ---")
df = pyogrio.read_dataframe(SHP, read_geometry=False, max_features=5)
pd.set_option("display.width", 250, "display.max_columns", 100)
print(df.to_string())

print("\n--- CSV row grain: 1985 first 3 rows, key cols ---")
CSV = (r"E:\Water\Oregan\Appendix_6a_Field_and_HUC_Consumptive_Use_Geodatabase"
       r"\or_openet_ensemble_etdemands_monthly_water_year_shift_1mo_1985_final.csv")
cols = ["OPENET_ID", "ACRES_FTR_GEOM_85", "HUC8", "HUC12", "%_IRRIGATED_85",
        "CROP_1985", "ETD_85", "ETOF_IRR_STATUS_85_MODE", "srctype", "ITYPE",
        "IRR_EFF", "GRIDMET_ID", "OWRD", "Region",
        "ETa_07_85_in", "ET_VOLUME_07_85_acft",
        "IRR_CU_VOLUME_07_85_acft", "IRR_CU_VOLUMEadj_07_85_acft",
        "AW_07_85_acft", "WS_C_07_85_acft"]
d = pd.read_csv(CSV, nrows=5, usecols=cols)
print(d[cols].to_string())

print("\n--- duplicate OPENET_ID check on 200k rows ---")
ids = pd.read_csv(CSV, usecols=["OPENET_ID"])
print("rows:", len(ids), "unique OPENET_ID:", ids["OPENET_ID"].nunique())
print("dtype:", ids["OPENET_ID"].dtype, "sample:", ids["OPENET_ID"].head(3).tolist())
