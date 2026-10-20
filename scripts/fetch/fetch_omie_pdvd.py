#!/usr/bin/env python3
"""Fetch OMIE's PDVD -- the day-ahead schedule after REE's technical constraints.

    .venv/bin/python scripts/fetch/fetch_omie_pdvd.py
    .venv/bin/python scripts/fetch/fetch_omie_pdvd.py --month 201901

Writes data/omie/pdvd/parquet/pdvd_YYYYMM.parquet, one file per month,
2019-01 -> 2025-03 by default (the minimum-income near-miss design,
docs/specs/2026-10-20-mic-near-miss-design.md §3.2); --all for every month OMIE lists.

WHY THIS EXISTS

PDVD (*Programa Diario Viable Definitivo*, the final viable daily schedule) is PDBF
after REE has resolved technical constraints: plants switched on to secure the grid
(paid as bid) and the reductions elsewhere that rebalance the system. It comes before
the first intraday session. A combined cycle withdrawn in the auction by its
minimum-income condition can still run here: on 2019-01-03 Naturgy's Sagunto 1, out
of the auction, is scheduled at 51.7 MW on average (155 MW at most).

FORMAT (checked on pdvd_20190103.1)

Header line `PDVD;`, then `year;month;day;period;unit;MW;code;`, latin-1, dot
decimal: seven fields, against PDBF's nine (no unit id, no group tag). `code` takes
the values 1 and 4, as PDBF's role code does; it is carried as `role_code`. MW is
average MW over the period, as in PDBF: derive energy as schedule_mw *
resolution_min / 60.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import (  # noqa: E402
    DATA, OMIE_LIST, monthly_parquet_may_grow, monthly_zip_may_grow, omie_url,
    resolution_minutes, session,
)

ZIPS = DATA / "omie" / "pdvd" / "zips"
OUT = DATA / "omie" / "pdvd" / "parquet"
FIRST, LAST = "201901", "202503"

SCHEMA = pa.schema([
    ("date", pa.date32()),
    ("period", pa.int16()),
    ("resolution_min", pa.int8()),
    ("unit", pa.string()),
    ("schedule_mw", pa.float64()),
    ("role_code", pa.string()),
])


def available_months(sess) -> list[str]:
    """OMIE's own listing, not an assumed range."""
    r = sess.get(OMIE_LIST, params={"parents[0]": "pdvd", "realdir": "pdvd"}, timeout=90)
    r.raise_for_status()
    return sorted(set(re.findall(r"pdvd_(\d{6})\.zip", r.text)))


def download_month(sess, ym: str) -> Path | None:
    dest = ZIPS / f"pdvd_{ym}.zip"
    have = dest.exists() and zipfile.is_zipfile(dest)
    if have and not monthly_zip_may_grow(dest, ym):
        return dest
    tmp = dest.with_suffix(".zip.part")
    with sess.get(omie_url("pdvd", f"pdvd_{ym}.zip"), timeout=900, stream=True, allow_redirects=True) as r:
        if r.status_code != 200:
            return dest if have else None
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    if not zipfile.is_zipfile(tmp):
        tmp.unlink(missing_ok=True)
        return dest if have else None
    tmp.replace(dest)
    return dest


def parse_member(raw: bytes) -> tuple[list, int]:
    """One day's rows, and the highest period seen (23/24/25 or 92/96/100)."""
    rows = []
    max_period = 0
    for rec in csv.reader(io.StringIO(raw.decode("latin-1")), delimiter=";"):
        if len(rec) < 7 or not rec[0].strip().isdigit():
            continue
        unit = rec[4].strip()
        if not unit:
            continue
        try:
            d = datetime(int(rec[0]), int(rec[1]), int(rec[2])).date()
            period = int(rec[3])
            mw = float(rec[5])
        except ValueError:
            continue
        max_period = max(max_period, period)
        rows.append((d, period, unit, mw, rec[6].strip() or None))
    return rows, max_period


def process_month(sess, ym: str, keep_zips: bool) -> int:
    dest = OUT / f"pdvd_{ym}.parquet"
    if dest.exists() and not monthly_parquet_may_grow(dest, ym):
        return -1
    z = download_month(sess, ym)
    if z is None:
        return 0
    rows: list = []
    res: dict = {}
    with zipfile.ZipFile(z) as zf:
        for name in sorted(zf.namelist()):
            digits = "".join(ch for ch in Path(name).name if ch.isdigit())[:8]
            if name.endswith("/") or len(digits) != 8:
                continue
            day_rows, max_period = parse_member(zf.read(name))
            if day_rows:
                res[day_rows[0][0]] = resolution_minutes(max_period)
                rows.extend(day_rows)
    if not rows:
        return 0
    OUT.mkdir(parents=True, exist_ok=True)
    cols = list(zip(*rows))
    tbl = pa.table({
        "date": pa.array(cols[0], pa.date32()),
        "period": pa.array(cols[1], pa.int16()),
        "resolution_min": pa.array([res[d] for d in cols[0]], pa.int8()),
        "unit": pa.array(cols[2], pa.string()),
        "schedule_mw": pa.array(cols[3], pa.float64()),
        "role_code": pa.array(cols[4], pa.string()),
    }, schema=SCHEMA)
    pq.write_table(tbl, dest, compression="zstd")
    if not keep_zips:
        z.unlink(missing_ok=True)
    return tbl.num_rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--month", help="single YYYYMM")
    ap.add_argument("--all", action="store_true", help="every month OMIE lists")
    ap.add_argument("--keep-zips", action="store_true")
    args = ap.parse_args()

    ZIPS.mkdir(parents=True, exist_ok=True)
    sess = session()
    months = [args.month] if args.month else available_months(sess)
    if not (args.month or args.all):
        months = [m for m in months if FIRST <= m <= LAST]
    for i, ym in enumerate(months, 1):
        n = process_month(sess, ym, args.keep_zips)
        what = "already on disk" if n == -1 else ("NO DATA" if n == 0 else f"{n:,} rows")
        print(f"  [{i}/{len(months)}] {ym}    {what}", flush=True)
    files = sorted(OUT.glob("pdvd_*.parquet"))
    print(f"\n{len(files)} months, {sum(pq.ParquetFile(f).metadata.num_rows for f in files):,} rows in {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
