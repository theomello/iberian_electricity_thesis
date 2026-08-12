#!/usr/bin/env python3
"""Fetch ERA5 reanalysis weather for Spain, for use as an instrument.

    .venv/bin/python scripts/fetch/fetch_weather.py
    .venv/bin/python scripts/fetch/fetch_weather.py --verify

Writes data/weather/weather_spain_hourly.parquet (long format, one row per
point per hour) plus weather_spain_aggregate.parquet (one row per hour).
Resumable: points already on disk are skipped.

WHY

The finding that residual demand elasticity falls as the renewable share rises
is a correlation. Renewable output is not randomly assigned, so it may be
picking up whatever else makes an hour unusual. The standard fix in this
literature is to instrument renewable output with weather: Novan (2015)
instruments wind generation with wind speed and installed capacity; Fabra,
Rapson, Reguant and Wang (2021) instrument the Spanish price with expected
national wind production.

The identifying assumption is that **weather moves the market only through
renewable output**. Wind speed is plausible on that score. Temperature is not
-- it drives heating and cooling demand directly -- so temperature is fetched
as a *control*, never as an instrument. Solar radiation sits in between: it
shifts PV output but also correlates with cooling demand.

SOURCE

Open-Meteo's ERA5 archive: free, no API key, hourly, from 1940.
<https://open-meteo.com/en/docs/historical-weather-api>. ERA5 is a reanalysis,
not station data -- it is a physically consistent model reconstruction, which
is what makes it dense and gap-free. Attribution: ERA5 is produced by
Copernicus / ECMWF.

POINTS

Ten locations chosen to span the regions where Spanish wind and solar capacity
actually sit, rather than a single national centroid. Each is tagged `wind` or
`solar` so the aggregate can be built from the relevant subset. These are
representative sites, **not** capacity-weighted: a capacity-weighted index
would be better and needs an installed-capacity-by-province source, which this
project does not yet have (see the installed-capacity gap in CLAUDE.md).

TIMEZONE

Requested in UTC and stored in UTC, to join directly onto `utc_timestamp`
elsewhere. Do not convert to local time before joining.
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
HOURLY = "wind_speed_100m,wind_speed_10m,temperature_2m,shortwave_radiation"

# name, lat, lon, role
POINTS = [
    ("galicia",       43.00, -8.00, "wind"),
    ("castilla_leon", 42.30, -3.70, "wind"),
    ("navarra",       42.70, -1.60, "wind"),
    ("aragon",        41.60, -1.00, "wind"),
    ("la_mancha",     39.00, -1.90, "wind"),
    ("tarifa",        36.10, -5.60, "wind"),
    ("sevilla",       37.40, -6.00, "solar"),
    ("badajoz",       38.90, -6.90, "solar"),
    ("murcia",        38.00, -1.10, "solar"),
    ("ciudad_real",   38.90, -3.90, "solar"),
]


def fetch_point(sess, name: str, lat: float, lon: float, role: str) -> pd.DataFrame:
    r = sess.get(API, params={
        "latitude": lat, "longitude": lon,
        "start_date": START.isoformat(), "end_date": END.isoformat(),
        "hourly": HOURLY, "timezone": "UTC", "wind_speed_unit": "ms",
    }, timeout=300)
    r.raise_for_status()
    h = r.json()["hourly"]
    df = pd.DataFrame(h)
    df["utc_timestamp"] = pd.to_datetime(df.pop("time"), utc=True)
    df.insert(0, "point", name)
    df.insert(1, "role", role)
    df.insert(2, "lat", lat)
    df.insert(3, "lon", lon)
    return df


def build_aggregate(long: pd.DataFrame) -> pd.DataFrame:
    wind = (long[long.role == "wind"].groupby("utc_timestamp")
            .wind_speed_100m.mean().rename("wind_speed_100m_wind_sites"))
    solar = (long[long.role == "solar"].groupby("utc_timestamp")
             .shortwave_radiation.mean().rename("radiation_solar_sites"))
    temp = long.groupby("utc_timestamp").temperature_2m.mean().rename("temperature_2m_mean")
    agg = pd.concat([wind, solar, temp], axis=1).reset_index()
    # Wind power in a turbine goes as the cube of speed below rated output, so
    # the cube is the more natural instrument for generation than speed itself.
    agg["wind_speed_cubed"] = agg.wind_speed_100m_wind_sites ** 3
    return agg


def verify() -> int:
    """First-stage check: does the instrument actually move renewable output?"""
    import pyarrow.parquet as pq
    agg = pd.read_parquet(OUT / "weather_spain_aggregate.parquet")
    rt = pq.read_table(DATA / "ree" / "ree_realtime_5min.parquet",
                       columns=["utc_timestamp", "wind", "solar_total", "demand"]).to_pandas()
    rt["hour"] = rt.utc_timestamp.dt.floor("h")
    g = rt.groupby("hour").agg(wind=("wind", "mean"), solar=("solar_total", "mean"),
                               demand=("demand", "mean")).reset_index()
    m = g.merge(agg, left_on="hour", right_on="utc_timestamp", how="inner")
    print(f"matched {len(m):,} hours\n")
    # Rank correlation without scipy: Pearson on ranks is Spearman by definition.
    def spearman(x: pd.Series, y: pd.Series) -> float:
        return x.rank().corr(y.rank())

    print("FIRST STAGE -- does weather move renewable output? (Spearman)")
    for a, b in (("wind_speed_100m_wind_sites", "wind"), ("wind_speed_cubed", "wind"),
                 ("radiation_solar_sites", "solar"), ("temperature_2m_mean", "demand")):
        print(f"  corr({a:28s}, {b:7s}) = {spearman(m[a], m[b]):+.3f}")
    print("\n  The last line is the reason temperature is a control, not an")
    print("  instrument: it moves demand directly, so it violates exclusion.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.verify:
        return verify()

    sess = session()
    frames = []
    for name, lat, lon, role in POINTS:
        cache = OUT / f"raw_{name}.parquet"
        if cache.exists():
            frames.append(pd.read_parquet(cache))
            print(f"  {name:14s} cached")
            continue
        df = fetch_point(sess, name, lat, lon, role)
        df.to_parquet(cache, index=False)
        frames.append(df)
        print(f"  {name:14s} {len(df):>7,} hours")
        time.sleep(1.0)          # be polite to a free service

    long = pd.concat(frames, ignore_index=True)
    long.to_parquet(OUT / "weather_spain_hourly.parquet", index=False)
    agg = build_aggregate(long)
    agg.to_parquet(OUT / "weather_spain_aggregate.parquet", index=False)
    print(f"\nwrote weather_spain_hourly.parquet    {len(long):,} rows")
    print(f"      weather_spain_aggregate.parquet  {len(agg):,} hours "
          f"({agg.utc_timestamp.min().date()} -> {agg.utc_timestamp.max().date()})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
