#!/usr/bin/env python3
"""Population-weighted Iberian temperature — the demand-side weather index.

    .venv/bin/python scripts/fetch/fetch_population_temperature.py
    .venv/bin/python scripts/fetch/fetch_population_temperature.py --verify

Writes data/weather/temperature_population_hourly.parquet (long, one row per
city per hour) and temperature_population_index.parquet (one row per hour, with
a Spain-peninsular and an all-Iberia weighted mean). Resumable: cities already
on disk are skipped.

WHY A SECOND TEMPERATURE SERIES

`fetch_weather.py` already fetches temperature, but its ten points were chosen
to span the regions where **wind and solar capacity** sit — Tarifa, La Mancha,
Badajoz, Ciudad Real. That is the right sampling frame for an instrument for
renewable output and the wrong one for demand. Nobody runs air conditioning in
Tarifa's wind corridor; they run it in Madrid, Barcelona, Valencia and Seville.

Electricity demand responds to the temperature **where people are**, so the
index has to be population-weighted. Using the renewable-sited series as a
demand shifter attenuates the relationship toward zero by measurement error,
and does so unevenly across the year, because the renewable sites are
systematically hotter and drier than the coastal cities where most of the load
is.

SCOPE: PENINSULAR ONLY

The Canaries and the Balearics are separate electrical systems — REE's own
`apidatos` requires `geo_limit=peninsular` for the series this repo uses, and
the islands do not clear in MIBEL. Las Palmas and Palma are therefore excluded
despite both being large cities. Ceuta and Melilla likewise.

Portugal is **included and tagged**, because MIBEL clears Spain and Portugal
jointly against one merged bid stack: the demand that meets the Iberian supply
curve is Iberian. Two indices are emitted so the choice is explicit rather than
buried — `temp_pop_es` for designs whose demand series is REE's Spanish
peninsular figure, `temp_pop_iberia` for anything working on market totals.

THE WEIGHTS ARE APPROXIMATE, AND THAT IS DEFENSIBLE

Populations below are municipal figures rounded to the nearest 10k, of the
right order for the mid-2020s. They are not looked up per-year, and they should
not be treated as a demographic source. Two reasons this is adequate:

* Temperature is strongly spatially correlated at national scale, so the
  weighted and unweighted means of a fixed city set move together — `--verify`
  reports the correlation between them, and it should be very high. What the
  weights buy is the *composition* of the city set, not fine-grained shares.
* The index enters as a regressor whose scale is absorbed by standardisation
  and whose level is absorbed by fixed effects; only relative movement matters.

If a design ever turns on the weights themselves, replace this with INE
municipal series by year, and say so.

SOURCE

Open-Meteo's ERA5 archive, the same token-free source and the same reanalysis
product `fetch_weather.py` uses, requested and stored in UTC so it joins
directly onto `utc_timestamp` elsewhere. Attribution: ERA5 is produced by
Copernicus / ECMWF.
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
HOURLY = "temperature_2m"

# name, lat, lon, country, approximate municipal population
CITIES = [
    ("madrid",        40.4168, -3.7038, "ES", 3_280_000),
    ("barcelona",     41.3874,  2.1686, "ES", 1_660_000),
    ("valencia",      39.4699, -0.3763, "ES",   790_000),
    ("sevilla",       37.3891, -5.9845, "ES",   680_000),
    ("zaragoza",      41.6488, -0.8891, "ES",   680_000),
    ("malaga",        36.7213, -4.4214, "ES",   580_000),
    ("murcia",        37.9922, -1.1307, "ES",   460_000),
    ("palma_excluded", 0, 0, "SKIP", 0),   # Balearics — separate system
    ("bilbao",        43.2630, -2.9350, "ES",   350_000),
    ("alicante",      38.3452, -0.4810, "ES",   340_000),
    ("cordoba",       37.8882, -4.7794, "ES",   320_000),
    ("valladolid",    41.6523, -4.7245, "ES",   300_000),
    ("vigo",          42.2406, -8.7207, "ES",   295_000),
    ("gijon",         43.5322, -5.6611, "ES",   270_000),
    ("granada",       37.1773, -3.5986, "ES",   230_000),
    ("a_coruna",      43.3623, -8.4115, "ES",   245_000),
    ("pamplona",      42.8125, -1.6458, "ES",   205_000),
    ("santander",     43.4623, -3.8100, "ES",   170_000),
    ("lisboa",        38.7223, -9.1393, "PT",   545_000),
    ("porto",         41.1579, -8.6291, "PT",   235_000),
    ("braga",         41.5454, -8.4265, "PT",   195_000),
    ("coimbra",       40.2033, -8.4103, "PT",   105_000),
]
CITIES = [c for c in CITIES if c[3] != "SKIP"]


def raw_path(name: str) -> Path:
    return OUT / f"raw_temp_{name}.parquet"


def fetch_city(sess, name, lat, lon, country, pop) -> pd.DataFrame:
    r = sess.get(API, params={
        "latitude": lat, "longitude": lon,
        "start_date": START.isoformat(), "end_date": END.isoformat(),
        "hourly": HOURLY, "timezone": "UTC",
    }, timeout=300)
    r.raise_for_status()
    df = pd.DataFrame(r.json()["hourly"])
    df["utc_timestamp"] = pd.to_datetime(df.pop("time"), utc=True)
    df.insert(0, "city", name)
    df.insert(1, "country", country)
    df.insert(2, "population", pop)
    df.insert(3, "lat", lat)
    df.insert(4, "lon", lon)
    return df


def build_index(long: pd.DataFrame) -> pd.DataFrame:
    def wmean(sub: pd.DataFrame, label: str) -> pd.Series:
        w = sub.population
        return (sub.assign(x=sub.temperature_2m * w)
                   .groupby("utc_timestamp")
                   .apply(lambda g: g.x.sum() / g.population.sum(),
                          include_groups=False)
                   .rename(label))

    es = wmean(long[long.country == "ES"], "temp_pop_es")
    ib = wmean(long, "temp_pop_iberia")
    # unweighted, so --verify can show what the weighting actually changes
    un = (long[long.country == "ES"].groupby("utc_timestamp")
             .temperature_2m.mean().rename("temp_es_unweighted"))
    idx = pd.concat([es, ib, un], axis=1).reset_index()
    # cooling and heating degree hours, base 18 C — the standard nonlinear form,
    # since demand responds asymmetrically either side of comfort (the pooled
    # quadratic fitted on this repo's renewable-sited series turns at 17.7 C)
    idx["cdh_es"] = (idx.temp_pop_es - 18.0).clip(lower=0)
    idx["hdh_es"] = (18.0 - idx.temp_pop_es).clip(lower=0)
    return idx


def verify() -> int:
    idx = pd.read_parquet(OUT / "temperature_population_index.parquet")
    old = pd.read_parquet(OUT / "weather_spain_aggregate.parquet")
    m = idx.merge(old[["utc_timestamp", "temperature_2m_mean"]],
                  on="utc_timestamp", how="inner")
    print(f"matched {len(m):,} hours, {m.utc_timestamp.min()} to "
          f"{m.utc_timestamp.max()}\n")
    print("WHAT THE WEIGHTING CHANGES")
    print(f"  corr(pop-weighted ES, unweighted ES city mean) = "
          f"{m.temp_pop_es.corr(m.temp_es_unweighted):+.4f}")
    print(f"  corr(pop-weighted ES, renewable-sited mean)    = "
          f"{m.temp_pop_es.corr(m.temperature_2m_mean):+.4f}")
    print(f"  mean pop-weighted {m.temp_pop_es.mean():.2f} C vs "
          f"renewable-sited {m.temperature_2m_mean.mean():.2f} C "
          f"(diff {m.temp_pop_es.mean() - m.temperature_2m_mean.mean():+.2f})")
    print(f"  sd   pop-weighted {m.temp_pop_es.std():.2f}    vs "
          f"renewable-sited {m.temperature_2m_mean.std():.2f}")
    print(f"  corr(ES index, Iberia index) = "
          f"{m.temp_pop_es.corr(m.temp_pop_iberia):+.4f}")
    print("\n  A high renewable-sited correlation does NOT make the two")
    print("  interchangeable: what matters for demand is the tails, and the")
    print("  two series disagree most exactly there.")
    hot = m.nlargest(int(len(m) * 0.01), "temp_pop_es")
    print(f"  top 1% of pop-weighted hours: pop {hot.temp_pop_es.mean():.1f} C, "
          f"renewable-sited {hot.temperature_2m_mean.mean():.1f} C")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.verify:
        return verify()

    sess = session()
    for name, lat, lon, country, pop in CITIES:
        p = raw_path(name)
        if p.exists():
            print(f"  skip {name} (on disk)")
            continue
        print(f"  fetching {name} ({country}, pop {pop:,})...", flush=True)
        df = fetch_city(sess, name, lat, lon, country, pop)
        df.to_parquet(p, index=False)
        time.sleep(1.0)

    long = pd.concat([pd.read_parquet(raw_path(n)) for n, *_ in CITIES],
                     ignore_index=True)
    long.to_parquet(OUT / "temperature_population_hourly.parquet", index=False)
    idx = build_index(long)
    idx.to_parquet(OUT / "temperature_population_index.parquet", index=False)
    print(f"\n  {len(CITIES)} cities, {len(long):,} city-hours, "
          f"{len(idx):,} hours in the index")
    print(f"  wrote {OUT / 'temperature_population_index.parquet'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
