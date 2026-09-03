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

FORMAT -- now taken from OMIE's own published specification

Fixed-width, latin-1, no header row. One line per unit per day. **There are
two layouts**, and the file switches between them on 2025-03-19 mid-month.

Field positions below are OMIE's, from *Modelo de Ficheros para la distribucion
publica de Informacion publica* -- **v1.35** (in force 2024-06-13, the last
edition describing the wide layout) and **v1.37** (in force 2025-09-30, the
current one). Both are public PDFs under
`https://www.omie.es/sites/default/files/<YYYY-MM>/formato_ficheros_inf_pub_<v>.pdf`.
The spec numbers positions from 1; the slices here are 0-based.

Until 2026-09-03 this parser inferred the numeric fields by splitting on
whitespace and indexing the resulting tokens. That happened to land correctly,
but only because every value was narrower than its column. A single value
filling its width (`99999.9` in an `F7.1`, say) would have run into its
neighbour and silently shifted every later field by one. Slice by position.

WIDE layout, 169 characters, used up to and including 2025-03-18:

    [  0:  7]  offer_id      CodOferta  I7   -- the OFFER code, not a unit id
    [  7: 10]  version       Version    I3
    [ 10: 17]  unit          Codigo     A7   -- joins to the bid curves
    [ 17: 47]  descr         Descripcion A30
    [ 47: 48]  side          CV         A1   -- C compra / V venta
    [ 48: 49]  (unused)      Int        A1   -- spec says unused; always "N"
    [ 49: 50]  ofer_plazo    OferPlazo  A1   -- O normal / P from a UCP
    [ 50: 67]  (unused)                 F17.3 -- spec says unused; verified 0.000
    [ 67: 84]  (unused)                 F17.3 -- spec says unused; verified 0.000
    [ 84: 91]  max_ramp_up   MaxRamSub  F7.1
    [ 91: 98]  max_ramp_down MaxRamBaj  F7.1
    [ 98:115]  min_income_fixed_eur   Fijoeuro F17.3
    [115:132]  min_income_var_eur_mwh Vareuro  F17.3
    [132:139]  max_power_mw  MaxPot     F7.1
    [139:146]  max_ramp_startup MaxRamArr F7.1
    [146:153]  max_ramp_shutdown MaxRamPar F7.1
    [153:155]  cod_int       CodInt     I2
    [155:169]  declared_at   YYYYMMDDHHMMSS

NARROW layout, 94 characters, from 2025-03-19:

    [  0: 10]  offer_id      CodOferta  I10
    [ 10: 15]  version       Version    I5
    [ 15: 22]  unit          Codigo     A7
    [ 22: 52]  descr         Descripcion A30
    [ 52: 53]  side          CV         A1
    [ 53: 54]  ofer_plazo    OferPlazo  A1
    [ 54: 71]  sco_fixed_eur Fijoeuro   F17.3 -- "termino fijo en EUR de la oferta SCO"
    [ 71: 78]  max_power_mw  MaxPot     F7.1
    [ 78: 80]  cod_int       CodInt     I2
    [ 80: 94]  declared_at   YYYYMMDDHHMMSS

Every field moved, and the pre-2026-08-13 parser's guard (`line[:7]` is all
digits) still passed on the narrow layout because [0:7] is leading spaces plus
digits. So it did not fail -- it silently emitted `0AB`, `0AC` as unit codes for
every month from 2025-03-19 on. Assert the line width; do not infer the layout
from the month, because the change lands mid-March.

WHAT THE 2025-03-19 CHANGE ACTUALLY DID TO THE MINIMUM INCOME CONDITION

OMIE replaced the offer typology on that date, for the European single
day-ahead coupling (SDAC). The old complex condition gave way to the **SCO**
(*Scalable Complex Order*), and the header now publishes **one** lump-sum
`Fijoeuro` in EUR instead of a fixed EUR/day plus a variable EUR/MWh term. The
variable term is not withheld -- under the new typology it does not exist as a
separately declared parameter. What replaces it is the SCO's own scalable price
tranches in `det`, which from the same date carry a **MAV** (Minimum Acceptable
Volume) per offer.

**The two fixed terms are not the same quantity and must never be spliced.**
ABO1 (C.T. Abono 1, 351 MW) declares 24,000 EUR/day fixed and 127.50 EUR/MWh
variable on 2025-03-18, and a single 601,620 EUR on 2025-03-19. Nor is it the
same population: on those two days 19 units declare a wide fixed term and 53 a
variable one, against 31 declaring an SCO fixed term. Hence two columns,
`min_income_fixed_eur` and `sco_fixed_eur`, never one.

Consequence for analysis, unchanged in substance from before: work needing the
**declared start-up cost on a consistent basis runs 2017-01-01 to 2025-03-18**.
`sco_fixed_eur` is a usable primitive after that date, but a different one.

`max_power_mw` is **confirmed** across the boundary: of the 2,390 units present
on both 2025-03-18 and 2025-03-19, 100% reproduce the same capacity.

