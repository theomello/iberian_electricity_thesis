#!/usr/bin/env python3
"""Fetch OMIE's PDBF -- the daily operating schedule -- per unit and period.

    .venv/bin/python scripts/fetch/fetch_omie_pdbf.py
    .venv/bin/python scripts/fetch/fetch_omie_pdbf.py --month 202401
    .venv/bin/python scripts/fetch/fetch_omie_pdbf.py --verify

Writes data/omie/pdbf/parquet/pdbf_YYYYMM.parquet, one file per month.

WHY THIS EXISTS: the contract position

PDBF (*Programa Diario Base de Funcionamiento*, daily base operating schedule)
is the day-ahead auction result **plus** bilateral physical contracts and
self-scheduling. PDBC (*Programa Diario Base de Casacion*, the auction result
alone) is what the bid files publish as `status == 'C'`.

The difference is the **contract position**: energy a unit is committed to
deliver at a price fixed outside the auction. That is the `theta` term in Wolak
(2000) and Hortacsu & Puller (2008), and it governs the incentive to raise the
auction price -- volume already sold forward earns nothing extra when the
day-ahead price rises, so a heavily contracted firm has a weaker incentive to
withhold, whatever its market share.

This matters because it is normally unobservable. Jha & Leslie devote an
appendix to inferring Snowy Hydro's contract position precisely because
Australian contracts are not public.

**Do not compute it as PDBF minus PDBC. It is labelled directly.**
`role_code == "4"` *is* the physical bilateral contract, and reading it off
beats the subtraction on every count:

- Its sell and buy legs are **exactly equal** -- 0.0000 gap in every month
  tested from 2018 to 2026 -- which is the matching identity a bilateral
  contract must satisfy and the subtraction cannot check.
- It is per unit per period, so it needs no join to the bid files.
- The subtraction is wrong in practice anyway: PDBF carries **several rows per
  unit-period**, one per role, so joining it to cleared volume on
  (date, period, unit) fans the auction volume out across those rows. That
  inflated an early cut of this series to a spurious 36% -> 5% collapse; the
  measured series is 46.5% -> 38.9%.

Measured share of scheduled sales under bilateral contract: 46.5% (2018),
48.5% (2022 peak), 38.9% (2024 and 2026).

**Still a proxy for theta, not theta.** It captures *physical* bilateral
contracts only, and misses **financial** hedges entirely -- an OMIP future or a
financially settled PPA fixes revenue while the energy still clears in the
auction. Since what matters is whether *revenue* is fixed rather than whether
electrons flow bilaterally, that omission is the more serious one. Bound it; do
not claim to measure it.

It also corrects a live error in this repo's own framing: CNMC publishes market
shares on PDBF, not on the auction, and on January 2024 PDBF sell volume is
1.73x day-ahead cleared volume. Comparing our day-ahead shares to CNMC's makes
firms look under-mapped when they are not.

FORMAT

Semicolon-delimited, latin-1, one header line `PDBF;`. Identical field layout
to `pdbce`, which build/build_unit_registry.py already parses:

    [0] year   [1] month   [2] day   [3] period
    [4] unit       unit code, joins to the bid curves and to unit_agents
    [5] schedule   average **MW**, **signed**: positive sells, negative buys
    [6] group_tag  populated only on role 4, where it is the contract id
    [7] role_code  transaction type -- see below
    [8] unit_id    OMIE registration id; on role-4 rows it is the contract id
                   instead, equal to group_tag on 100% of them

**There are several rows per unit-period**, one per role code, so
(date, period, unit) is *not* a key. Aggregate before joining anything to it.
Observed roles on a typical month, by volume: 9 (generation sales, the bulk),
4 (bilateral contracts), 1 (large generation), 7 (retail purchase), 10, 6, 5,
3, 8. Only role 4 carries a group tag.

`period` runs 1..N over the *local* Madrid day, so N is 23 or 25 on DST days.
Resolution is derived from the observed period count per day, never assumed --
see the DST and 15-minute traps in CLAUDE.md.

**PDBF adopted the 15-minute MTU on 2025-03-19**, not on 2025-10-01 like the
day-ahead auction and not in June 2025 like intraday. The break is clean: 24
periods a day through 2025-03-18, 96 from 2025-03-19. A third resolution date
for a third dataset -- do not infer one from another.

That is also the day `cab` changed its fixed-width layout, and the day the
61-day bid clearing-identity anomaly cluster begins. Three datasets changing on
one date makes an OMIE platform migration on 2025-03-19 the obvious reading.

**`schedule_mw` is average MW, not MWh per period.** Confirmed on Asco 1
(1,028 MW nameplate), which reads 995.8 hourly and 1,003.0 at 15 minutes -- had
the field been MWh per quarter it would read ~250. Summing the raw column
across the 15-minute era therefore overstates energy fourfold: April 2025 sums
to 119.29 "TWh" against ~27 TWh in neighbouring years. Derive energy exactly as
the bid files do:

    energy_mwh = schedule_mw * resolution_min / 60

The signed convention means a unit appears with both signs across its life
(pumped storage buys and sells), so do not filter on sign to identify a role;
use the registry's role code.
"""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
import zipfile
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import (  # noqa: E402
    DATA, OMIE_LIST, month_range, monthly_parquet_may_grow, monthly_zip_may_grow,
    omie_url, resolution_minutes, session, START, END,
)

