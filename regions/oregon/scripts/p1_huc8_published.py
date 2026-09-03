"""Phase 1: extract DRI's published HUC-8 annual totals for validating our
field-level aggregation (independent check that we reproduce their pipeline)."""
import pyogrio, pandas as pd, numpy as np

GDB = (r"E:\Water\Oregan\Appendix_6a_Field_and_HUC_Consumptive_Use_Geodatabase"
       r"\or_huc_boundaries.gdb\or_huc_boundaries.gdb")
OUT = r"E:\Water\Oregan\analysis\processed\huc8_published_annual.parquet"

df = pyogrio.read_dataframe(GDB, layer="or_openet_huc8_irrigated_all",
                            read_geometry=False)
print("rows:", len(df))
print("columns:", len(df.columns))
print([c for c in df.columns][:40])

rows = []
for y in range(1985, 2023):
    yy = f"{y % 100:02d}"           # published columns use 2-DIGIT years
    sub = pd.DataFrame({
        "huc8": df["HUC8_code"],
        "water_year": y,
        "acres_pub": df.get(f"ACRES_{yy}"),
        "et_v_pub": df.get(f"ET_v_{yy}"),
        "cu_v_pub": df.get(f"CU_v_{yy}"),
        "aw_v_pub": df.get(f"AW_v_{yy}"),
        "eff_v_pub": df.get(f"EFF_v_{yy}"),
        "ppt_v_pub": df.get(f"PPT_v_{yy}"),
        "niwr_v_pub": df.get(f"NIWR_v_{yy}"),
    })
    rows.append(sub)
out = pd.concat(rows, ignore_index=True)
out["huc8"] = pd.to_numeric(out["huc8"], errors="coerce").astype("Int64")
out.to_parquet(OUT, index=False)
print("\nwrote", OUT, out.shape)
print(out.groupby("water_year")[["acres_pub", "cu_v_pub", "et_v_pub"]]
      .sum().tail(8).to_string())
print("\nstatewide totals (all HUC8, WY2015):")
s = out[out.water_year == 2015].sum(numeric_only=True)
print(s.to_string())
