"""Fetch 5-minute generation mix, demand and interconnection flows for Spain.

Source
------
``demanda.ree.es`` -- the undocumented feed behind REE's public "Demanda de
energía eléctrica en tiempo real" widget. **No token required.**

    .../resources/demandaGeneracionPeninsula?curva=NACIONAL&fecha=YYYY-MM-DD

This supersedes the token-gated route for hourly generation and demand. It is
also strictly better than hourly: 5-minute resolution, generation split by
technology, demand, and *bilateral* interconnection flows with France,
Portugal, Morocco and Andorra. Verified working back to 2018.

`curva` must be ``NACIONAL``; most other values are rejected outright with
``curva X no valida``. ``DEMANDAQH`` returns a quarter-hourly variant.

Response quirks
---------------
1. **JSONP, not JSON** -- the body is wrapped as ``null({...});`` and must
   have the wrapper stripped before parsing.
2. **Timestamps are local Madrid time**, and the repeated hour on the autumn
   DST day is encoded with letter suffixes: ``2A`` is the first pass (CEST)
   and ``2B`` the second (CET), giving 25 distinct hour tokens. The spring
   day simply omits ``02``, giving 23. ``strptime`` raises on ``2A``, so this
   fails loudly rather than silently -- but it must be handled.
3. Each request returns a ~30-hour window centred on the requested date, so
   consecutive dates overlap. Rows are de-duplicated on the UTC instant.

Units are MW (instantaneous power), not MWh.

Usage
-----
    .venv/bin/python scripts/fetch_ree_realtime.py
    .venv/bin/python scripts/fetch_ree_realtime.py --start 2024-01-01
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, END, MADRID, START, date_range, session  # noqa: E402

URL = (
    "https://demanda.ree.es/WSvisionaMovilesPeninsulaRest/resources/"
    "demandaGeneracionPeninsula"
)
OUT = DATA / "ree" / "ree_realtime_5min.parquet"
CACHE = DATA / "ree" / "realtime_raw"

JSONP = re.compile(r"^\s*\w*\(|\);?\s*$")

# Field glossary. Names REE uses are Spanish abbreviations; those left out of
# this map are carried through under their original name rather than guessed at.
FIELDS = {
    "dem": "demand",
    "eol": "wind",
    "nuc": "nuclear",
    "car": "coal",
    "cc": "combined_cycle",
    "hid": "hydro",
    "sol": "solar_total",
    "solFot": "solar_pv",
    "solTer": "solar_thermal",
    "bio": "biomass",
    "die": "diesel",
    "gas": "gas_turbine",
    "vap": "steam_turbine",
    "cogenResto": "cogeneration_other",
    "inter": "interconnection_balance",
    "expFra": "export_france",
    "expPor": "export_portugal",
    "expMar": "export_morocco",
    "expAnd": "export_andorra",
    "expTot": "export_total",
    "impFra": "import_france",
    "impPor": "import_portugal",
    "impMar": "import_morocco",
    "impAnd": "import_andorra",
    "impTot": "import_total",
    "bat": "battery_delivery",
    "consBat": "battery_charging",
    "turb": "pumped_turbining",
    "conb": "pumped_consumption",
}

# Three fields changed at the 2025-12-12 migration: `die`, `gas` and
# `genAux` disappear, and `aut`, `gf` and `icb` appear. Both eras carry 33
# fields. The new names are carried through unrenamed rather than guessed at
# -- confirm their meaning against REE documentation before using them, and
# expect nulls on either side of the boundary for all six.
ERA_SPLIT = date(2025, 12, 12)


def parse_local_ts(ts: str) -> datetime | None:
    """Convert a REE local timestamp to a UTC instant.

    Handles the ``2A``/``2B`` DST encoding via ``fold``: ``2A`` is the first
    pass through the repeated hour (fold=0, CEST) and ``2B`` the second
    (fold=1, CET).
    """
    try:
        day, clock = ts.split(" ")
        y, m, d = (int(x) for x in day.split("-"))
        hh, mm = clock.split(":")
        fold = 0
        if not hh.isdigit():
            marker = hh[1].upper()
            if marker not in ("A", "B"):
                return None
            fold = 1 if marker == "B" else 0
            hh = "2"
        naive = datetime(y, m, d, int(hh), int(mm), tzinfo=MADRID, fold=fold)
        return naive.astimezone(timezone.utc)
    except (ValueError, IndexError):
        return None


def fetch_day(sess, d: date) -> list[dict]:
    """Fetch one day, handling REE's 2025-12-12 endpoint migration.

    Until 2025-12-11 the endpoint requires ``curva=NACIONAL``. From
    2025-12-12 that value is rejected with ``curva NACIONAL no valida`` and
    the parameter must be **omitted** instead. Neither form works for both
    eras, so try the named curve first and fall back to the bare request.
    """
    cached = CACHE / f"{d:%Y%m%d}.json"
    if cached.exists() and cached.stat().st_size > 200:
        body = cached.read_text()
    else:
        body = None
        for params in ({"curva": "NACIONAL", "fecha": f"{d:%Y-%m-%d}"},
                       {"fecha": f"{d:%Y-%m-%d}"}):
            r = sess.get(URL, params=params, timeout=90)
            if r.status_code == 200 and "valoresHorarios" in r.text:
                body = r.text
                break
        if body is None:
            return []
        cached.write_text(body)
    try:
        payload = json.loads(JSONP.sub("", body))
    except json.JSONDecodeError:
        return []
    return payload.get("valoresHorariosGeneracion", []) or []


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    ap.add_argument("--workers", type=int, default=6)
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    days = list(date_range(args.start, min(args.end, date.today())))
    print(f"REE realtime: {len(days)} days, 5-minute resolution", flush=True)

    sess = session()
    records: list[dict] = []
    empty = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futs = {pool.submit(fetch_day, sess, d): d for d in days}
        for i, fut in enumerate(as_completed(futs), 1):
            try:
                got = fut.result()
            except Exception as exc:  # noqa: BLE001
                print(f"  ! {futs[fut]}: {exc}", flush=True)
                got = []
            if not got:
                empty += 1
            records.extend(got)
            if i % 250 == 0:
                print(f"  {i}/{len(days)} days, {len(records):,} raw records", flush=True)

    if not records:
        print("no records", flush=True)
        return 1

    df = pd.DataFrame(records)
    df["utc_timestamp"] = [parse_local_ts(t) for t in df["ts"]]
    bad = df["utc_timestamp"].isna().sum()
    df = df[df["utc_timestamp"].notna()].copy()
    df = df.rename(columns=FIELDS)
    df = df.drop_duplicates("utc_timestamp").sort_values("utc_timestamp")
    df["local_date"] = pd.to_datetime(df["ts"].str[:10], format="%Y-%m-%d").dt.date

    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)

    span_days = (df["local_date"].max() - df["local_date"].min()).days + 1
    print(f"\nwrote {OUT}  rows={len(df):,}")
    print(f"  span        : {df['local_date'].min()} -> {df['local_date'].max()} ({span_days} days)")
    print(f"  per day     : {len(df) / span_days:.1f} records (288 = full 5-min coverage)")
    print(f"  empty days  : {empty}   unparseable timestamps: {bad}")
    if "wind" in df:
        print(f"  wind        : mean {df['wind'].mean():,.0f} MW, max {df['wind'].max():,.0f} MW")
    if "demand" in df:
        print(f"  demand      : mean {df['demand'].mean():,.0f} MW, max {df['demand'].max():,.0f} MW")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