ZIPS = DATA / "omie" / "pdbf" / "zips"
OUT = DATA / "omie" / "pdbf" / "parquet"

SCHEMA = pa.schema([
    ("date", pa.date32()),
    ("period", pa.int16()),
    ("resolution_min", pa.int8()),
    ("unit", pa.string()),
    ("unit_id", pa.int64()),
    ("schedule_mw", pa.float64()),
    ("role_code", pa.string()),
    ("group_tag", pa.string()),
])


def available_months(sess) -> list[str]:
    """Scrape OMIE's own listing rather than assuming a range."""
    r = sess.get(OMIE_LIST, params={"parents[0]": "pdbf", "realdir": "pdbf"},
                 timeout=90)
    r.raise_for_status()
    return sorted(set(re.findall(r"pdbf_(\d{6})\.zip", r.text)))


def download_month(sess, ym: str) -> Path | None:
    dest = ZIPS / f"pdbf_{ym}.zip"
    have = dest.exists() and zipfile.is_zipfile(dest)
    if have and not monthly_zip_may_grow(dest, ym):
        return dest
    tmp = dest.with_suffix(".zip.part")
    with sess.get(omie_url("pdbf", f"pdbf_{ym}.zip"), timeout=900,
                  stream=True, allow_redirects=True) as r:
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
    """Rows for one day, plus the observed period count.

    Resolution is derived from the maximum period seen, so DST days (23/25) and
    the 15-minute era (92/96/100) are all handled without a date rule.
    """
    rows = []
    max_period = 0
    for rec in csv.reader(io.StringIO(raw.decode("latin-1")), delimiter=";"):
        if len(rec) < 9 or not rec[0].strip().isdigit():
            continue
        unit = rec[4].strip()
        if not unit:
            continue
        try:
            d = datetime(int(rec[0]), int(rec[1]), int(rec[2])).date()
            period = int(rec[3])
            mwh = float(rec[5])
        except ValueError:
            continue
        max_period = max(max_period, period)
        try:
            uid = int(rec[8])
        except (ValueError, IndexError):
            uid = None
        rows.append((d, period, unit, uid, mwh,
                     rec[7].strip() or None, rec[6].strip() or None))
    return rows, max_period


def write_month(ym: str, rows: list, res: int) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cols = list(zip(*rows)) if rows else [()] * 7
    tbl = pa.table({
        "date": pa.array(cols[0], pa.date32()),
        "period": pa.array(cols[1], pa.int16()),
        "resolution_min": pa.array([res] * len(rows), pa.int8()),
        "unit": pa.array(cols[2], pa.string()),
        "unit_id": pa.array(cols[3], pa.int64()),
        "schedule_mw": pa.array(cols[4], pa.float64()),
        "role_code": pa.array(cols[5], pa.string()),
        "group_tag": pa.array(cols[6], pa.string()),
    }, schema=SCHEMA)
    pq.write_table(tbl, OUT / f"pdbf_{ym}.parquet", compression="zstd")
    return tbl.num_rows


