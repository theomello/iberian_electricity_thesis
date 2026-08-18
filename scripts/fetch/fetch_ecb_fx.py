#!/usr/bin/env python3
"""Fetch the ECB's daily USD/EUR reference rate -- the currency conversion
`fetch_coal_price.py`'s USD series needs before it can join the EUR-only
marginal-cost inputs.

    .venv/bin/python scripts/fetch/fetch_ecb_fx.py
    .venv/bin/python scripts/fetch/fetch_ecb_fx.py --verify

Writes data/ecb/ecb_usd_eur_daily.parquet, one row per ECB publication day.
Unlike the investing.com price series, this one is an ordinary token-free,
resumable fetch -- the ECB's Statistical Data Warehouse API is public and
answers a plain `requests` call, no browser session needed.

SOURCE

`data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A`, the ECB's own
"US dollar/Euro ECB reference exchange rate, 2.15pm (C.E.T.)" series --
the standard daily reference rate, published on every day the ECB and
member-state central banks are open (not full 5/7 -- some Eurosystem
holidays fall on weekdays the ECB doesn't publish on top of the usual
weekends). Confirmed 2026-08-18: 2,207 rows, 2018-01-02 -> 2026-08-17.

WHAT THE RATE MEANS -- DIVIDE, DON'T MULTIPLY

Despite the field being named `USD` under a `EUR`-denominated series, the
published number is **USD per 1 EUR** (e.g. 1.2065 on 2018-01-02 -- correct,
EUR was worth about $1.21 then). To convert a USD amount to EUR:

    eur_amount = usd_amount / usd_per_eur

`fetch_coal_price.py`'s USD/tonne coal price needs exactly this division,
not a multiplication -- confirmed against a known point (EUR was ~1.20
USD in early 2018, ~1.05-1.15 more recently; multiplying instead of
dividing would move the coal price the wrong direction by the square of
the true adjustment).

COLUMNS

    date              publication day
    usd_per_eur       USD needed to buy 1 EUR (divide a USD amount by this)
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, session  # noqa: E402

OUT_DIR = DATA / "ecb"
OUT = OUT_DIR / "ecb_usd_eur_daily.parquet"
URL = ("https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A"
       "?format=csvdata&startPeriod=2018-01-01&endPeriod=2026-12-31")


def fetch(sess) -> pd.DataFrame:
    r = sess.get(URL, timeout=60)
    r.raise_for_status()
    df = pd.read_csv(io.StringIO(r.text))
    df = df.rename(columns={"TIME_PERIOD": "date", "OBS_VALUE": "usd_per_eur"})
    df = df[["date", "usd_per_eur"]].copy()
    df["date"] = pd.to_datetime(df.date)
    df = df.dropna(subset=["usd_per_eur"]).sort_values("date").reset_index(drop=True)
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                     help="re-derive coverage facts from the written parquet")
    ap.add_argument("--refresh", action="store_true",
                     help="re-fetch even if the output parquet already exists")
    args = ap.parse_args()

    if OUT.exists() and not args.refresh and not args.verify:
        print(f"  {OUT} already exists; pass --refresh to re-fetch")
        df = pd.read_parquet(OUT)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        df = fetch(session())
        df.to_parquet(OUT, index=False)
        print(f"  wrote {OUT}")

    print(f"\n{len(df):,} days, {df.date.min().date()} -> {df.date.max().date()}")
    print(f"  usd_per_eur: mean {df.usd_per_eur.mean():.4f}, "
          f"range {df.usd_per_eur.min():.4f}-{df.usd_per_eur.max():.4f}")

    if args.verify:
        dupe = df.duplicated("date").sum()
        assert dupe == 0, "duplicate date rows -- not a key"
        assert df.date.min().year <= 2018, "series should reach back to 2018"
        assert 0.8 < df.usd_per_eur.min() and df.usd_per_eur.max() < 1.8, \
            "usd_per_eur outside a plausible historical range -- check for a units mixup"
        print("\n  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
