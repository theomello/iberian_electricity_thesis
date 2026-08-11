#!/usr/bin/env python3
"""Fetch OMIE `cab` -- the day-ahead offer *header* -- and parse it to parquet.

    .venv/bin/python scripts/fetch/fetch_omie_cab.py
    .venv/bin/python scripts/fetch/fetch_omie_cab.py --start 202401 --end 202412

Writes monthly zips to data/omie/cab/zips/ and parsed tables to
data/omie/cab/parquet/cab_YYYYMM.parquet. Resumable: months already on disk
are skipped.

WHY THIS FILE MATTERS

`curva_pbc_uof` (the bid curves we already have) identifies a bidder only by a
7-character unit code. `cab` is the header record that accompanies those
offers, and it carries three things nothing else in the token-free sources
publishes:

* **A descriptive plant name.** `ESCCC1` -> "C.C. ESCOMBRERAS 1". The prefix
  encodes technology: `C.C.` ciclo combinado, `C.N.` central nuclear,
  `C.T.` central termica, `UOF HIDRO`/`CH.` hydro, `PS`/`FV` solar, `PE` wind.
  This is the only token-free route to unit-level technology.
* **Maximum capacity in MW.** Validated against published figures: Asco 1
  reads 1028.0 (published ~1032), Escombreras 1 reads 408.6 (~400).
  `CLAUDE.md` records "no nameplate capacity" -- this closes that gap.
* **The minimum income condition**, as a fixed term (EUR/day) and a variable
  term (EUR/MWh). This is the complex condition behind the whole-day unit
  withdrawals documented in CLAUDE.md, and the primitive Reguant (2014) uses
  to identify startup costs. Nuclear units declare 0.000 on both.

FORMAT

Fixed-width, 169 characters, latin-1, no header row. One line per unit per
day. Layout established empirically on CAB_20240115.1:

    [ 0: 7]  unit_id     7-digit OMIE registration id, joins to pdbce
    [ 7:10]  seq         small integer, purpose unconfirmed
    [10:17]  unit        unit code, joins to the bid curves
    [17:47]  descr       plant name, 30 chars, padded
    [47:50]  offer_type  VNO / CNO / VSI / CSI -- V sell, C buy
    [50:  ]  nine numeric fields then a trailing registration timestamp

The nine numerics are, in order: two fields that are 0.000 throughout the
sample checked, two more that are 0.0, then **min income fixed**, **min income
variable**, **max capacity**, and two trailing 0.0 fields. The middle three
are the ones validated above; the outer six are carried through unnamed rather
than guessed at, because a wrong label is worse than no label.

Decimal separator here is a **dot**, unlike `curva_pbc_uof` which uses a comma
-- see the decimal-separator trap in CLAUDE.md. Do not share a parser.
"""

from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, OMIE_LIST, omie_url, session  # noqa: E402

ZIPS = DATA / "omie" / "cab" / "zips"
OUT = DATA / "omie" / "cab" / "parquet"

MEMBER_RE = re.compile(r"CAB_(\d{8})\.\d+$", re.IGNORECASE)
LINE_LEN = 169

SCHEMA = pa.schema([
    ("date", pa.date32()),
    ("unit", pa.string()),
    ("unit_id", pa.int64()),
    ("descr", pa.string()),
    ("offer_type", pa.string()),
    ("side", pa.string()),
    ("min_income_fixed_eur", pa.float64()),
    ("min_income_var_eur_mwh", pa.float64()),
    ("max_power_mw", pa.float64()),
    ("n_fields", pa.int32()),
])


def available_months(sess) -> list[str]:
    """Scrape OMIE's own listing rather than assuming a range."""
    r = sess.get(OMIE_LIST, params={"parents[0]": "cab", "realdir": "cab"},
                 timeout=90)
    r.raise_for_status()
    return sorted(set(re.findall(r"cab_(\d{6})\.zip", r.text)))


def download_month(sess, ym: str) -> Path | None:
    dest = ZIPS / f"cab_{ym}.zip"
    if dest.exists() and zipfile.is_zipfile(dest):
        return dest
    tmp = dest.with_suffix(".zip.part")
    with sess.get(omie_url("cab", f"cab_{ym}.zip"), timeout=600,
                  stream=True, allow_redirects=True) as r:
        if r.status_code != 200:
            return None
        with open(tmp, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    if not zipfile.is_zipfile(tmp):
        tmp.unlink(missing_ok=True)
        return None
    tmp.rename(dest)
    return dest


def parse_member(raw: bytes, day: pd.Timestamp) -> list[tuple]:
    rows = []
    for line in raw.decode("latin-1").splitlines():
        if len(line) < 50 or not line[:7].strip().isdigit():
            continue
        unit = line[10:17].strip()
        if not unit:
            continue
        offer_type = line[47:50].strip()
        nums = line[50:].split()
        # Trailing token is a registration timestamp, not a measurement.
        vals = []
        for tok in nums:
            try:
                vals.append(float(tok))
            except ValueError:
                break
        # Only label the three fields validated against published capacity and
        # against the units observed withdrawing for a whole day.
        fixed = vals[4] if len(vals) > 6 else None
        var = vals[5] if len(vals) > 6 else None
        mw = vals[6] if len(vals) > 6 else None
        rows.append((
            day.date(), unit, int(line[:7]), line[17:47].strip(), offer_type,
            offer_type[:1] if offer_type else None, fixed, var, mw, len(vals),
        ))
    return rows


def convert_month(zpath: Path, ym: str, force: bool = False) -> Path | None:
    out = OUT / f"cab_{ym}.parquet"
    if out.exists() and not force:
        return out
    rows: list[tuple] = []
    with zipfile.ZipFile(zpath) as z:
        for name in sorted(z.namelist()):
            m = MEMBER_RE.search(name)
            if not m:
                continue
            day = pd.Timestamp(m.group(1))
            rows.extend(parse_member(z.read(name), day))
    if not rows:
        return None
    df = pd.DataFrame(rows, columns=[f.name for f in SCHEMA])
    tmp = out.with_suffix(".parquet.part")
    pq.write_table(pa.Table.from_pandas(df, schema=SCHEMA, preserve_index=False),
                   tmp, compression="zstd")
    tmp.rename(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default=None, help="YYYYMM")
    ap.add_argument("--end", default=None, help="YYYYMM")
    ap.add_argument("--force", action="store_true", help="re-parse existing months")
    ap.add_argument("--keep-zips", action="store_true", default=True)
    args = ap.parse_args()

    ZIPS.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)

    sess = session()
    months = available_months(sess)
    if args.start:
        months = [m for m in months if m >= args.start]
    if args.end:
        months = [m for m in months if m <= args.end]
    if not months:
        print("no months matched", file=sys.stderr)
        return 1
    print(f"{len(months)} months available: {months[0]} .. {months[-1]}")

    total = 0
    for i, ym in enumerate(months, 1):
        z = download_month(sess, ym)
        if z is None:
            print(f"  ! {ym}: download failed")
            continue
        p = convert_month(z, ym, args.force)
        if p is None:
            print(f"  ! {ym}: no parsable members")
            continue
        n = pq.ParquetFile(p).metadata.num_rows
        total += n
        print(f"  [{i:3d}/{len(months)}] {ym}  {n:>8,} rows", flush=True)

    print(f"\n{total:,} rows in {OUT.relative_to(DATA.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