def process_month(sess, ym: str, keep_zips: bool) -> int:
    dest = OUT / f"pdbf_{ym}.parquet"
    # The zip is deleted once parsed, so whether a month is complete has to be
    # read off the parquet: a frontier month stops short of its last day and is
    # re-fetched until it reaches it. See `month_may_grow` in omie_common.
    if dest.exists() and not monthly_parquet_may_grow(dest, ym):
        return -1
    z = download_month(sess, ym)
    if z is None:
        return 0
    rows: list = []
    # Resolution can change within a month (the 15-minute switch is 2025-10-01
    # and DST days sit mid-month), so track it per day and keep the modal value
    # for the file while recording each day's own count.
    per_day_res: dict = {}
    with zipfile.ZipFile(z) as zf:
        for name in sorted(zf.namelist()):
            if name.endswith("/"):
                continue
            digits = "".join(ch for ch in Path(name).name if ch.isdigit())[:8]
            if len(digits) != 8:
                continue
            day_rows, max_period = parse_member(zf.read(name))
            if not day_rows:
                continue
            per_day_res[day_rows[0][0]] = resolution_minutes(max_period)
            rows.extend(day_rows)
    if not rows:
        return 0
    # Attach each row its own day's resolution rather than a month-wide guess.
    res_by_day = per_day_res
    OUT.mkdir(parents=True, exist_ok=True)
    cols = list(zip(*rows))
    tbl = pa.table({
        "date": pa.array(cols[0], pa.date32()),
        "period": pa.array(cols[1], pa.int16()),
        "resolution_min": pa.array([res_by_day[d] for d in cols[0]], pa.int8()),
        "unit": pa.array(cols[2], pa.string()),
        "unit_id": pa.array(cols[3], pa.int64()),
        "schedule_mw": pa.array(cols[4], pa.float64()),
        "role_code": pa.array(cols[5], pa.string()),
        "group_tag": pa.array(cols[6], pa.string()),
    }, schema=SCHEMA)
    pq.write_table(tbl, dest, compression="zstd")
    if not keep_zips:
        z.unlink(missing_ok=True)
    return tbl.num_rows


def verify() -> int:
    """Re-derive PDBF against the auction from the files themselves.

    PDBF should exceed PDBC on the sell side, because it adds bilateral
    contracts and self-scheduling to the auction result. A month where it does
    not is a parsing failure, not a market fact.
    """
    import pyarrow.compute as pc
    import pyarrow.dataset as ds

    bad = 0
    for f in sorted(OUT.glob("pdbf_*.parquet")):
        ym = f.stem.split("_")[1]
        bids = DATA / "omie" / "bids" / "parquet" / f"bids_{ym}.parquet"
        t = pq.read_table(f, columns=["schedule_mw", "resolution_min"])
        sell = pc.sum(pc.multiply(
            pc.max_element_wise(t.column("schedule_mw"), pa.scalar(0.0)),
            pc.divide(pc.cast(t.column("resolution_min"), pa.float64()),
                      pa.scalar(60.0)))).as_py() or 0.0
        if not bids.exists():
            print(f"  {ym}  PDBF sell {sell/1e6:9.2f} TWh   (no bid file)")
            continue
        b = ds.dataset(bids).to_table(
            filter=(pc.field("status") == "C") & (pc.field("side") == "V"),
            columns=["power_mw", "resolution_min"])
        cleared = pc.sum(pc.multiply(
            pc.cast(b.column("power_mw"), pa.float64()),
            pc.divide(pc.cast(b.column("resolution_min"), pa.float64()),
                      pa.scalar(60.0)))).as_py() or 0.0
        ratio = sell / cleared if cleared else float("nan")
        flag = "" if ratio >= 1.0 else "   <-- PDBF below auction, check parse"
        if ratio < 1.0:
            bad += 1
        print(f"  {ym}  PDBF sell {sell/1e6:8.2f} TWh   "
              f"PDBC {cleared/1e6:8.2f} TWh   ratio {ratio:5.2f}{flag}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--month", help="single YYYYMM")
    ap.add_argument("--keep-zips", action="store_true")
    ap.add_argument("--verify", action="store_true",
                    help="compare PDBF against the auction, per month")
    args = ap.parse_args()

    if args.verify:
        return verify()

    ZIPS.mkdir(parents=True, exist_ok=True)
    sess = session()
    months = [args.month] if args.month else available_months(sess)
    months = [m for m in months
              if START.strftime("%Y%m") <= m <= END.strftime("%Y%m")]
    total = 0
    for i, ym in enumerate(months, 1):
        n = process_month(sess, ym, args.keep_zips)
        if n == -1:
            print(f"  [{i}/{len(months)}] {ym}    already on disk")
        elif n == 0:
            print(f"  [{i}/{len(months)}] {ym}    NO DATA")
        else:
            total += n
            print(f"  [{i}/{len(months)}] {ym}    {n:,} rows")
    files = sorted(OUT.glob("pdbf_*.parquet"))
    grand = sum(pq.ParquetFile(f).metadata.num_rows for f in files)
    print(f"\n{len(files)} months, {grand:,} rows in {OUT}"
          + (f"  ({total:,} new)" if total else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
