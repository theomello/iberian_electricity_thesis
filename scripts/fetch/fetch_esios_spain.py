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

Installed capacity (``--capacity``)
-----------------------------------
Nineteen indicators -- 17 technologies (1475-1491), the total (10300) and
self-consumption (10413) -- monthly, per autonomous community, from 2015-01.
They need ``time_trunc=month``: without it the API answers HTTP 500 ("No value
specified for parameter 2"). They are requested a year at a time with no region
filter, and written together to ``esios_installed_capacity.parquet``. Peninsular
capacity is the sum over every region except the four separate electrical
systems in `NON_PENINSULAR`: the Balearic and Canary Islands, Ceuta, Melilla.
Pure pumped storage (1476, 3,331 MW) is in neither hydro (1475) nor the total
(10300): REE counts it as storage. The other 16 technologies sum to the total
to the megawatt; add 1476 and the sum exceeds it by 3,331 MW.

Measured output by province (``--provinces``)
---------------------------------------------
Wind (1159) and photovoltaic (1161) generation as metered, hourly, in MWh, for every
province with such plant, from 2018-01. Requested a month at a time with **no region
filter**: the answer then carries one series per province (40 provinces for wind on
2017-12-31). Published from M+1, so the last month or two are partial and re-requested
on a later run. A month is about 5 MB of JSON, so these chunks are cached gzipped
(``<YYYYMM>.json.gz``). Written together to ``esios_measured_generation_province.parquet``.
It is output, not weather: it includes what farms shed at low prices.

Indicator IDs are checked, not trusted
--------------------------------------
ESIOS indicator IDs are poorly documented, so the preset ids are checked
against the live catalogue by exact name and the script stops if one differs.
For anything else, search the catalogue by name::

    # 1. confirm the token works and see what exists
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --probe

    # 2. find the indicators you want (offline once the catalogue is cached)
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --search "previsión"

    # 3. fetch by id, chunked by month
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --forecasts --capacity --provinces
    .venv/bin/python scripts/fetch/fetch_esios_spain.py --ids 1293 10391

The catalogue is cached to ``data/esios/indicator_catalogue.parquet``.

One request per chunk, never twice
----------------------------------
Every chunk -- a month of native values, or a year of monthly aggregates -- is
cached as REE returned it, in ``data/esios/raw/<id>/<YYYYMM>.json`` or
``data/esios/raw/<id>/month/<YYYY>.json``, and a complete chunk is never
requested again: REE issues the token on condition that the API is not asked for
data already downloaded. A chunk is complete once it reaches its last unit (the
last day, or the last month when aggregated), or was fetched long after it
closed (see `chunk_is_final`); one still growing is asked for again on a later day,
never twice on the same day. A refused request raises rather than leaving a silent hole,
except REE's occasional HTTP 404 ``NoSuchKey`` on a large answer, which is retried.
Values are kept at the indicator's native resolution -- the three forecasts are
hourly, also after the market's 15-minute switch on 2025-10-01.
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from config import require_token  # noqa: E402
from omie_common import DATA, END, FINAL_AFTER_DAYS, START, month_last_day, month_range, session  # noqa: E402

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

# Installed capacity by technology, monthly, per autonomous community.
CAPACITY = {
    1475: "Potencia instalada de generación hidráulica",
    1476: "Potencia instalada de turbinación de bombeo",
    1477: "Potencia instalada de generación nuclear",
    1478: "Potencia instalada de generación carbón",
    1479: "Potencia instalada de generación motores diesel",
    1480: "Potencia instalada de generación turbina de gas",
    1481: "Potencia instalada de generación turbina de vapor",
    1482: "Potencia instalada de generación fuel",
    1483: "Potencia instalada de generación ciclo combinado",
    1484: "Potencia instalada de generación hidroeólica",
    1485: "Potencia instalada de generación eólica",
    1486: "Potencia instalada de generación solar fotovoltaica",
    1487: "Potencia instalada de generación solar térmica",
    1488: "Potencia instalada de generación otras renovables",
    1489: "Potencia instalada de generación cogeneración",
    1490: "Potencia instalada de generación residuos no renovables",
    1491: "Potencia instalada de generación residuos renovables",
    10300: "Potencia instalada de generación total",
    10413: "Potencia instalada de generación autoconsumo total",
}
CAPACITY_START = date(2015, 1, 1)
CAPACITY_OUT = OUT / "esios_installed_capacity.parquet"
# ESIOS geo ids of the regions outside the peninsular system, which MIBEL does not clear
NON_PENINSULAR = {12: "Ceuta", 18: "Islas Baleares", 19: "Islas Canarias", 8746: "Melilla"}

# Measured generation by province, hourly, from 2018-01.
PROVINCES = {
    1159: "Generación medida Eólica terrestre",
    1161: "Generación medida Solar fotovoltaica",
}
PROVINCES_OUT = OUT / "esios_measured_generation_province.parquet"

COLUMNS = ["indicator_id", "indicator_name", "value", "datetime", "utc_timestamp", "geo_id", "geo_name"]


def resolve_ids(cat: pd.DataFrame, wanted: dict[int, str]) -> list[int]:
    """The `wanted` ids, after checking each against the catalogue by exact name.

    Raises if an id is missing or now carries another name, so a renumbered
    catalogue cannot silently swap in a different series.
    """
    names = cat.set_index("id")["name"]
    for ind_id, name in wanted.items():
        found = names.get(ind_id)
        if found != name:
            raise ValueError(f"ESIOS indicator {ind_id} is {found!r} in the catalogue, expected {name!r}")
        print(f"  {ind_id}  {name}")
    return list(wanted)


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


def month_chunks(start: date, end: date) -> list[tuple[str, date, date]]:
    """Whole calendar months touching [start, end], as (key, first, last)."""
    return [(ym, date(int(ym[:4]), int(ym[4:]), 1), month_last_day(ym)) for ym in month_range(start, end)]


def year_chunks(start: date, end: date) -> list[tuple[str, date, date]]:
    """Whole calendar years touching [start, end], the current one included."""
    return [(str(y), date(y, 1, 1), date(y, 12, 31)) for y in range(start.year, end.year + 1)]


def chunk_is_final(payload: dict, last: date, fetched: date, trunc: str | None = None) -> bool:
    """True if a cached chunk needs no further request: it holds a value for the
    chunk's last unit (its last day, or the first of its last month when
    aggregated monthly), or was fetched long enough after the chunk closed."""
    unit = date(last.year, last.month, 1) if trunc == "month" else last
    values = payload.get("indicator", {}).get("values", []) or []
    if any(str(v.get("datetime", ""))[:10] == f"{unit:%Y-%m-%d}" for v in values):
        return True
    return (fetched - last).days >= FINAL_AFTER_DAYS


def fetch_chunk(sess, ind_id: int, first: date, last: date, geo: int | None, trunc: str | None) -> dict:
    """One chunk of one indicator, local midnight to midnight, as REE returns it."""
    params = {"start_date": f"{first:%Y-%m-%d}T00:00", "end_date": f"{last:%Y-%m-%d}T23:59"}
    if trunc:
        params["time_trunc"] = trunc
    if geo:
        params["geo_ids[]"] = geo
    for attempt in range(4):
        r = sess.get(f"{BASE}/indicators/{ind_id}", params=params, timeout=180)
        # A large answer is staged in a temporary file on REE's storage; now and then it
        # is gone before it is served (HTTP 404 NoSuchKey, 1161 for 2018-02 on 2026-10-05).
        if not (r.status_code == 404 and "NoSuchKey" in r.text):
            break
        time.sleep(15 * (attempt + 1))
    if r.status_code != 200:
        raise RuntimeError(f"ESIOS {ind_id} {first}..{last}: HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


def fetch_indicator(sess, ind_id: int, chunks: list[tuple[str, date, date]], geo: int | None,
                    trunc: str | None = None, raw_dir: Path = RAW, today: date | None = None,
                    gz: bool = False) -> pd.DataFrame:
    """All `chunks` of one indicator, requesting only those not cached complete.
    With `gz`, new chunks are cached gzipped; either form is read back."""
    today = today or date.today()
    folder = raw_dir / str(ind_id) / (trunc or "")
    folder.mkdir(parents=True, exist_ok=True)
    frames, requested = [], 0
    for key, first, last in chunks:
        meta = folder / f"{key}.fetched"
        plain, packed = folder / f"{key}.json", folder / f"{key}.json.gz"
        path = packed if packed.exists() else plain
        cached = path.exists() and meta.exists()
        if cached:
            payload = json.loads(gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_text())
            fetched = date.fromisoformat(meta.read_text().strip())
        # a chunk still growing is asked for again, but not on the day it was fetched
        if not cached or (fetched < today and not chunk_is_final(payload, last, fetched, trunc)):
            payload = fetch_chunk(sess, ind_id, first, last, geo, trunc)
            text = json.dumps(payload, ensure_ascii=False)
            if gz:
                packed.write_bytes(gzip.compress(text.encode("utf-8")))
                plain.unlink(missing_ok=True)
            else:
                plain.write_text(text)
            meta.write_text(today.isoformat())
            requested += 1
            time.sleep(0.25)
            if requested % 12 == 0:
                print(f"  indicator {ind_id}: {requested} chunks requested, at {key}", flush=True)
        frames.append(parse_payload(payload))
    print(f"  indicator {ind_id}: {requested} of {len(chunks)} chunks requested, rest cached")
    # an empty chunk (a month not yet published) would turn the timestamps into objects
    frames = [f for f in frames if not f.empty] or frames[:1]
    df = pd.concat(frames, ignore_index=True)
    return df.drop_duplicates(["utc_timestamp", "geo_id"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true", help="validate token, show catalogue size")
    ap.add_argument("--search", help="case-insensitive substring search over indicator names")
    ap.add_argument("--ids", nargs="*", type=int, help="indicator ids to download")
    ap.add_argument("--forecasts", action="store_true",
                    help="fetch REE's day-ahead demand, wind and solar forecasts "
                         "(1775/1777/1779) from 2019-01-01 to today")
    ap.add_argument("--capacity", action="store_true",
                    help="fetch installed capacity by technology, monthly per region, from 2015-01")
    ap.add_argument("--provinces", action="store_true",
                    help="fetch measured wind and PV generation, hourly per province, from 2018-01")
    ap.add_argument("--start", type=date.fromisoformat, default=None,
                    help=f"default {START} (also with --provinces); {FORECAST_START} with --forecasts, "
                         f"{CAPACITY_START} with --capacity")
    ap.add_argument("--end", type=date.fromisoformat, default=None,
                    help=f"default {END}, or today with --forecasts, --capacity and --provinces")
    ap.add_argument("--geo", type=int, default=GEO_PENINSULAR, help="region filter for --ids; 0 for none")
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

    today = date.today()
    jobs = []  # (ids, chunks, trunc, geo, combined output or None, gzip the raw cache)
    if args.forecasts:
        jobs.append((resolve_ids(cat, FORECASTS),
                     month_chunks(args.start or FORECAST_START, args.end or today), None, GEO_PENINSULAR, None, False))
    if args.capacity:
        jobs.append((resolve_ids(cat, CAPACITY),
                     year_chunks(args.start or CAPACITY_START, args.end or today), "month", None, CAPACITY_OUT, False))
    if args.provinces:
        jobs.append((resolve_ids(cat, PROVINCES),
                     month_chunks(args.start or START, args.end or today), None, None, PROVINCES_OUT, True))
    if args.ids:
        jobs.append((args.ids, month_chunks(args.start or START, min(args.end or END, today)),
                     None, args.geo or None, None, False))
    if not jobs:
        print("\nNothing to fetch. Use --search to find indicator ids, then --ids.")
        return 0

    for ids, chunks, trunc, geo, combined, gz in jobs:
        frames = []
        for ind_id in ids:
            df = fetch_indicator(sess, ind_id, chunks, geo, trunc, gz=gz)
            if df.empty:
                print(f"  indicator {ind_id}: NO DATA")
                continue
            if combined:
                frames.append(df)
                continue
            path = OUT / f"esios_{ind_id}.parquet"
            df.to_parquet(path, index=False)
            print(f"  indicator {ind_id}: rows={len(df):,} -> {path}")
        if combined and frames:
            out = pd.concat(frames, ignore_index=True)
            out.to_parquet(combined, index=False)
            print(f"  {len(frames)} indicators: rows={len(out):,} -> {combined}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
