#!/usr/bin/env python3
"""OMIE `marginalpibc` — published intraday marginal prices, per session.

    .venv/bin/python scripts/fetch/fetch_omie_intraday_prices.py
    .venv/bin/python scripts/fetch/fetch_omie_intraday_prices.py --verify

Writes data/omie/intraday_prices/omie_intraday_prices.parquet. Token-free.
Resumable: yearly zips and daily files already on disk are skipped.

WHY FETCH WHAT COULD BE DERIVED

`sequential_market_premium.py` first derived the intraday clearing price from the
bid archive: in a uniform-price auction the clearing price is bracketed by
`max(cleared sell) <= p* <= min(cleared buy)`. Checked against OMIE's published
prices on 1,875 date-session-periods, that estimator is **not good enough for
this design**:

| estimator | median abs err | p95 | exact | mean err |
|---|---|---|---|---|
| max cleared sell | 0.010 | 7.802 | 48.8% | **+1.069** |
| min cleared buy | 0.000 | 3.876 | 53.7% | −0.651 |
| bracket midpoint | 0.245 | 7.139 | 22.2% | +0.209 |

The premium being measured is about 1 EUR/MWh. A p95 error of 3.9-7.8 EUR/MWh
swamps it.

Worse, the error violates its own theory: `max(cleared sell)` is a **lower
bound** on the clearing price, so its error should never be positive — and it is
positive on 10% of rows, averaging +5.28 there. The cause is in the same data:
the published files show ES and PT prices differing on **13.1%** of intraday
periods. **The intraday market splits independently of the day-ahead market**,
and the bid archive tags almost every unit `MI` rather than by zone, so pooling
both zones' units picks up whichever price is higher. Filtering on day-ahead
splitting, as the first cut did, does not remove intraday splitting.

FILE LAYOUT — the pattern is date PLUS session, not one file per day

Filenames are `marginalpibc_YYYYMMDD<SS>.1`, where `SS` is the two-digit session
index. A date-only guess returns 404 on every request, which reads as "the
dataset does not exist" rather than "the pattern is wrong" — that is how the
first attempt failed.

Following `marginalpdbc`, **2018-2022 exist only as yearly zips** and 2023
onward as daily files. Assuming the daily pattern throughout silently loses five
years.

Fields are `YYYY;MM;DD;period;price_A;price_B;`. The day-ahead file
`marginalpdbc` is documented in CLAUDE.md as **Portugal first, then Spain**, and
this file is from the same publisher and family — but that is an assumption
until checked, so `--verify` decides it from the data by asking which column
tracks the day-ahead Spanish price more closely, rather than trusting the
analogy.
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import zipfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, omie_url, session  # noqa: E402

OUT = DATA / "omie" / "intraday_prices"
RAW = OUT / "raw"
PARQ = OUT / "omie_intraday_prices.parquet"
DATASET = "marginalpibc"


def listing(sess) -> list[str]:
    u = (f"https://www.omie.es/es/file-access-list?parents%5B0%5D={DATASET}"
         f"&realdir={DATASET}")
    r = sess.get(u, timeout=120)
    r.raise_for_status()
    names = set(re.findall(rf"{DATASET}_\d{{4}}\.zip", r.text))
    names |= set(re.findall(rf"{DATASET}_\d{{10}}\.\d+", r.text))
    return sorted(names)


def parse_text(txt: str, sess_idx: int) -> list[dict]:
    rows = []
    for line in txt.splitlines():
        f = line.strip().rstrip(";").split(";")
        if len(f) < 6 or not f[0].isdigit() or len(f[0]) != 4:
            continue
        try:
            rows.append(dict(
                date=pd.Timestamp(int(f[0]), int(f[1]), int(f[2])),
                session=sess_idx, period=int(f[3]),
                price_a=float(f[4].replace(",", ".")),
                price_b=float(f[5].replace(",", ".")),
            ))
        except (ValueError, TypeError):
            continue
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    RAW.mkdir(parents=True, exist_ok=True)
    if args.verify:
        return verify()

    s = session()
    names = listing(s)
    zips = [n for n in names if n.endswith(".zip")]
    dailies = [n for n in names if not n.endswith(".zip")]
    print(f"{len(zips)} yearly zips, {len(dailies)} daily files")

    rows = []
    for z in zips:
        p = RAW / z
        if not p.exists():
            r = s.get(omie_url(DATASET, z), timeout=900)
            r.raise_for_status()
            p.write_bytes(r.content)
        with zipfile.ZipFile(p) as zf:
            for m in zf.namelist():
                mm = re.search(r"_(\d{8})(\d{2})", m)
                if not mm:
                    continue
                rows += parse_text(zf.read(m).decode("latin-1"), int(mm.group(2)))
        print(f"  {z}: cumulative {len(rows):,} rows", flush=True)

    cache = RAW / "daily_cache.parquet"
    done = set()
    if cache.exists():
        c = pd.read_parquet(cache)
        rows += c.to_dict("records")
        done = set(c.attrs.get("names", []))
    new = []
    todo = [n for n in dailies if n not in done]
    for i, n in enumerate(todo, 1):
        mm = re.search(r"_(\d{8})(\d{2})\.", n)
        if not mm:
            continue
        r = s.get(omie_url(DATASET, n), timeout=60)
        if r.status_code != 200 or "<html" in r.text[:200].lower():
            continue
        new += parse_text(r.text, int(mm.group(2)))
        done.add(n)
        if i % 250 == 0:
            print(f"  daily {i}/{len(todo)}, {len(new):,} new rows", flush=True)
    rows += new
    d = pd.DataFrame(rows).drop_duplicates(subset=["date", "session", "period"])
    d = d.sort_values(["date", "session", "period"])
    OUT.mkdir(parents=True, exist_ok=True)
    d.to_parquet(PARQ, index=False)
    c = d.copy()
    c.attrs["names"] = sorted(done)
    c.to_parquet(cache, index=False)
    print(f"\n  {len(d):,} rows, {d.date.min().date()} to {d.date.max().date()}, "
          f"sessions {sorted(d.session.unique())}")
    print(f"  wrote {PARQ}")
    return 0


def verify() -> int:
    d = pd.read_parquet(PARQ)
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    d["date"] = pd.to_datetime(d.date)
    m = d.merge(px, on=["date", "period"], how="inner")
    print(f"{len(d):,} intraday price rows, {len(m):,} matched to day-ahead")
    print(f"  sessions: {sorted(d.session.unique())}")
    print(f"  ES/PT differ (intraday splits) on "
          f"{(d.price_a != d.price_b).mean():.1%} of rows")
    print("\nWHICH COLUMN IS SPAIN? decided from the data, not from the "
          "marginalpdbc analogy")
    for c in ("price_a", "price_b"):
        print(f"  corr({c}, day-ahead ES) = {m[c].corr(m.price_es):+.5f}   "
              f"corr({c}, day-ahead PT) = {m[c].corr(m.price_pt):+.5f}")
    sp = m[m.price_a != m.price_b]
    if len(sp) > 100:
        print(f"\n  on the {len(sp):,} intraday-splitting periods "
              "(where the two genuinely differ):")
        for c in ("price_a", "price_b"):
            print(f"    mean |{c} - DA ES| = {(sp[c]-sp.price_es).abs().mean():.3f}"
                  f"   mean |{c} - DA PT| = {(sp[c]-sp.price_pt).abs().mean():.3f}")
        print("  the column closer to the day-ahead ES price on splitting "
              "periods is Spain.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
