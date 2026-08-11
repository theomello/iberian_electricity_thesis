"""Fetch hourly generation, demand and capacity for Spain from ESIOS (REE).

ESIOS is the system operator's own data platform and is the primary source
for the three series that REE's public `apidatos` cannot deliver: hourly
generation by technology, hourly demand, and installed capacity.

Requires ``ESIOS_TOKEN`` -- see `config.py` for how to request one.

Indicator IDs are NOT hardcoded
------------------------------
ESIOS indicator IDs are unstable across time and poorly documented, so
guessing them produces silently wrong series. This script instead pulls the
live catalogue and resolves indicators **by name**, which is verifiable.

Workflow::

    # 1. confirm the token works and see what exists
    .venv/bin/python scripts/fetch_esios_spain.py --probe

    # 2. find the indicators you want
    .venv/bin/python scripts/fetch_esios_spain.py --search "generación"
    .venv/bin/python scripts/fetch_esios_spain.py --search demanda

    # 3. fetch by id, hourly, chunked by month
    .venv/bin/python scripts/fetch_esios_spain.py --ids 1293 10391

The catalogue is cached to ``data/esios/indicator_catalogue.parquet`` so the
search is offline after the first run.

NOTE: written against the documented ESIOS contract but NOT yet executed --
no token existed at authoring time (2026-08-07). Run ``--probe`` first; if
the auth header or response shape differs, that is the place it will show.
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from config import require_token  # noqa: E402
from omie_common import DATA, END, START, month_range, session  # noqa: E402

BASE = "https://api.esios.ree.es"
OUT = DATA / "esios"
CATALOGUE = OUT / "indicator_catalogue.parquet"

# geo id for peninsular Spain in the ESIOS geo taxonomy
GEO_PENINSULAR = 8741


def esios_session(token: str):
    s = session()
    s.headers.update(
        {
            "Accept": "application/json; application/vnd.esios-api-v2+json",
            "Content-Type": "application/json",
            "x-api-key": token,
        }
    )
    return s


def fetch_catalogue(sess, refresh: bool = False) -> pd.DataFrame:
    if CATALOGUE.exists() and not refresh:
        return pd.read_parquet(CATALOGUE)
    r = sess.get(f"{BASE}/indicators", timeout=120)
    r.raise_for_status()
    df = pd.DataFrame(r.json().get("indicators", []))
    OUT.mkdir(parents=True, exist_ok=True)
    keep = [c for c in ("id", "name", "short_name", "description") if c in df.columns]
    df = df[keep]
    df.to_parquet(CATALOGUE, index=False)
    return df


def fetch_indicator(sess, ind_id: int, ym: str, geo: int | None) -> list[dict]:
    y, m = int(ym[:4]), int(ym[4:])
    first = date(y, m, 1)
    last = date(y + (m == 12), (m % 12) + 1, 1) - pd.Timedelta(days=1).to_pytimedelta()
    params = {
        "start_date": f"{first:%Y-%m-%d}T00:00",
        "end_date": f"{last:%Y-%m-%d}T23:59",
        "time_trunc": "hour",
    }
    if geo:
        params["geo_ids[]"] = geo
    r = sess.get(f"{BASE}/indicators/{ind_id}", params=params, timeout=180)
    if r.status_code != 200:
        return []
    payload = r.json().get("indicator", {})
    rows = payload.get("values", []) or []
    for row in rows:
        row["indicator_id"] = ind_id
        row["indicator_name"] = payload.get("name")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", action="store_true", help="validate token, show catalogue size")
    ap.add_argument("--search", help="case-insensitive substring search over indicator names")
    ap.add_argument("--ids", nargs="*", type=int, help="indicator ids to download")
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    ap.add_argument("--geo", type=int, default=GEO_PENINSULAR)
    ap.add_argument("--refresh-catalogue", action="store_true")
    args = ap.parse_args()

    token = require_token("ESIOS_TOKEN")
    sess = esios_session(token)
    OUT.mkdir(parents=True, exist_ok=True)

    if args.probe:
        r = sess.get(f"{BASE}/indicators", timeout=120)
        print(f"HTTP {r.status_code}")
        if r.status_code != 200:
            print("token rejected or contract changed; body:", r.text[:400])
            return 1
        inds = r.json().get("indicators", [])
        print(f"token OK -- {len(inds)} indicators visible")
        for i in inds[:8]:
            print(f"  {i.get('id'):>6}  {i.get('name', '')[:70]}")
        return 0

    cat = fetch_catalogue(sess, refresh=args.refresh_catalogue)
    print(f"catalogue: {len(cat)} indicators -> {CATALOGUE}")

    if args.search:
        hay = cat.astype(str).agg(" ".join, axis=1).str.lower()
        hits = cat[hay.str.contains(args.search.lower(), na=False)]
        print(f"\n{len(hits)} match '{args.search}':")
        for _, row in hits.head(60).iterrows():
            print(f"  {row['id']:>6}  {str(row.get('name'))[:78]}")
        return 0

    if not args.ids:
        print("\nNothing to fetch. Use --search to find indicator ids, then --ids.")
        return 0

    months = month_range(args.start, min(args.end, date.today()))
    for ind_id in args.ids:
        rows: list[dict] = []
        for i, ym in enumerate(months, 1):
            rows.extend(fetch_indicator(sess, ind_id, ym, args.geo))
            if i % 12 == 0:
                print(f"  indicator {ind_id}: {i}/{len(months)} months", flush=True)
            time.sleep(0.25)
        if not rows:
            print(f"  indicator {ind_id}: NO DATA")
            continue
        df = pd.DataFrame(rows)
        if "datetime" in df.columns:
            df["utc_timestamp"] = pd.to_datetime(df["datetime"], utc=True, format="mixed")
        path = OUT / f"esios_{ind_id}.parquet"
        df.to_parquet(path, index=False)
        print(f"  indicator {ind_id}: rows={len(df):,} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
