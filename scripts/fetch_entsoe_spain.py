"""Fetch Spanish load, generation and capacity from the ENTSO-E Transparency Platform.

Serves two purposes: an independent cross-check on ESIOS (different
publication chain, same underlying system), and the cross-border flows that
matter if the Spain-France and Spain-Portugal interconnections turn out to
be part of whatever question we settle on.

Requires ``ENTSOE_TOKEN`` -- see `config.py`.

Document types fetched
----------------------
=======  ==========================================  ============
code     series                                      granularity
=======  ==========================================  ============
A65      total load (actual)                         hourly
A75      actual generation per production type       hourly
A68      installed generation capacity (aggregated)  yearly
A44      day-ahead prices                            hourly
A11      cross-border physical flows                 hourly
=======  ==========================================  ============

The API is XML and rate-limited (400 requests/minute), and rejects windows
longer than a year for most document types, so requests are chunked yearly.

NOTE: written against the documented ENTSO-E contract but NOT yet executed --
no token existed at authoring time (2026-08-07). Run ``--probe`` first.
"""

from __future__ import annotations

import argparse
import sys
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import require_token  # noqa: E402
from omie_common import DATA, END, START, session  # noqa: E402

BASE = "https://web-api.tp.entsoe.eu/api"
OUT = DATA / "entsoe"

ES = "10YES-REE------0"       # Spain bidding zone
PT = "10YPT-REN------W"       # Portugal
FR = "10YFR-RTE------C"       # France

DOCS = {
    "load":       dict(documentType="A65", processType="A16", scope="in"),
    "generation": dict(documentType="A75", processType="A16", scope="in"),
    "capacity":   dict(documentType="A68", processType="A33", scope="in"),
    "prices":     dict(documentType="A44", scope="both"),
}


def strip_ns(tag: str) -> str:
    return tag.split("}", 1)[-1] if "}" in tag else tag


def parse_timeseries(xml_text: str) -> list[dict]:
    """Flatten ENTSO-E TimeSeries/Period/Point into rows.

    Each Period carries a start instant and a resolution (ISO-8601 duration,
    e.g. ``PT60M`` or ``PT15M``); Points carry a 1-based position. The actual
    instant is start + (position-1) * resolution -- ENTSO-E does not repeat
    the timestamp per point.
    """
    root = ET.fromstring(xml_text)
    rows: list[dict] = []
    for ts in root.iter():
        if strip_ns(ts.tag) != "TimeSeries":
            continue
        meta: dict[str, str] = {}
        for child in ts:
            name = strip_ns(child.tag)
            if name == "MktPSRType":
                for sub in child.iter():
                    if strip_ns(sub.tag) == "psrType":
                        meta["psr_type"] = sub.text
            elif name in ("quantity_Measure_Unit.name", "currency_Unit.name"):
                meta[name.split(".")[0]] = child.text
        for period in ts.iter():
            if strip_ns(period.tag) != "Period":
                continue
            start_txt, res_txt = None, None
            for child in period:
                if strip_ns(child.tag) == "timeInterval":
                    for sub in child:
                        if strip_ns(sub.tag) == "start":
                            start_txt = sub.text
                elif strip_ns(child.tag) == "resolution":
                    res_txt = child.text
            if not start_txt or not res_txt:
                continue
            start = datetime.strptime(start_txt, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
            minutes = int("".join(c for c in res_txt if c.isdigit()) or 60)
            for point in period:
                if strip_ns(point.tag) != "Point":
                    continue
                pos, val = None, None
                for sub in point:
                    n = strip_ns(sub.tag)
                    if n == "position":
                        pos = int(sub.text)
                    elif n in ("quantity", "price.amount"):
                        val = float(sub.text)
                if pos is None or val is None:
                    continue
                rows.append(
                    {
                        "utc_timestamp": start + timedelta(minutes=minutes * (pos - 1)),
                        "resolution_min": minutes,
                        "value": val,
                        **meta,
                    }
                )
    return rows


def fetch_window(sess, token: str, spec: dict, start: date, end: date, zone: str) -> list[dict]:
    params = {
        "securityToken": token,
        "periodStart": f"{start:%Y%m%d}0000",
        "periodEnd": f"{end:%Y%m%d}2300",
        **{k: v for k, v in spec.items() if k != "scope"},
    }
    if spec.get("scope") == "both":
        params["in_Domain"] = params["out_Domain"] = zone
    else:
        params["outBiddingZone_Domain"] = zone
        params["in_Domain"] = zone
    r = sess.get(BASE, params=params, timeout=180)
    if r.status_code != 200:
        return []
    return parse_timeseries(r.text)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--series", nargs="*", default=list(DOCS), choices=list(DOCS))
    ap.add_argument("--zone", default=ES, help=f"default Spain ({ES})")
    ap.add_argument("--start", type=date.fromisoformat, default=START)
    ap.add_argument("--end", type=date.fromisoformat, default=END)
    args = ap.parse_args()

    token = require_token("ENTSOE_TOKEN")
    sess = session()
    OUT.mkdir(parents=True, exist_ok=True)

    if args.probe:
        rows = fetch_window(sess, token, DOCS["load"], date(2024, 1, 1), date(2024, 1, 2), args.zone)
        print(f"probe returned {len(rows)} rows")
        if rows:
            print("  sample:", rows[0])
            print("  token OK")
            return 0
        print("  no rows -- token rejected, or contract/params changed")
        return 1

    end = min(args.end, date.today())
    for name in args.series:
        spec, rows = DOCS[name], []
        for y in range(args.start.year, end.year + 1):
            ws = max(args.start, date(y, 1, 1))
            we = min(end, date(y, 12, 31))
            if ws > we:
                continue
            try:
                got = fetch_window(sess, token, spec, ws, we, args.zone)
            except Exception as exc:  # noqa: BLE001
                print(f"  {name} {y}: ERROR {exc}", flush=True)
                continue
            rows.extend(got)
            print(f"  {name} {y}: {len(got):,} rows", flush=True)
            time.sleep(1.0)  # stay well inside the 400 req/min limit
        if not rows:
            print(f"  {name}: NO DATA")
            continue
        df = pd.DataFrame(rows).drop_duplicates()
        path = OUT / f"entsoe_{name}_{args.zone.replace('-', '')}.parquet"
        df.to_parquet(path, index=False)
        print(f"  {name}: rows={len(df):,} -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
