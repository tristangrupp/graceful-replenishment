"""Phase 1: enumerate GDB layers + dump the two xlsx data dictionaries."""
import sys
import pyogrio
import openpyxl

BASE = r"E:\Water\Oregan"
A6A = BASE + r"\Appendix_6a_Field_and_HUC_Consumptive_Use_Geodatabase"

gdbs = [
    A6A + r"\or_field_boundaries.gdb\or_field_boundaries.gdb",
    A6A + r"\or_huc_boundaries.gdb\or_huc_boundaries.gdb",
]

for g in gdbs:
    print("=" * 80)
    print("GDB:", g)
    try:
        for name, geom in pyogrio.list_layers(g):
            print(f"   layer={name!r:60s} geom={geom}")
    except Exception as e:
        print("   ERROR:", type(e).__name__, e)

print("=" * 80)
print("Oregon_Hyd_Area_Ag_Boundaries_20241016 dir:")
import os
d = A6A + r"\Oregon_Hyd_Area_Ag_Boundaries_20241016"
for f in sorted(os.listdir(d)):
    print("  ", f, os.path.getsize(os.path.join(d, f)))

for xl in [BASE + r"\Appendix_1_Field_Boundary_Geodatabase_Attributes.xlsx",
           BASE + r"\Appendix_2_Watershed_Geodatabase_Attributes.xlsx"]:
    print("=" * 80)
    print("XLSX:", xl)
    wb = openpyxl.load_workbook(xl, read_only=True, data_only=True)
    for ws in wb.worksheets:
        print(f"--- sheet {ws.title!r}")
        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c).strip() for c in row]
            if not any(cells):
                continue
            print("   | " + " | ".join(cells))
    wb.close()
