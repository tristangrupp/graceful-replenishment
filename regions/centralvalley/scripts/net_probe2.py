"""Second network probe: browser user-agent, and the specific data endpoints
that matter for Phase 3."""
import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")
H = {"User-Agent": UA, "Accept": "*/*"}

URLS = [
    ("cnra-ckan", "https://data.cnra.ca.gov/api/3/action/package_search?q=cimis&rows=3"),
    ("cnra-root", "https://data.cnra.ca.gov/"),
    ("ca-ckan", "https://data.ca.gov/api/3/action/package_search?q=cimis&rows=3"),
    ("sgma", "https://sgma.water.ca.gov/webgis/?appid=SGMADataViewer"),
    ("waterdata-nwis", "https://waterservices.usgs.gov/nwis/dv/?format=json&sites=11303500&parameterCd=00060&startDT=2020-01-01&endDT=2020-01-05"),
    ("prism-ftp", "https://ftp.prism.oregonstate.edu/monthly/ppt/2020/"),
    ("openet-ts", "https://openet-api.org/raster/timeseries/point"),
    ("nasa-gldas", "https://hydro1.gesdisc.eosdis.nasa.gov/data/GLDAS/"),
    ("noaa-nclimgrid", "https://www.ncei.noaa.gov/pub/data/daily-grids/"),
    ("cimis-api", "https://et.water.ca.gov/api/data?appKey=test&targets=2&startDate=2020-01-01&endDate=2020-01-02"),
]
for name, url in URLS:
    try:
        r = requests.get(url, timeout=45, headers=H)
        print(f"{name:16s} {r.status_code} {r.headers.get('content-type','')[:35]:35s} "
              f"{len(r.content):>9,} B  {r.text[:120]!r}")
    except Exception as e:
        print(f"{name:16s} FAIL {type(e).__name__}: {str(e)[:110]}")
