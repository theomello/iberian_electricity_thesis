#!/usr/bin/env python3
"""Fetch E-OBS daily precipitation and keep the Iberian Peninsula.

    .venv/bin/python scripts/fetch/fetch_eobs_precipitation.py

E-OBS is the European gridded daily dataset built from weather-station
observations (ECA&D, KNMI; Cornes et al. 2018). Used here for rainfall over
every hydro plant's catchment in Spain and Portugal, replacing the single ERA5
points of `fetch_hydro_precipitation.py`, which cost about 220 Open-Meteo calls
per point for 2018-2026 and cannot cover a grid within the free limits.

FILES (downloaded 2026-10-02 on the user's approval, ensemble mean, 0.25 degree):
  rr_ens_mean_0.25deg_reg_v33.0e.nc   1950-01-01 -> 2025-12-31, 738 MB
  rr_0.25deg_day_2026_grid_ensmean.nc 2026, through the last month KNMI has added
                                       (August on 2026-09-11), 68 MB; KNMI replaces
                                       it as months are added, so it is re-fetched
                                       whenever its size changes.
Terms: non-commercial research and education only; cite Cornes et al. (2018) and
the E-OBS dataset (ECA&D).

OUTPUT: data/eobs/eobs_rr_iberia_daily.parquet, one row per land cell and day,
1991-01-01 onwards (1991-2020 gives the climate normals that rainfall anomalies
are measured against): date, lat, lon, rr (mm/day). Cells are 0.25 degree, inside
35.8-44.0 N and 9.6 W - 3.4 E; sea cells (always missing) are dropped. The raw
files stay in data/eobs/raw/.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

BASE = "https://knmi-ecad-assets-prd.s3.amazonaws.com/ensembles/data"
FILES = {
    "rr_ens_mean_0.25deg_reg_v33.0e.nc": f"{BASE}/Grid_0.25deg_reg_ensemble/rr_ens_mean_0.25deg_reg_v33.0e.nc",
    "rr_0.25deg_day_2026_grid_ensmean.nc": f"{BASE}/months/ens/rr_0.25deg_day_2026_grid_ensmean.nc",
}
OUT = DATA / "eobs"
RAW = OUT / "raw"
IBERIA = {"lat": (35.8, 44.0), "lon": (-9.6, 3.4)}
FIRST = "1991-01-01"


def download(sess, name: str, url: str) -> Path:
    """Stream to .part and rename once the size matches the server's; skip a file
    already complete at the server's current size."""
    path = RAW / name
    size = int(sess.head(url, timeout=60).headers["Content-Length"])
    if path.exists() and path.stat().st_size == size:
        print(f"  {name}: on disk ({size / 1e6:.0f} MB)")
        return path
    part = path.with_suffix(".part")
    with sess.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(part, "wb") as f:
            for chunk in r.iter_content(1 << 22):
                f.write(chunk)
    if part.stat().st_size != size:
        raise RuntimeError(f"{name}: got {part.stat().st_size} bytes, expected {size}")
    part.rename(path)
    print(f"  {name}: downloaded ({size / 1e6:.0f} MB)")
    return path


def iberia(path: Path) -> pd.DataFrame:
    ds = xr.open_dataset(path)
    lat = "latitude" if "latitude" in ds.coords else "lat"
    lon = "longitude" if "longitude" in ds.coords else "lon"
    sub = ds["rr"].sel({lat: slice(*IBERIA["lat"]), lon: slice(*IBERIA["lon"])}).sel(time=slice(FIRST, None))
    df = sub.to_dataframe().reset_index().rename(columns={"time": "date", lat: "lat", lon: "lon"})
    df = df.dropna(subset=["rr"])
    return df[["date", "lat", "lon", "rr"]].astype({"lat": "float32", "lon": "float32", "rr": "float32"})


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    sess = session()
    paths = [download(sess, n, u) for n, u in FILES.items()]
    parts = [iberia(p) for p in paths]
    d = pd.concat(parts, ignore_index=True)
    d["date"] = pd.to_datetime(d.date)
    d = d.drop_duplicates(["date", "lat", "lon"], keep="last")
    cells = d.groupby(["lat", "lon"]).size()
    out = OUT / "eobs_rr_iberia_daily.parquet"
    d.sort_values(["date", "lat", "lon"]).to_parquet(out, index=False)
    print(f"wrote {out}: {len(d):,} rows, {len(cells)} land cells, {d.date.min().date()} -> {d.date.max().date()}")
    days = pd.date_range(d.date.min(), d.date.max())
    missing = days.difference(pd.DatetimeIndex(d.date.unique()))
    print(f"days without any value: {len(missing)}" + (f" (first {list(missing[:3].date)})" if len(missing) else ""))
    print(f"mean annual precipitation over the cells, 1991-2020: "
          f"{d[d.date.dt.year.between(1991, 2020)].groupby(d.date.dt.year).rr.mean().mean() * 365.25:.0f} mm")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
