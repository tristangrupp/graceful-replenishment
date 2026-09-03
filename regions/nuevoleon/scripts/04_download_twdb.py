"""Amistad and Falcon whole-lake storage from Water Data for Texas.

CONAGUA's SINA series for the two international Rio Grande reservoirs alternates
between the whole-lake volume and Mexico's treaty allotment, most visibly between
the 2018-03-15 and 2018-05-15 snapshots (Amistad 2,484.7 -> 494.5 hm^3, Falcon
1,709.4 -> 231.8 hm^3, with `namoalmac` switching 4,040.3 -> 1,769.7 and
3,264.8 -> 1,351.6 in the same step). An ownership balance is not the water GRACE
weighs, so that series cannot be differenced against GRACE.

TWDB's `reservoir_storage` column - "actual storage at measured lake elevation" -
is the whole-lake figure. Confirmed by matching SINA on 2018-03-15 in the period
when SINA is also whole-lake: 2,013,173 ac-ft = 2,483.2 hm^3 at Amistad against
SINA's 2,484.7 (0.06%), and 1,384,408 ac-ft = 1,707.6 hm^3 at Falcon against
SINA's 1,709.4 (0.10%). TWDB's `conservation_storage` column is the *Texas* share
and does not match; it is not used.

Downloads are serial and unauthenticated.
"""

from pathlib import Path

import requests

OUT = Path(r"E:\Water\NuevoLeon\raw")
URLS = {
    "amistad": "https://waterdatafortexas.org/reservoirs/individual/amistad.csv",
    "falcon": "https://waterdatafortexas.org/reservoirs/individual/falcon.csv",
}

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, url in URLS.items():
        r = requests.get(url, timeout=300)
        print(url, r.status_code, len(r.content))
        if r.status_code == 200:
            (OUT / f"twdb_{name}.csv").write_bytes(r.content)
        else:
            raise SystemExit(f"{url} returned {r.status_code}")
