"""Fetch REE `apidatos` generation, demand and balance for peninsular Spain.

Source
------
https://apidatos.ree.es -- REE's public widget API. **No token required**,
which is what makes it useful as an independent cross-check on the
token-gated ESIOS series.

Known limitation (measured 2026-08-07)
--------------------------------------
``time_trunc=hour`` returns HTTP 400 "The requested data is currently
unavailable" on every endpoint tried, for windows from one day to one month,
in both 2014 and 2024. ``time_trunc=day`` works reliably back to at least
2014. The ``potencia-instalada`` (installed capacity) endpoint returns
HTTP 500 regardless of window or truncation.

So this script delivers **daily** generation and demand only. Hourly
generation, hourly demand and installed capacity must come from ESIOS or
ENTSO-E -- see `fetch_esios_spain.py` and `fetch_entsoe_spain.py`.

Requests are chunked by month because long windows are unreliable.

Usage
-----
    .venv/bin/python scripts/fetch_ree_daily.py
    .venv/bin/python scripts/fetch_ree_daily.py --start 2024-01-01
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from omie_common import DATA, END, START, month_range, session  # noqa: E402

BASE = "https://apidatos.ree.es/en/datos"
OUT = DATA / "ree"

# endpoint -> output stem
ENDPOINTS = {
    "generacion/estructura-generacion": "ree_generation_daily",
    "demanda/evolucion": "ree_demand_daily",
    "balance/balance-electrico": "ree_balance_daily",
}


def month_bounds(ym: str) -> tuple[str, str]:
    y, m = int(ym[:4]), int(ym[4:])
    first = date(y, m, 1)
    last = date(y + (m == 12), (m % 12) + 1, 1) - pd.Timedelta(days=1).to_pytimedelta()
    return f"{first:%Y-%m-%d}T00:00", f"{last:%Y-%m-%d}T23:59"


def fetch_endpoint(sess, endpoint: str, ym: str) -> list[dict]:
    start, end = month_bounds(ym)
    r = sess.get(
        f"{BASE}/{endpoint}",
        params={"start_date": start, "end_date": end, "time_trunc": "day"},
        timeout=120,
    )
    if r.status_code != 200:
        return []
    payload = r.json()
    rows: list[dict] = []

    def walk(node: dict, group: str | None) -> None:
        """Series may hold values directly, or nest them under `content`.

        `estructura-generacion` and `evolucion` put values on the series
        itself; `balance-electrico` instead groups them (Renewable /
        Non-renewable / Almacenamiento / Demand) with the real series one
        level down under `attributes.content`.
        """
        name = node.get("type")
        attrs = node.get("attributes", {})
        for child in attrs.get("content", []) or []:
            walk(child, group=name)
        for v in attrs.get("values", []) or []:
            stamp = v.get("datetime")
            rows.append(
                {
                    # REE returns local Madrid time with an offset, e.g.
                    # `2024-01-01T00:00:00.000+01:00`. Taking the date from
                    # the string keeps the local calendar day; converting to
                    # UTC first would relabel 1 Jan as 31 Dec.
                    "local_date": (stamp or "")[:10],
                    "datetime": stamp,
                    "group": group,
                    "series": name,
                    "value": v.get("value"),
                    "percentage": v.get("percentage"),
                }
            )

    for series in payload.get("included", []):
        walk(series, group=None)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    sess = session()
    months = month_range(args.start, min(args.end, date.today()))
    print(f"REE apidatos: {len(months)} months, daily granularity", flush=True)

    for endpoint, stem in ENDPOINTS.items():
        rows: list[dict] = []
        empty = 0
        for i, ym in enumerate(months, 1):
            got = fetch_endpoint(sess, endpoint, ym)
            rows.extend(got)
            if not got:
                empty += 1
            if i % 24 == 0:
                print(f"  {stem}: {i}/{len(months)} months", flush=True)
            time.sleep(0.3)  # be polite to a public widget API
        if not rows:
            print(f"  {stem}: NO DATA", flush=True)
            continue
        df = pd.DataFrame(rows)
        df["utc_timestamp"] = pd.to_datetime(df["datetime"], utc=True, format="mixed")
        df["local_date"] = pd.to_datetime(df["local_date"], format="%Y-%m-%d").dt.date
        df = (
            df.drop(columns=["datetime"])
            .drop_duplicates(["local_date", "group", "series"])
            .sort_values(["local_date", "series"])
        )
        path = OUT / f"{stem}.parquet"
        df.to_parquet(path, index=False)
        print(f"  {stem}: rows={len(df):,}  series={df['series'].nunique()}  "
              f"span={df['local_date'].min()}..{df['local_date'].max()}  "
              f"empty_months={empty}", flush=True)
        print(f"    -> {path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
