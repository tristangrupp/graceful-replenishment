"""Phase 1e - period of content, purpose, lineage and ACRES definition per year."""
import re
from pathlib import Path

FILES = {
    2014: r"E:\Water\CentralValley\tmp\cm_2014\i15_Crop_Mapping_2014_SHP\i15_Crop_Mapping_2014.shp.xml",
    2016: r"E:\Water\CentralValley\tmp\cm_2016\i15_Crop_Mapping_2016_SHP\i15_Crop_Mapping_2016.shp.xml",
    2018: r"E:\Water\CentralValley\tmp\cm_2018\i15_Crop_Mapping_2018_SHP\i15_Crop_Mapping_2018.shp.xml",
    2019: r"E:\Water\CentralValley\tmp\cm_2019\i15_Crop_Mapping_2019\i15_Crop_Mapping_2019.shp.xml",
    2020: r"E:\Water\CentralValley\tmp\cm_2020\i15_Crop_Mapping_2020\i15_Crop_Mapping_2020.shp.xml",
    2021: r"E:\Water\CentralValley\tmp\cm_2021\i15_Crop_Mapping_2021_SHP\i15_Crop_Mapping_2021.shp.xml",
    2022: r"E:\Water\CentralValley\tmp\cm_2022\i15_crop_mapping_2022.shp.xml",
    2023: r"E:\Water\CentralValley\tmp\cm_2023\i15_Crop_Mapping_Final_2023.shp.xml",
}

TAGS = ["abstract", "purpose", "timeperd", "current", "rngdates", "sngdate",
        "caldate", "begdate", "enddate", "attracc", "logic", "complete"]


def txt(s):
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip()


for y, p in FILES.items():
    p = Path(p)
    if not p.exists():
        print(f"{y}: MISSING {p}")
        continue
    t = p.read_text(encoding="utf-8", errors="replace")
    print(f"\n================= {y} =================")
    for tag in ["abstract", "purpose", "timeperd", "complete", "attraccr"]:
        m = re.search(rf"<{tag}>(.*?)</{tag}>", t, re.S)
        if m:
            print(f"[{tag}] {txt(m.group(1))[:900]}")
    # ACRES / Acres definition
    for b in re.split(r"(?=<attrlabl>)", t):
        m = re.match(r"<attrlabl>(.*?)</attrlabl>", b)
        if m and m.group(1).strip().upper() in ("ACRES", "CROP2014", "DWR_STANDA"):
            print(f"[{m.group(1).strip()}] {txt(b)[:800]}")
