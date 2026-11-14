#!/usr/bin/env python3
"""MERRA-2 hourly 2 m air temperature over Iberia (NASA GES DISC, Earthdata Cloud OPeNDAP).

    .venv/bin/python scripts/fetch/fetch_merra2_t2m.py [--start 2018-01-01 --end 2021-12-31]

Token: EARTHDATA_TOKEN in the gitignored .env (Earthdata Login user token; the
app "NASA GESDISC DATA ARCHIVE" must be approved). One file per day in
data/merra2/raw/T2M_YYYYMMDD.nc4, T2M only, box 35.5-44 N, 10 W-4 E
(0.5 x 0.625 degree grid), 24 hours UTC, ~58 KB a day. Resumable.

Files are named MERRA2_400 except Sep 2020 and Jun-Sep 2021 (MERRA2_401), so both are tried.
Route: M2T1NXSLV v5.12.4 (DOI 10.5067/VJAFPLI1CSIV), collection C1276812863-GES_DISC,
DAP4 constraint expression on opendap.earthdata.nasa.gov. The old goldsmr4 OPeNDAP host
answers 410. Cite: GMAO (2015), MERRA-2 tavg1_2d_slv_Nx, GES DISC.
"""
import argparse, datetime as dt, sys, time
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from config import require_token  # noqa: E402

OUT = ROOT / "data" / "merra2" / "raw"
LA0, LA1 = int((35.5 + 90) / 0.5), int((44 + 90) / 0.5)
LO0, LO1 = int((-10 + 180) / 0.625), int((4 + 180) / 0.625)
BASE = ("https://opendap.earthdata.nasa.gov/collections/C1276812863-GES_DISC/granules/"
        "M2T1NXSLV.5.12.4%3AMERRA2_{s}.tavg1_2d_slv_Nx.{d}.nc4.dap.nc4")
CE = f"?dap4.ce=/T2M[0:23][{LA0}:{LA1}][{LO0}:{LO1}];/time;/lat[{LA0}:{LA1}];/lon[{LO0}:{LO1}]"

ap = argparse.ArgumentParser()
ap.add_argument("--start", default="2018-01-01")
ap.add_argument("--end", default="2021-12-31")
a = ap.parse_args()
H = {"Authorization": "Bearer " + require_token("EARTHDATA_TOKEN")}
OUT.mkdir(parents=True, exist_ok=True)
d, end, got, bad = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end), 0, []
while d <= end:
    f = OUT / f"T2M_{d:%Y%m%d}.nc4"
    if not f.exists():
        ok = False
        for k in range(3):
            for stream in ("400", "401"):  # September 2020 and June-September 2021 are stream 401
                r = requests.get(BASE.format(d=f"{d:%Y%m%d}", s=stream) + CE, headers=H, timeout=180)
                if r.ok and r.content[:4] == b"\x89HDF":
                    f.write_bytes(r.content); got += 1; ok = True; break
                if r.status_code in (401, 403):
                    sys.exit(f"auth failed ({r.status_code}): check the token and the GESDISC approval")
            if ok:
                break
            time.sleep(5 * (k + 1))
        if not ok:
            bad.append(d.isoformat())
        time.sleep(0.3)
    d += dt.timedelta(days=1)
print(f"fetched {got}, failed {len(bad)} {bad[:10]}")
sys.exit(1 if bad else 0)
