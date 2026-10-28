#!/usr/bin/env python3
"""Population-weighted Italian temperature, for the Italian side of the gas-cap comparison.

    .venv/bin/python scripts/fetch/fetch_italy_temperature.py

Writes data/weather/temperature_population_italy.parquet: one row per UTC hour,
2021-01-01 -> 2023-12-31, `temp_pop_it` (population-weighted over twelve cities),
`cdh_it` and `hdh_it` (cooling and heating degree hours, base 18 C). Raw city series in
data/weather/raw_temp_it_<city>.parquet; resumable.

Same source and rule as `fetch_population_temperature.py` (Open-Meteo's ERA5 archive,
token-free; approximate municipal populations as weights, adequate because temperature is
strongly correlated across a country). Mainland and the two large islands, which clear in
GME's day-ahead market (zones SICI, SARD). ERA5: Copernicus / ECMWF.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

OUT = DATA / "weather"
API = "https://archive-api.open-meteo.com/v1/archive"
START, END = "2021-01-01", "2023-12-31"
CITIES = [  # name, lat, lon, approximate municipal population
    ("roma", 41.9028, 12.4964, 2_750_000), ("milano", 45.4642, 9.1900, 1_370_000),
    ("napoli", 40.8518, 14.2681, 910_000), ("torino", 45.0703, 7.6869, 840_000),
    ("palermo", 38.1157, 13.3615, 630_000), ("genova", 44.4056, 8.9463, 560_000),
    ("bologna", 44.4949, 11.3426, 390_000), ("firenze", 43.7696, 11.2558, 360_000),
    ("bari", 41.1171, 16.8719, 315_000), ("catania", 37.5079, 15.0830, 300_000),
    ("venezia", 45.4408, 12.3155, 255_000), ("verona", 45.4384, 10.9916, 255_000),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    s = session()
    parts = []
    for name, lat, lon, pop in CITIES:
        p = OUT / f"raw_temp_it_{name}.parquet"
        if not p.exists():
            r = s.get(API, params={"latitude": lat, "longitude": lon, "start_date": START,
                                   "end_date": END, "hourly": "temperature_2m", "timezone": "UTC"},
                      timeout=300)
            r.raise_for_status()
            df = pd.DataFrame(r.json()["hourly"])
            df["utc_timestamp"] = pd.to_datetime(df.pop("time"), utc=True)
            df["city"], df["population"] = name, pop
            df.to_parquet(p, index=False)
            print(f"  fetched {name}", flush=True)
            time.sleep(1.0)
        parts.append(pd.read_parquet(p))
    long = pd.concat(parts, ignore_index=True)
    long["x"] = long.temperature_2m * long.population
    g = long.groupby("utc_timestamp")
    idx = (g.x.sum() / g.population.sum()).rename("temp_pop_it").reset_index()
    idx["cdh_it"] = (idx.temp_pop_it - 18.0).clip(lower=0)
    idx["hdh_it"] = (18.0 - idx.temp_pop_it).clip(lower=0)
    idx.to_parquet(OUT / "temperature_population_italy.parquet", index=False)
    print(f"wrote {len(idx):,} hours, {idx.utc_timestamp.min()} -> {idx.utc_timestamp.max()}, "
          f"mean {idx.temp_pop_it.mean():.1f} C")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
