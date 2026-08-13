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

Fixed-width, latin-1, no header row. One line per unit per day. **There are
two layouts**, and the file switches between them on 2025-03-19 mid-month.

WIDE layout, 169 characters, used up to and including 2025-03-18:

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

NARROW layout, 94 characters, from 2025-03-19:

    [ 0:10]  unit_id     right-aligned, now 8 digits
    [10:15]  seq
    [15:22]  unit
    [22:52]  descr       plant name, 30 chars, padded
    [52:54]  offer_type  VO / CO -- two characters, not three
    [54:71]  numeric 0   UNIDENTIFIED, see below
    [71:78]  max_power_mw
    [78:  ]  registration timestamp

Every field moved, and the old parser's guard (`line[:7]` is all digits) still
passes on the narrow layout because [0:7] is leading spaces plus digits. So it
did not fail -- it silently emitted `0AB`, `0AC` as unit codes for every month
from 2025-03-19 on. Assert the line width; do not infer the layout from the
month, because the change lands mid-March.

**max_power_mw is confirmed**: matching the 2,390 units present on both
2025-03-18 and 2025-03-19 reproduces the wide layout's capacity for 100% of
them. Numeric 0 is **not** confirmed and is deliberately left unlabelled. It is
neither the old fixed term nor the old variable term -- ABO1 declares 24,000
EUR/day fixed and 127.50 EUR/MWh variable on 18 March and a single 601,620 on
19 March. The minimum income declaration is chosen per unit per day, so a
day-over-day comparison cannot identify the field, and guessing it would
corrupt exactly the start-up-cost work it is wanted for. OMIE ticket #12541 is
open; ask there.

Consequence for analysis: the **minimum income variable term in EUR/MWh is not
available from 2025-03-19**, and the fixed term is not available under that
name either. Work that needs declared start-up costs runs 2017-01-01 to
2025-03-18 unless OMIE clarifies the new field.

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
LINE_LEN_WIDE = 169
LINE_LEN_NARROW = 94
# The layout changed on this day, mid-month. Kept for documentation only --
# the parser dispatches on the observed line width, never on the date, so a
# further change fails loudly instead of silently mis-slicing.
NARROW_FROM = "2025-03-19"

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
    # Narrow layout only (2025-03-19 on). Deliberately unnamed: it is not the
    # old fixed or variable minimum-income term. See the module docstring.
    ("narrow_numeric_0", pa.float64()),
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


def _floats(rest: str) -> list[float]:
    """Leading numeric tokens; the trailing token is a registration timestamp."""
    vals = []
    for tok in rest.split():
        try:
            vals.append(float(tok))
        except ValueError:
            break
    return vals


def _parse_wide(line: str, day: pd.Timestamp) -> tuple | None:
    unit = line[10:17].strip()
    if not unit:
        return None
    offer_type = line[47:50].strip()
    vals = _floats(line[50:])
    # Only label the three fields validated against published capacity and
    # against the units observed withdrawing for a whole day.
    fixed = vals[4] if len(vals) > 6 else None
    var = vals[5] if len(vals) > 6 else None
    mw = vals[6] if len(vals) > 6 else None
    return (day.date(), unit, int(line[:7]), line[17:47].strip(), offer_type,
            offer_type[:1] if offer_type else None, fixed, var, mw, len(vals))


def _parse_narrow(line: str, day: pd.Timestamp) -> tuple | None:
    unit = line[15:22].strip()
    if not unit:
        return None
    offer_type = line[52:54].strip()
    vals = _floats(line[54:])
    # vals[1] is max power, confirmed against the wide layout across the
    # 2025-03-18/19 boundary. vals[0] is NOT the old fixed or variable term and
    # is carried unlabelled -- see the module docstring.
    mw = vals[1] if len(vals) > 1 else None
    unlabelled = vals[0] if vals else None
    return (day.date(), unit, int(line[:10]), line[22:52].strip(), offer_type,
            offer_type[:1] if offer_type else None, None, None, mw, len(vals),
            unlabelled)


def parse_member(raw: bytes, day: pd.Timestamp) -> list[tuple]:
    """Dispatch on the observed line width, never on the date.

    Both layouts begin with digits, so a date- or guard-based choice reads the
    narrow layout with wide offsets and yields plausible-looking garbage
    (`0AB`, `0AC` as unit codes) rather than raising.
    """
    rows = []
    for line in raw.decode("latin-1").splitlines():
        n = len(line.rstrip("\r\n"))
        if n >= LINE_LEN_WIDE - 1:
            row = _parse_wide(line, day)
            if row is not None:
                rows.append(row + (None,))
        elif LINE_LEN_NARROW - 2 <= n <= LINE_LEN_NARROW + 1:
            row = _parse_narrow(line, day)
            if row is not None:
                rows.append(row)
        elif line.strip():
            raise ValueError(
                f"{day.date()}: unrecognised cab line width {n} "
                f"(expected {LINE_LEN_WIDE} or {LINE_LEN_NARROW}): {line[:60]!r}")
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
