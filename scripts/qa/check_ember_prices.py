#!/usr/bin/env python3
"""Ember's hourly day-ahead prices for Spain, France and Portugal.

    .venv/bin/python scripts/qa/check_ember_prices.py

Checks `data/ember/ember_prices_hourly.parquet` (`fetch/fetch_ember_prices.py`):
  - Spain's price equals OMIE's `price_es` at the same UTC hour within €0.01 on ≥ 99% of
    hours 2018-01-01 → 2025-09-30 (the clock join, and that Ember is the published price);
  - France has a price in ≥ 99.9% of those hours;
  - (country, utc) is a key.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
FILE = ROOT / "data" / "ember" / "ember_prices_hourly.parquet"


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    if not FILE.exists():
        print(f"  FAIL {FILE.relative_to(ROOT)} missing\nFAIL: 1")
        return 1
    e = pd.read_parquet(FILE)
    check(not e.duplicated(["country", "utc"]).any(), "(country, utc) is a key")
    px = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "utc_timestamp", "price_es", "resolution_min"])
    px = px[(px.resolution_min == 60) & (pd.to_datetime(px.date) >= "2018-01-01") & (pd.to_datetime(px.date) <= "2025-09-30")]
    px["utc"] = pd.to_datetime(px.utc_timestamp, utc=True)
    es = px.merge(e[e.country == "ESP"][["utc", "price_eur_mwh"]], on="utc", how="left")
    same = ((es.price_es - es.price_eur_mwh).abs() <= 0.01).mean()
    check(same >= 0.99, f"ESP = OMIE price_es within €0.01 on {same:.2%} of {len(es):,} hours")
    fr = px[["utc"]].merge(e[e.country == "FRA"][["utc", "price_eur_mwh"]], on="utc", how="left")
    have = fr.price_eur_mwh.notna().mean()
    check(have >= 0.999, f"FRA priced on {have:.3%} of those hours")
    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
