#!/usr/bin/env python3
"""Fetch Iberian gas storage (GIE AGSI+) and LNG terminal data (GIE ALSI), daily.

    .venv/bin/python scripts/fetch/fetch_gie_gas.py [--start 2018-01-01] [--end YYYY-MM-DD]

Writes data/gie/gie_storage_daily.parquet and data/gie/gie_lng_daily.parquet, one row per country
(ES, PT) and gas day, and keeps every answer as served (gzipped JSON) in data/gie/raw/. A
completed year already on disk is not requested again; the current year is.

Source: Gas Infrastructure Europe's transparency platforms, https://agsi.gie.eu (storage) and
https://alsi.gie.eu (LNG), API at `/api?country=..&from=..&to=..&page=..&size=300`. Free, but each
request needs a personal key (`GIE_API_KEY` in `.env`, sent as `x-key`; see `lib/config.py`).
Cite GIE as the data source.

Storage (AGSI+): gas in storage, injection, withdrawal, working gas volume, fill share. LNG
(ALSI): send-out (gas leaving the terminals into the grid, GWh/d), LNG inventory, declared total
send-out capacity. Numbers arrive as strings and are converted; the original field names are kept.
Spain's storage is small against its LNG tanks, so for Iberia the LNG side carries most of the
physical gas balance.

Exists for the gas-cap design: the one confound the control tests could not rule out
(`notes/rq-gas-cap-control.md`, "What was not done") is Iberian plants responding to physical gas
supply (LNG send-out, storage) rather than to the gas price.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from config import require_token  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent.parent
BASE = ROOT / "data" / "gie"
HOSTS = {"storage": "https://agsi.gie.eu/api", "lng": "https://alsi.gie.eu/api"}
COUNTRIES = ("ES", "PT")
PAUSE = 1.0


def get(s: requests.Session, url: str, params: dict) -> dict:
    for attempt in range(5):
        r = s.get(url, params=params, timeout=120)
        if r.status_code == 200:
            j = r.json()
            if j.get("error"):
                raise SystemExit(f"{url}: {j.get('error')}: {j.get('message')}")
            return j
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(10 * (attempt + 1))
            continue
        raise SystemExit(f"{url} {params}: HTTP {r.status_code} {r.text[:200]!r}")
    raise SystemExit(f"{url} {params}: gave up after retries")


def fetch_year(s: requests.Session, kind: str, country: str, y: int, end: date) -> list:
    p = BASE / "raw" / kind / f"{country}_{y}.json.gz"
    final = date(y, 12, 31) < date.today().replace(day=1)
    if p.exists() and final:
        with gzip.open(p, "rt") as f:
            return json.load(f)
    a, b = date(y, 1, 1), min(date(y, 12, 31), end)
    rows, page = [], 1
    while True:
        j = get(s, HOSTS[kind], {"country": country, "from": a.isoformat(), "to": b.isoformat(),
                                 "page": page, "size": 300})
        rows += j.get("data", [])
        if page >= int(j.get("last_page") or 1):
            break
        page += 1
        time.sleep(PAUSE)
    p.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(p, "wt") as f:
        json.dump(rows, f)
    time.sleep(PAUSE)
    return rows


def tidy(rows: list, country: str) -> pd.DataFrame:
    df = pd.json_normalize(rows)
    if df.empty:
        return df
    df = df[[c for c in df.columns if not isinstance(df[c].iloc[0], (list, dict))]]
    df["country"] = country
    df["gas_day"] = pd.to_datetime(df.gasDayStart).dt.date
    for c in df.columns:
        if c not in ("country", "gas_day", "gasDayStart", "name", "code", "url", "status", "info", "updatedAt"):
            df[c] = pd.to_numeric(df[c].replace({"-": None, "": None}), errors="ignore")
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2018-01-01")
    ap.add_argument("--end", default=date.today().isoformat())
    a = ap.parse_args()
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    s = requests.Session()
    s.headers.update({"x-key": require_token("GIE_API_KEY"), "User-Agent": "research (LMU Munich)"})
    for kind in HOSTS:
        parts = []
        for c in COUNTRIES:
            for y in range(start.year, end.year + 1):
                parts.append(tidy(fetch_year(s, kind, c, y, end), c))
        df = pd.concat([p for p in parts if not p.empty], ignore_index=True)
        df = df.drop_duplicates(["country", "gas_day"]).sort_values(["country", "gas_day"]).reset_index(drop=True)
        out = BASE / f"gie_{kind}_daily.parquet"
        df.to_parquet(out, index=False)
        cov = df.groupby("country").gas_day.agg(["min", "max", "size"])
        print(f"wrote {out}: {len(df):,} rows\n{cov.to_string()}\n  columns: {', '.join(df.columns)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
