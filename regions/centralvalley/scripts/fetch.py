"""Robust downloader. The CNRA host resets TLS connections intermittently and
refuses a non-browser user agent, so every request retries with backoff."""
import sys
import time
from pathlib import Path

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
HDR = {"User-Agent": UA, "Accept": "*/*"}


def get(url, tries=8, timeout=180, **kw):
    last = None
    for k in range(tries):
        try:
            r = requests.get(url, headers=HDR, timeout=timeout, **kw)
            if r.status_code >= 500:
                raise RuntimeError(f"HTTP {r.status_code}")
            return r
        except Exception as e:
            last = e
            time.sleep(min(30, 2 ** k))
    raise RuntimeError(f"GET {url} failed after {tries}: {last}")


def download(url, dest, tries=8):
    dest = Path(dest)
    if dest.exists() and dest.stat().st_size > 0:
        return dest, "cached"
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = None
    for k in range(tries):
        try:
            with requests.get(url, headers=HDR, timeout=300, stream=True) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(1 << 20):
                        fh.write(chunk)
                tmp.replace(dest)
            return dest, "ok"
        except Exception as e:
            last = e
            time.sleep(min(30, 2 ** k))
    return None, f"FAILED: {last}"
