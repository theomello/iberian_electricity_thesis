"""Fetch indicators from ESIOS (REE), above all the day-ahead forecasts.

ESIOS is the system operator's own data platform. It publishes what REE's
public `apidatos` cannot: the forecasts REE issues before the day-ahead market,
hourly generation by technology, and installed capacity.

Requires ``ESIOS_TOKEN`` -- see `config.py` for how to request one. Token checked
2026-10-02: the ``x-api-key`` header works, and 1,983 indicators are visible.

The day-ahead forecasts (``--forecasts``)
-----------------------------------------
REE publishes three forecasts **before 11:00 on D-1, an hour before day-ahead
offers close at 12:00**: demand (1775), wind (1777) and photovoltaic solar
(1779), for the peninsula, hourly, from 2019-01-01. They are what bidders knew.
There is no 2018.

Indicators 541 (wind) and 542 (solar) look like the same thing and are not:
REE republishes them **every hour** up to delivery, so the stored value is a
late update that already contains information bidders did not have. An earlier
version of this script fetched them.

Indicator IDs are checked, not trusted
--------------------------------------
ESIOS indicator IDs are poorly documented, so the forecast ids are checked
against the live catalogue by exact name and the script stops if one differs.
For anything else, search the catalogue by name::

    # 1. confirm the token works and see what exists
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --probe

    # 2. find the indicators you want (offline once the catalogue is cached)
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --search "previsión"

    # 3. fetch by id, chunked by month
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --forecasts
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --ids 1293 10391

The catalogue is cached to ``data/esios/indicator_catalogue.parquet``.

One request per month, never twice
----------------------------------
Every month is cached as REE returned it, in ``data/esios/raw/<id>/<YYYYMM>.json``,
and a complete month is never requested again: REE issues the token on condition
that the API is not asked for data already downloaded. A month is complete once
it reaches its last day (or was fetched long after it closed; see
`month_may_grow`). A refused request raises rather than leaving a silent hole.
Values are kept at the indicator's native resolution -- the three forecasts are
hourly, also after the market's 15-minute switch on 2025-10-01.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from config import require_token  # noqa: E402
from omie_common import DATA, END, START, month_last_day, month_may_grow, month_range, session  # noqa: E402

BASE = "https://api.esios.ree.es"
OUT = DATA / "esios"
RAW = OUT / "raw"
CATALOGUE = OUT / "indicator_catalogue.parquet"

# geo id for peninsular Spain in the ESIOS geo taxonomy
GEO_PENINSULAR = 8741

# REE's day-ahead forecasts, published before 11:00 on D-1. Not 541/542: those
# are republished hourly up to delivery (see the module docstring).
FORECASTS = {
    1775: "Previsión diaria D+1 demanda",
    1777: "Previsión diaria D+1 eólica",
    1779: "Previsión diaria D+1 fotovoltaica",
}
FORECAST_START = date(2019, 1, 1)

COLUMNS = ["indicator_id", "indicator_name", "value", "datetime", "utc_timestamp", "geo_id", "geo_name"]


def resolve_forecast_ids(cat: pd.DataFrame) -> list[int]:
    """The forecast ids, after checking each against the catalogue by exact name.

    Raises if an id is missing or now carries another name, so a renumbered
    catalogue cannot silently swap in a different series.
    """
    names = cat.set_index("id")["name"]
    for ind_id, name in FORECASTS.items():
        found = names.get(ind_id)
        if found != name:
            raise ValueError(f"ESIOS indicator {ind_id} is {found!r} in the catalogue, expected {name!r}")
        print(f"  {ind_id}  {name}")
    return list(FORECASTS)


def search_catalogue(cat: pd.DataFrame, text: str) -> pd.DataFrame:
    """Catalogue rows whose id, name or description contain `text`, ignoring case."""
    hay = cat.fillna("").astype(str).agg(" ".join, axis=1).str.lower()
    return cat[hay.str.contains(text.lower(), regex=False)]


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


def parse_payload(payload: dict) -> pd.DataFrame:
    """One row per value, with the UTC timestamp REE gives alongside local time."""
    ind = payload.get("indicator", {})
    df = pd.DataFrame(ind.get("values", []) or [])
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    df["indicator_id"] = ind.get("id")
    df["indicator_name"] = ind.get("name")
    df["utc_timestamp"] = pd.to_datetime(df["datetime_utc"], utc=True)
    return df[COLUMNS]


def month_is_final(payload: dict, ym: str, fetched: date) -> bool:
    """True if a cached month needs no further request: it reaches the month's
    last local day, or was fetched long enough after the month closed."""
    last = f"{month_last_day(ym):%Y-%m-%d}"
    values = payload.get("indicator", {}).get("values", []) or []
    covers = any(str(v.get("datetime", ""))[:10] == last for v in values)
    return not month_may_grow(ym, covers, fetched)


def fetch_month(sess, ind_id: int, ym: str, geo: int | None) -> dict:
    """One month of one indicator, local midnight to midnight, as REE returns it."""
    first, last = date(int(ym[:4]), int(ym[4:]), 1), month_last_day(ym)
    params = {"start_date": f"{first:%Y-%m-%d}T00:00", "end_date": f"{last:%Y-%m-%d}T23:59"}
    if geo:
        params["geo_ids[]"] = geo
    r = sess.get(f"{BASE}/indicators/{ind_id}", params=params, timeout=180)
    if r.status_code != 200:
        raise RuntimeError(f"ESIOS {ind_id} {ym}: HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def fetch_indicator(sess, ind_id: int, months: list[str], geo: int | None,
                    raw_dir: Path = RAW, today: date | None = None) -> pd.DataFrame:
    """All `months` of one indicator, requesting only those not cached complete."""
    today = today or date.today()
    folder = raw_dir / str(ind_id)
    folder.mkdir(parents=True, exist_ok=True)
    frames, requested = [], 0
    for ym in months:
        path, meta = folder / f"{ym}.json", folder / f"{ym}.fetched"
        cached = path.exists() and meta.exists()
        if cached:
            payload = json.loads(path.read_text())
        if not cached or not month_is_final(payload, ym, date.fromisoformat(meta.read_text().strip())):
            payload = fetch_month(sess, ind_id, ym, geo)
            path.write_text(json.dumps(payload, ensure_ascii=False))
            meta.write_text(today.isoformat())
            requested += 1
            time.sleep(0.25)
        frames.append(parse_payload(payload))
    print(f"  indicator {ind_id}: {requested} of {len(months)} months requested, rest cached")
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates("utc_timestamp" if geo else ["utc_timestamp", "geo_id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true", help="validate token, show catalogue size")
    ap.add_argument("--search", help="case-insensitive substring search over indicator names")
    ap.add_argument("--ids", nargs="*", type=int, help="indicator ids to download")
    ap.add_argument("--forecasts", action="store_true",
                    help="fetch REE's day-ahead demand, wind and solar forecasts "
                         "(1775/1777/1779) from 2019-01-01 to today")
    ap.add_argument("--start", type=date.fromisoformat, default=None,
                    help=f"default {START}, or {FORECAST_START} with --forecasts")
    ap.add_argument("--end", type=date.fromisoformat, default=None,
                    help=f"default {END}, or today with --forecasts")
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
        hits = search_catalogue(cat, args.search)
        print(f"\n{len(hits)} match '{args.search}':")
        for _, row in hits.head(60).iterrows():
            print(f"  {row['id']:>6}  {str(row.get('name'))[:78]}")
        return 0

    if args.forecasts:
        args.ids = (args.ids or []) + resolve_forecast_ids(cat)
    if not args.ids:
        print("\nNothing to fetch. Use --search to find indicator ids, then --ids.")
        return 0

    start = args.start or (FORECAST_START if args.forecasts else START)
    end = args.end or (date.today() if args.forecasts else END)
    months = month_range(start, min(end, date.today()))
    for ind_id in args.ids:
        df = fetch_indicator(sess, ind_id, months, args.geo)
        if df.empty:
            print(f"  indicator {ind_id}: NO DATA")
            continue
        path = OUT / f"esios_{ind_id}.parquet"
        df.to_parquet(path, index=False)
        print(f"  indicator {ind_id}: rows={len(df):,} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