The four ramp fields are documented but mostly empty -- on 2025-03-18, 5 of
2,454 units declare a non-zero up or down ramp and none declare a startup or
shutdown ramp. **The spec gives no unit of measure for them**, so they are
carried under OMIE's own field names without a unit suffix rather than being
labelled MW/min on a guess.

`offer_id` is `CodOferta`, the code of the *offer*, and changes from day to day
(ABO1 is 9497313 on 14 March and 9512371 on 18 March). It is not a stable unit
registration id and does not join to `pdbce`; use `unit` for that. It was
called `unit_id` here until 2026-09-03, which was simply wrong.

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
    ("offer_id", pa.int64()),
    ("version", pa.int32()),
    ("descr", pa.string()),
    ("offer_type", pa.string()),
    ("side", pa.string()),
    ("ofer_plazo", pa.string()),
    # Wide layout only (to 2025-03-18): the old minimum-income condition.
    ("min_income_fixed_eur", pa.float64()),
    ("min_income_var_eur_mwh", pa.float64()),
    # Narrow layout only (2025-03-19 on): Fijoeuro, the SCO lump-sum fixed
    # term. NOT comparable with min_income_fixed_eur -- see the docstring.
    ("sco_fixed_eur", pa.float64()),
    ("max_power_mw", pa.float64()),
    # Wide layout only. Units of measure are undocumented in OMIE's spec.
    ("max_ramp_up", pa.float64()),
    ("max_ramp_down", pa.float64()),
    ("max_ramp_startup", pa.float64()),
    ("max_ramp_shutdown", pa.float64()),
    ("cod_int", pa.int32()),
    ("declared_at", pa.timestamp("s")),
    ("layout", pa.string()),
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


def _f(s: str) -> float | None:
    """One fixed-width numeric column. Blank padding means absent, not zero."""
    s = s.strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _i(s: str) -> int | None:
    s = s.strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def _ts(s: str) -> pd.Timestamp | None:
    """Registration timestamp, YYYYMMDDHHMMSS in Madrid local time."""
    s = s.strip()
    if len(s) != 14 or not s.isdigit():
        return None
    return pd.to_datetime(s, format="%Y%m%d%H%M%S", errors="coerce")


def _parse_wide(line: str, day: pd.Timestamp) -> tuple | None:
    unit = line[10:17].strip()
    if not unit:
        return None
    # offer_type is retained as OMIE writes it -- CV + Int + OferPlazo, e.g.
    # "VNO" -- so pre-2026-09 outputs stay comparable. The components are also
    # broken out into `side` and `ofer_plazo`.
    offer_type = line[47:50].strip()
    return (
        day.date(), unit, _i(line[0:7]), _i(line[7:10]), line[17:47].strip(),
        offer_type or None,
        line[47:48].strip() or None,      # side  (CV)
        line[49:50].strip() or None,      # ofer_plazo
        _f(line[98:115]),                 # min_income_fixed_eur  (Fijoeuro)
        _f(line[115:132]),                # min_income_var_eur_mwh (Vareuro)
        None,                             # sco_fixed_eur -- narrow only
        _f(line[132:139]),                # max_power_mw (MaxPot)
        _f(line[84:91]),                  # max_ramp_up   (MaxRamSub)
        _f(line[91:98]),                  # max_ramp_down (MaxRamBaj)
        _f(line[139:146]),                # max_ramp_startup  (MaxRamArr)
        _f(line[146:153]),                # max_ramp_shutdown (MaxRamPar)
        _i(line[153:155]),                # cod_int
        _ts(line[155:169]),
        "wide",
    )


def _parse_narrow(line: str, day: pd.Timestamp) -> tuple | None:
    unit = line[15:22].strip()
    if not unit:
        return None
    offer_type = line[52:54].strip()     # CV + OferPlazo, e.g. "VO"
    return (
        day.date(), unit, _i(line[0:10]), _i(line[10:15]), line[22:52].strip(),
        offer_type or None,
        line[52:53].strip() or None,      # side  (CV)
        line[53:54].strip() or None,      # ofer_plazo
        None,                             # min_income_fixed_eur  -- wide only
        None,                             # min_income_var_eur_mwh -- wide only
        _f(line[54:71]),                  # sco_fixed_eur (Fijoeuro)
        _f(line[71:78]),                  # max_power_mw  (MaxPot)
        None, None, None, None,           # ramps -- not published post-change
        _i(line[78:80]),                  # cod_int
        _ts(line[80:94]),
        "narrow",
    )


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
        elif LINE_LEN_NARROW - 2 <= n <= LINE_LEN_NARROW + 1:
            row = _parse_narrow(line, day)
        elif line.strip():
            raise ValueError(
                f"{day.date()}: unrecognised cab line width {n} "
                f"(expected {LINE_LEN_WIDE} or {LINE_LEN_NARROW}): {line[:60]!r}")
        else:
            continue
        if row is not None:
            rows.append(row)
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
