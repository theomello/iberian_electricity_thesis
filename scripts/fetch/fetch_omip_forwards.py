#!/usr/bin/env python3
"""Fetch OMIP forward (futures) settlement prices for the Iberian power market.

    .venv/bin/python scripts/fetch/fetch_omip_forwards.py
    .venv/bin/python scripts/fetch/fetch_omip_forwards.py --year 2021
    .venv/bin/python scripts/fetch/fetch_omip_forwards.py --zone PT

Writes data/omip/parquet/omip_forwards_{zone}_{YYYY}.parquet, one file per year.

WHY THIS EXISTS

Two distinct jobs, both of which the rest of this repo cannot do without it.

**1. The expected future price, for a water-value model.** A hydro plant with
storage has no fuel cost. Its true marginal cost is the *opportunity cost of
water* -- what the stored energy would earn if kept for later. That is a
function of the expected future price, and the forward curve is the market's
own statement of it. Arzhintar, Leslie, Neill and Wyrwoll estimate an
opportunity-cost function c(pf, Vol, Snow); `pf` is this file.

Without it, any event study around a Spanish policy date is confounded: hydro
offer prices peaked in March 2022 with the *gas* price, not on a policy date,
because expectations moved. Netting that channel out is the whole point.

**2. Bounding the financial hedge position.** PDBF publishes *physical*
bilateral contracts (role 4), but a financially settled contract fixes revenue
while the energy still clears in the auction, and is invisible there. This
matters concretely for the 2021 clawback: RDL 23/2021 exempted energy under
fixed-price forward contracts from the levy, **whether settled physically or
financially**, so a firm's exposure to the policy depends on a quantity we can
only partly see. Open interest and traded volume here bound the financial part
at market level -- not per firm, but enough to say whether the physical series
is a floor worth trusting.

SOURCE

`omip.pt`, token-free, no registration. One HTML page per trading date carries
the whole curve for a zone:

    /en/dados-mercado?date=YYYY-MM-DD&product=EL&zone=ES&instrument=FTB

`FTB` is the SPEL base-load future (SPEL = Spanish electricity). Each maturity
class -- Day, Weekend, Week, Month, Quarter, Year, and PPA strips -- is its own
HTML table, captioned "SPEL Base Futures - <maturity>". The caption is the only
place the maturity appears, so it is parsed from there and carried as a column.

Columns: `trade_date`, `zone`, `maturity`, `contract`, `isin`,
`price_ref_eur_mwh` (the D settlement price), `price_ref_prev_eur_mwh` (D-1),
`best_bid`, `best_ask`, `session_volume_mwh`, `open_interest`, `n_contracts`,
`otc_volume_mwh`, `nominal_mwh`, `last_trading_day`.

NOTES AND TRAPS

- **Non-trading days return a page with no data rows**, not an error. They are
  skipped and recorded, so a genuinely new gap is still visible.
- The contract-name cell is a run-together blob --
  `ISIN Code: PTFTO0182355Nominal Fixo MWH: 24Trading last day: 2021-09-16Trading
  quotation: EUR/MWhFTB D Fr17Sep-21` -- with the contract code only at the end.
  Fields are cut by label, and the code is what follows the quotation label.
- Prices read `n.a.` when a contract did not settle; those become null rather
  than zero. **A zero would be a real price** in this market.
- This is a public website, not an API. Requests are serialised with a delay
  and the fetcher is resumable, so an interrupted run costs nothing.
- Yearly contract-specification workbooks exist at
  `/sites/default/files/dados/eod/omip_contracts_YYYY.xlsx` (2018 onward) but
  carry **no prices** -- they are instrument definitions only.
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, START, END, session  # noqa: E402

OUT = DATA / "omip" / "parquet"
BASE = "https://www.omip.pt/en/dados-mercado"
DELAY = 0.7  # polite; this is a public website, not an API

SCHEMA = pa.schema([
    ("trade_date", pa.date32()),
    ("zone", pa.string()),
    ("maturity", pa.string()),
    ("contract", pa.string()),
    ("isin", pa.string()),
    ("price_ref_eur_mwh", pa.float64()),
    ("price_ref_prev_eur_mwh", pa.float64()),
    ("best_bid", pa.float64()),
    ("best_ask", pa.float64()),
    ("session_volume_mwh", pa.float64()),
    ("open_interest", pa.float64()),
    ("n_contracts", pa.float64()),
    ("otc_volume_mwh", pa.float64()),
    ("nominal_mwh", pa.float64()),
    ("last_trading_day", pa.string()),
])

TAG = re.compile(r"<[^>]+>")
WS = re.compile(r"\s+")


def num(s: str | None) -> float | None:
    """`n.a.` and blanks are missing. Zero is a real price here, never a filler."""
    if s is None:
        return None
    s = s.strip().replace(",", "")
    if not s or s.lower() in {"n.a.", "na", "-", "n/a"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def clean(html: str) -> str:
    return WS.sub(" ", TAG.sub("", html)).strip()


def split_name(blob: str) -> tuple[str | None, str | None, float | None, str | None]:
    """Cut the run-together contract cell by its labels.

    The contract code is only identifiable as the text after the trading-quotation
    label, so the labels are the parse -- position is not stable.
    """
    isin = re.search(r"ISIN Code:\s*([A-Z0-9]+)", blob)
    nominal = re.search(r"Nominal\s+\w+\s+MWH:\s*([\d.,]+)", blob, re.I)
    ltd = re.search(r"Trading last day:\s*([\d-]+)", blob)
    code = re.split(r"Trading quotation:\s*\S+", blob)
    contract = code[-1].strip() if len(code) > 1 else None
    return (isin.group(1) if isin else None,
            contract or None,
            num(nominal.group(1)) if nominal else None,
            ltd.group(1) if ltd else None)


def parse_page(html: str, d: date, zone: str) -> list[tuple]:
    rows: list[tuple] = []
    for m in re.finditer(r"<table[^>]*>(.*?)</table>", html, re.S):
        # The maturity appears only in the caption preceding the table.
        pre = html[max(0, m.start() - 600):m.start()]
        caps = [c.strip() for c in re.findall(r">([^<>]{3,80})<", pre) if c.strip()]
        maturity = None
        for c in reversed(caps):
            hit = re.search(r"Futures\s*[-–]\s*(.+)$", c)
            if hit:
                maturity = hit.group(1).strip()
                break
        for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", m.group(1), re.S):
            cells = [clean(c) for c in
                     re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
            if len(cells) < 16 or "ISIN Code" not in cells[0]:
                continue
            isin, contract, nominal, ltd = split_name(cells[0])
            rows.append((
                d, zone, maturity, contract, isin,
                num(cells[14]), num(cells[15]),
                num(cells[2]), num(cells[3]), num(cells[4]),
                num(cells[10]), num(cells[11]), num(cells[12]),
                nominal, ltd,
            ))
    return rows


def fetch_day(sess, d: date, zone: str) -> list[tuple]:
    r = sess.get(BASE, params={"date": d.isoformat(), "product": "EL",
                               "zone": zone, "instrument": "FTB"}, timeout=90)
    if r.status_code != 200:
        return []
    return parse_page(r.text, d, zone)


def write_year(year: int, zone: str, rows: list[tuple]) -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    cols = list(zip(*rows))
    tbl = pa.table({f.name: pa.array(cols[i], f.type)
                    for i, f in enumerate(SCHEMA)}, schema=SCHEMA)
    pq.write_table(tbl, OUT / f"omip_forwards_{zone}_{year}.parquet",
                   compression="zstd")
    return tbl.num_rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, help="single year")
    ap.add_argument("--zone", default="ES", choices=["ES", "PT"])
    ap.add_argument("--delay", type=float, default=DELAY)
    args = ap.parse_args()

    sess = session()
    years = [args.year] if args.year else range(START.year, END.year + 1)
    grand = 0
    for year in years:
        dest = OUT / f"omip_forwards_{args.zone}_{year}.parquet"
        if dest.exists():
            print(f"  {year}  already on disk")
            continue
        lo = max(START, date(year, 1, 1))
        hi = min(END, date(year, 12, 31))
        rows: list[tuple] = []
        empty = 0
        d = lo
        while d <= hi:
            if d.weekday() < 5:            # OMIP does not trade at weekends
                got = fetch_day(sess, d, args.zone)
                if got:
                    rows.extend(got)
                else:
                    empty += 1
                time.sleep(args.delay)
            d += timedelta(days=1)
        if not rows:
            print(f"  {year}  NO DATA")
            continue
        n = write_year(year, args.zone, rows)
        grand += n
        days = len({r[0] for r in rows})
        print(f"  {year}  {n:,} rows   {days} trading days   "
              f"{empty} weekday(s) with no data")
    files = sorted(OUT.glob(f"omip_forwards_{args.zone}_*.parquet"))
    total = sum(pq.ParquetFile(f).metadata.num_rows for f in files)
    print(f"\n{len(files)} years, {total:,} rows in {OUT}"
          + (f"  ({grand:,} new)" if grand else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
