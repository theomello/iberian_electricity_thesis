"""Fetch Portuguese generation, demand, capacity and prices from REN.

Portugal is not a neighbouring market -- it is *inside* MIBEL, clearing
jointly with Spain against one merged bid stack. REN is the Portuguese TSO
and the counterpart to REE on the Spanish side.

Source
------
``servicebus.ren.pt/datahubapi/electricity`` -- REN's DataHub API, publicly
documented at https://datahub.ren.pt/pt/instrucoes-api/. **No token.**

Datasets
--------
=================================  ==================  =================
endpoint                           content             granularity
=================================  ==================  =================
ElectricityProductionBreakdownDaily 15 series: hydro,   **15-minute**
                                    wind, solar, gas,
                                    coal, biomass,
                                    wave, batteries,
                                    pumping, imp/exp
ElectricityInstalledPowerMonthly    capacity by tech    monthly
ElectricityMarketPricesDaily        market prices       hourly
ElectricityConsumptionSupplyDaily   energy balance      daily
=================================  ==================  =================

``ElectricityInstalledPowerMonthly`` is notable: installed capacity is the
one series with **no token-free Spanish source** (REE's `potencia-instalada`
returns HTTP 500), yet Portugal publishes it openly.

Traps
-----
1. **REN publishes in Lisbon local time, one hour behind Madrid.** Portugal
   is WET/WEST while Spain is CET/CEST, despite the shared market. Aligning
   PT and ES series without accounting for this misplaces every observation
   by exactly one hour. Confirmed by solar-noon geometry (2026-08-07): under
   the Lisbon reading, PT and ES solar noon coincide at 12:22 UTC on
   2024-06-15; a Madrid reading would put Portugal 60 minutes *earlier* than
   Spain, impossible for a country lying further west.
2. **DST changes the point count**: 92 on the spring day, 100 in autumn,
   96 otherwise -- the same 4x pattern as the hourly series. The x-axis
   labels still read ``00:00``..``23:45`` regardless, so the labels alone
   cannot be trusted; the count is what carries the information.
3. Values are **MW** (instantaneous power), not MWh.

Usage
-----
    .venv/bin/python scripts/fetch_ren_portugal.py
    .venv/bin/python scripts/fetch_ren_portugal.py --start 2024-01-01
"""

from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omie_common import (  # noqa: E402
    DATA,
    END,
    LISBON,
    MADRID,
    START,
    date_range,
    day_periods_utc,
    month_range,
    session,
)

BASE = "https://servicebus.ren.pt/datahubapi/electricity"
OUT = DATA / "ren"
CACHE = OUT / "raw"


def get_json(sess, endpoint: str, params: dict, cache_key: str | None = None):
    if cache_key:
        cached = CACHE / f"{cache_key}.json"
        if cached.exists() and cached.stat().st_size > 40:
            try:
                return json.loads(cached.read_text())
            except json.JSONDecodeError:
                pass
    r = sess.get(f"{BASE}/{endpoint}", params={"culture": "en-US", **params}, timeout=90)
    if r.status_code != 200:
        return None
    try:
        payload = r.json()
    except ValueError:
        return None
    if cache_key:
        CACHE.mkdir(parents=True, exist_ok=True)
        (CACHE / f"{cache_key}.json").write_text(json.dumps(payload))
    return payload


def fetch_production_day(sess, d: date) -> list[dict]:
    """15-minute generation/demand series for one Lisbon day."""
    p = get_json(sess, "ElectricityProductionBreakdownDaily",
                 {"date": f"{d:%Y-%m-%d}"}, cache_key=f"prod_{d:%Y%m%d}")
    if not p or "series" not in p:
        return []
    series = p["series"]
    n = max((len(s.get("data") or []) for s in series), default=0)
    if n == 0:
        return []
    # Derive the grid from the observed count so DST days (92/100) are right.
    grid = day_periods_utc(d, n, LISBON)
    res = round((grid[1] - grid[0]).total_seconds() / 60) if n > 1 else 15
    rows = []
    for s in series:
        name, data = s.get("name"), s.get("data") or []
        for i, v in enumerate(data):
            if i >= len(grid) or v is None:
                continue
            rows.append(
                {
                    "local_date": d,
                    "utc_timestamp": grid[i],
                    "resolution_min": res,
                    "series": name,
                    "value_mw": float(v),
                }
            )
    return rows


