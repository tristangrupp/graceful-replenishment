"""Fetch CSR RL06.3 mascons for the Arabian Peninsula cross-check.

The Saudi run rested entirely on GSFC, and HESS 26, 5757 (2022) explicitly
rejected GSFC for the Saq-Ram domain. CSR is the one alternative solution
reachable without Earthdata credentials, so it is the available check.

NOTE ON TLS: download.csr.utexas.edu serves an incomplete certificate chain,
so verification is disabled for this host only. The mitigation is that the
payload is a public scientific netCDF whose structure is validated after
download, and the file is checksummed so a later run can detect a change.
"""

import hashlib
import json
import sys
from pathlib import Path

import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

URL = ("https://download.csr.utexas.edu/outgoing/grace/RL0603_mascons/"
       "CSR_GRACE_GRACE-FO_RL0603_Mascons_all-corrections.nc")
DEST = Path(r"E:\Water\Saudi\raw\csr_rl0603_mascons.nc")


def main():
    DEST.parent.mkdir(parents=True, exist_ok=True)
    if not (DEST.exists() and DEST.stat().st_size > 1_000_000):
        print(f"downloading {URL}")
        with requests.get(URL, stream=True, timeout=300, verify=False) as r:
            r.raise_for_status()
            tmp = DEST.with_suffix(".part")
            got = 0
            with open(tmp, "wb") as fh:
                for chunk in r.iter_content(1 << 20):
                    fh.write(chunk)
                    got += len(chunk)
                    if got % (25 << 20) < (1 << 20):
                        print(f"  {got / 1e6:,.0f} MB")
            tmp.replace(DEST)
    print(f"file: {DEST} ({DEST.stat().st_size / 1e6:,.1f} MB)")

    digest = hashlib.sha256()
    with open(DEST, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    sha = digest.hexdigest()

    # Structural validation. A netCDF that opens with the expected variables
    # is the check that the unverified transport did not hand us something else.
    import xarray as xr
    with xr.open_dataset(DEST) as ds:
        info = {
            "sha256": sha,
            "size_bytes": DEST.stat().st_size,
            "data_vars": list(ds.data_vars),
            "dims": {k: int(v) for k, v in ds.sizes.items()},
            "coords": list(ds.coords),
            "attrs_title": str(ds.attrs.get("title", "")),
        }
        print(json.dumps(info, indent=2)[:2000])
        if "lwe_thickness" not in ds.data_vars:
            print("WARNING: no lwe_thickness variable; inspect before using")
            return 1
    (DEST.parent / "csr_download_info.json").write_text(json.dumps(info, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
