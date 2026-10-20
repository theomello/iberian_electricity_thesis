#!/usr/bin/env python3
"""Fetch Ember's hourly day-ahead electricity prices for Spain, France and Portugal.

    .venv/bin/python scripts/fetch/fetch_ember_prices.py [--force]

Writes data/ember/ember_prices_hourly.parquet: country (ISO3), utc, price_eur_mwh.
The raw zip is kept in data/ember/raw/ and re-downloaded only with --force.

Source: Ember, *European wholesale electricity price data*, hourly
(https://ember-energy.org/data/european-wholesale-electricity-price-data/), compiled from
ENTSO-E's transparency platform, CC BY 4.0: cite Ember. One CSV per country inside the zip,
columns `Country, ISO3 Code, Datetime (UTC), Datetime (Local), Price (EUR/MWhe)`, from
2015-01-01, hourly also after the day-ahead's 15-minute switch (2025-10-01).

Exists for the France-link design (docs/specs/2026-10-20-france-link-design.md): France's
price, to check that the line is open exactly when the Spanish and French prices are equal.
No token is needed; ENTSO-E's own API needs one (still pending).
"""
from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "ember" / "raw" / "european_wholesale_electricity_price_data_hourly.zip"
OUT = ROOT / "data" / "ember" / "ember_prices_hourly.parquet"
URL = ("https://files.ember-energy.org/public-downloads/price/outputs/"
       "european_wholesale_electricity_price_data_hourly.zip")
COUNTRIES = {"Spain.csv": "ESP", "France.csv": "FRA", "Portugal.csv": "PRT"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="download the zip again")
    args = ap.parse_args()
    if args.force or not RAW.exists():
        RAW.parent.mkdir(parents=True, exist_ok=True)
        r = requests.get(URL, timeout=600)
        r.raise_for_status()
        RAW.write_bytes(r.content)
    parts = []
    with zipfile.ZipFile(RAW) as z:
        for name, iso in COUNTRIES.items():
            t = pd.read_csv(io.BytesIO(z.read(name)))
            if set(t["ISO3 Code"].unique()) != {iso}:
                raise SystemExit(f"{name}: expected {iso}, found {sorted(t['ISO3 Code'].unique())}")
            parts.append(pd.DataFrame({
                "country": iso,
                "utc": pd.to_datetime(t["Datetime (UTC)"]).dt.tz_localize("UTC"),
                "price_eur_mwh": t["Price (EUR/MWhe)"].astype(float),
            }))
    e = pd.concat(parts, ignore_index=True).sort_values(["country", "utc"], ignore_index=True)
    if e.duplicated(["country", "utc"]).any():
        raise SystemExit("duplicate (country, utc) rows")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    e.to_parquet(OUT, index=False)
    for iso, g in e.groupby("country"):
        print(f"  {iso}: {len(g):,} hours, {g.utc.min()} → {g.utc.max()}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