def fetch_prices_day(sess, d: date) -> list[dict]:
    """Hourly MIBEL prices as republished by REN, for both ES and PT.

    **This series uses a different clock from REN's production data.** The
    production series is Lisbon local time, but market prices are on the
    MIBEL/Madrid (CET) clock -- as they must be, since the price is a market
    object shared with Spain rather than a Portuguese physical measurement.

    Mapping prices with Lisbon puts them exactly one hour late: verified
    2026-08-07 against OMIE, where REN[01:00 UTC] reproduced OMIE[00:00 UTC]
    to the cent. Under the Madrid reading the two sources agree exactly.
    """
    p = get_json(sess, "ElectricityMarketPricesDaily",
                 {"date": f"{d:%Y-%m-%d}"}, cache_key=f"price_{d:%Y%m%d}")
    if not p or "series" not in p:
        return []
    rows = []
    for s in p["series"]:
        data = s.get("data") or []
        if not data:
            continue
        grid = day_periods_utc(d, len(data), MADRID)
        for i, v in enumerate(data):
            if v is None:
                continue
            rows.append({"local_date": d, "utc_timestamp": grid[i],
                         "series": s.get("name"), "value": float(v)})
    return rows


def fetch_monthly(sess, endpoint: str, ym: str, key: str) -> list[dict]:
    p = get_json(sess, endpoint, {"year": ym[:4], "month": ym[4:]},
                 cache_key=f"{key}_{ym}")
    if not isinstance(p, list):
        return []
    out = []
    for r in p:
        val = r.get("monthly_Accumulation")
        out.append({"year": int(ym[:4]), "month": int(ym[4:]),
                    "type": r.get("type"),
                    "value": float(val) if val is not None else None})
    return out


def fetch_daily_balance(sess, d: date) -> list[dict]:
    p = get_json(sess, "ElectricityConsumptionSupplyDaily",
                 {"date": f"{d:%Y-%m-%d}"}, cache_key=f"bal_{d:%Y%m%d}")
    if not isinstance(p, list):
        return []
    return [{"local_date": d, "type": r.get("type"),
             "value": (float(r["daily_Accumulation"])
                       if r.get("daily_Accumulation") is not None else None)}
            for r in p]


def run_daily(sess, days, fn, label, workers=6):
    rows, empty = [], 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fn, sess, d): d for d in days}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                got = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {label} {futs[fut]}: {exc}", flush=True)
                got = []
            if not got:
                empty += 1
            rows.extend(got)
            if i % 250 == 0:
                print(f"  {label}: {i}/{len(days)} days, {len(rows):,} rows", flush=True)
    return rows, empty


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    sess = session()
    days = list(date_range(args.start, min(args.end, date.today())))
    months = month_range(args.start, min(args.end, date.today()))
    print(f"REN Portugal: {len(days)} days, {len(months)} months", flush=True)

    # 1. 15-minute production / consumption
    rows, empty = run_daily(sess, days, fetch_production_day, "production", args.workers)
    if rows:
        df = pd.DataFrame(rows).drop_duplicates(["utc_timestamp", "series"])
        df = df.sort_values(["utc_timestamp", "series"])
        df.to_parquet(OUT / "ren_production_15min.parquet", index=False)
        per = df.groupby("local_date")["utc_timestamp"].nunique()
        print(f"\n  production: rows={len(df):,}  series={df['series'].nunique()}  "
              f"days={per.size}  empty={empty}")
        print(f"    points/day: {per.value_counts().sort_index().to_dict()}")
        print(f"    span: {df['local_date'].min()} -> {df['local_date'].max()}")

    # 2. hourly market prices (cross-check against OMIE price_pt)
    rows, empty = run_daily(sess, days, fetch_prices_day, "prices", args.workers)
    if rows:
        df = pd.DataFrame(rows).drop_duplicates(["utc_timestamp", "series"])
        df.sort_values(["utc_timestamp", "series"]).to_parquet(
            OUT / "ren_market_prices.parquet", index=False)
        print(f"  prices: rows={len(df):,}  series={sorted(df['series'].unique())}  empty={empty}")

    # 3. daily energy balance
    rows, empty = run_daily(sess, days, fetch_daily_balance, "balance", args.workers)
    if rows:
        df = pd.DataFrame(rows).drop_duplicates(["local_date", "type"])
        df.to_parquet(OUT / "ren_consumption_supply_daily.parquet", index=False)
        print(f"  balance: rows={len(df):,}  types={df['type'].nunique()}  empty={empty}")

    # 4. monthly installed capacity -- the series Spain has no open source for
    cap = []
    for ym in months:
        cap.extend(fetch_monthly(sess, "ElectricityInstalledPowerMonthly", ym, "cap"))
    if cap:
        df = pd.DataFrame(cap).dropna(subset=["value"])
        df.to_parquet(OUT / "ren_installed_power_monthly.parquet", index=False)
        latest = df[(df["year"] == df["year"].max())]
        print(f"  capacity: rows={len(df):,}  types={sorted(df['type'].unique())}")
        print(f"    latest year {df['year'].max()}: "
              f"{latest.groupby('type')['value'].last().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
