#!/usr/bin/env python3
"""Fetch ERA5 daily precipitation and snowfall at Spanish river-basin points.

    .venv/bin/python scripts/fetch/fetch_hydro_precipitation.py

Writes data/weather/precipitation_basins_daily.parquet, one row per basin
point per day. Resumable: points already on disk are skipped.

WHY

`notes/rq-gas-cap-conduct.md` and `notes/candidate-natural-experiments.md`
record four failed attempts to identify the 2021 windfall-levy effect on
hydro bidding, all blocked by the same thing: hydro's opportunity cost
("water value") is unobservable, and every proxy built from the bid data
itself turned out contaminated, censored, or unstable across sample choice.

This is a different kind of proxy: **exogenous rainfall**, not a function of
bidding at all. A wet spell raises expected future inflow into a reservoir,
which lowers the opportunity cost of releasing water today, which should
lower a storage plant's offer price -- a mechanism that runs through physics,
not through the auction. If basin-level precipitation moves a hydro unit's
own offers while a placebo basin's rain does not, that is evidence the
channel is real and could supply the missing water-value proxy.

This is explicitly the cheap, reduced-form probe for the question that
`notes/hydro-water-value-design.md` argues needs a full structural model
(reservoir volume, forward price, snowpack, jointly estimated). It fetches
one input of that structural design (rainfall/snow) and asks the much
smaller question first: does the channel show up at all in a simple
unit + month fixed-effects regression, before three more data series and a
joint estimation are committed to.

BASIN POINTS

44 Spanish `hydro_ugh` (managed-storage) units exist in
`unit_agents.parquet`; roughly half name their river basin directly in
`descr` ("UGH. GUADALQUIVIR", "HYDRO CUENCA DUERO", ...). Points below are
one representative coordinate per basin that appears, chosen inside the
basin's territory, not a hydrological centroid -- there is no basin-boundary
shapefile in this repo, so this is a coarse proxy, matching the existing
`fetch_weather.py` choice of representative points over a proper
capacity-weighted index.

SOURCE

Same as fetch_weather.py: Open-Meteo's ERA5 archive, free, no API key,
daily aggregates back to 1940. <https://open-meteo.com/en/docs/historical-weather-api>
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, END, START, session  # noqa: E402

OUT = DATA / "weather"
API = "https://archive-api.open-meteo.com/v1/archive"
DAILY = "precipitation_sum,snowfall_sum"

# basin, lat, lon -- one point inside each basin that a hydro_ugh unit names
BASINS = [
    ("duero",         41.60, -4.70),
    ("ebro",           41.90, -1.00),
    ("tajo",           39.90, -3.70),
    ("guadiana",       38.90, -6.90),
    ("guadalquivir",   37.90, -4.80),
    ("jucar",          39.50, -1.30),
    ("galicia_sil_mino", 42.50, -7.60),
    ("cantabrico",     43.20, -3.80),
    ("segura",         38.10, -1.30),
    # Added 2026-10-02 for the own-basin rainfall design (notes/rq-hydro-rain-first-stage.md):
    # the five firms' cascades the points above miss or represent badly. One point each,
    # near the reservoirs, not a basin average.
    ("pirineo",        42.40,  0.85),   # Endesa's Ebro-Fecsa-Enher (Noguera Pallaresa/Ribagorzana)
    ("catalunya_ter",  41.98,  2.40),   # Endesa's Ter (Sau, Susqueda)
    ("galicia_costa",  42.95, -8.55),   # Naturgy's UF-Galicia Costa (Tambre, Ulla)
    ("pt_lima_cavado", 41.80, -8.05),   # EDP's Lima and Cavado (Alto Lindoso, Alto Rabagao)
    ("pt_douro",       41.20, -7.20),   # EDP's and Movhera's Douro dams
    ("pt_tamega",      41.55, -7.80),   # Iberdrola's Tamega scheme (Gouvaes, Daivoes)
    ("pt_mondego",     40.40, -7.90),   # EDP's Mondego (Aguieira)
    ("pt_tejo_zezere", 39.90, -8.10),   # EDP's Tejo-Mondego system (Castelo do Bode, Cabril)
    ("pt_guadiana",    38.30, -7.40),   # EDP's Alqueva
]


def fetch_basin(sess, name: str, lat: float, lon: float) -> pd.DataFrame:
    r = sess.get(API, params={
        "latitude": lat, "longitude": lon,
        "start_date": START.isoformat(), "end_date": END.isoformat(),
        "daily": DAILY, "timezone": "UTC", "precipitation_unit": "mm",
    }, timeout=300)
    r.raise_for_status()
    d = r.json()["daily"]
    df = pd.DataFrame(d)
    df["date"] = pd.to_datetime(df.pop("time"))
    df.insert(0, "basin", name)
    df.insert(1, "lat", lat)
    df.insert(2, "lon", lon)
    return df


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    sess = session()
    frames = []
    for name, lat, lon in BASINS:
        cache = OUT / f"raw_precip_{name}.parquet"
        if cache.exists():
            frames.append(pd.read_parquet(cache))
            print(f"  {name:20s} cached")
            continue
        df = fetch_basin(sess, name, lat, lon)
        df.to_parquet(cache, index=False)
        frames.append(df)
        print(f"  {name:20s} {len(df):>7,} days")
        time.sleep(1.0)

    long = pd.concat(frames, ignore_index=True)
    out = OUT / "precipitation_basins_daily.parquet"
    long.to_parquet(out, index=False)
    print(f"\nwrote {out}  {len(long):,} rows, {long.basin.nunique()} basins, "
          f"{long.date.min().date()} -> {long.date.max().date()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
