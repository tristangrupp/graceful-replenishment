"""Run the decorrelation analysis for a set of regions."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from grace_region import analyse
from region_figure import make_figure

REGIONS = {
    "Nuevo Leon, Mexico": dict(
        out=r"E:\Water\NuevoLeon",
        lat=(23.2, 27.8), lon=(-101.2, -98.4),
    ),
    "Mississippi": dict(
        out=r"E:\Water\Mississippi",
        lat=(30.1, 35.0), lon=(-91.7, -88.1),
    ),
    "California Central Valley": dict(
        out=r"E:\Water\CentralValley",
        lat=(34.8, 40.5), lon=(-122.4, -118.6),
        note="The Sierra Nevada bounds this region to the east. Mascons that straddle the crest\n"
             "mix valley groundwater with mountain snowpack, which is a different signal on a\n"
             "different schedule.",
    ),
    "Iran": dict(
        out=r"E:\Water\Iran",
        lat=(25.0, 39.5), lon=(44.0, 63.0),
    ),
}


def main(only=None):
    results = {}
    for name, cfg in REGIONS.items():
        if only and name not in only:
            continue
        print(f"\n=== {name} ===")
        summary, mascons, ds, pairs, binned = analyse(
            name, cfg["lat"], cfg["lon"], cfg["out"])
        path = make_figure(name, cfg["out"], summary, mascons, ds, pairs, binned,
                           note=cfg.get("note", ""))
        print(json.dumps(summary, indent=2))
        print("figure:", path)
        results[name] = summary
    return results


if __name__ == "__main__":
    main(sys.argv[1:] or None)
