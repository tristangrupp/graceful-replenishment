"""Phase 1d - pull FGDC attribute definitions and value domains out of the
shapefile sidecar .shp.xml metadata (authoritative DWR documentation)."""
import re
import sys
from pathlib import Path

WANT = {"IRR_TYP2PA", "IRR_TYP2PB", "IRR_TYP1PA", "SPECOND2", "SPECOND1",
        "MULTIUSE", "SYMB_CLASS", "CLASS1", "CLASS2", "SUBCLASS2", "PCNT2",
        "ACRES", "ACRES ", "DWR_REVISE", "UCF_ATT", "MAIN_CROP", "EMRG_CROP",
        "DATASTATUS", "CROP2014", "DWR_STANDA", "YR_PLANTED", "SEN_CROP"}


def dump(path, limit=2600):
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    print(f"##### {path}  ({len(t)} chars)")
    for b in re.split(r"(?=<attrlabl>)", t):
        m = re.match(r"<attrlabl>(.*?)</attrlabl>", b)
        if not m:
            continue
        lab = m.group(1).strip()
        if lab.upper() not in WANT:
            continue
        body = re.sub(r"<[^>]+>", "\n", b)
        body = re.sub(r"\n\s*\n+", "\n", body).strip()
        print("\n############", lab, "\n", body[:limit])


if __name__ == "__main__":
    for p in sys.argv[1:]:
        dump(p)
