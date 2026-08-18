#!/usr/bin/env python3
"""Parse the daily Rotterdam (API2-equivalent) coal price series -- the
fuel-cost input the 15 coal-fired units `build_jrc_cab_match.py` matched but
`build_implied_marginal_cost.py` left unpriced.

    .venv/bin/python scripts/fetch/fetch_coal_price.py
    .venv/bin/python scripts/fetch/fetch_coal_price.py --verify

Writes data/investing/coal_price_daily.parquet from the raw CSV already
captured at data/investing/raw/coal_rotterdam_historical.csv. Like
`fetch_eua_carbon_price.py`, **this script does not itself download
anything** -- same investing.com API, same Cloudflare block on non-browser
clients, same manual-capture requirement. See that script's docstring for
the full explanation; this one only records what's specific to coal.

SOURCE

investing.com ticker `ATWMc1`, "Rotterdam Coal" -- ICE's front-month
continuous future on the API2 CIF ARA (Argus-McCloskey) index, the standard
European seaborne thermal coal benchmark. Not listed on investing.com's main
Energy commodities page (Brent, Carbon Emissions, Crude WTI, Natural Gas,
etc. are; coal is not, consistent with its declining relevance as Europe's
coal fleet retires) -- found instead by guessing the URL slug
`rotterdam-coal-futures-historical-data`, then reading the instrument id
(1112838) out of the page's own HTML and replaying the same
`api.investing.com/api/financialdata/historical/{id}` call
`fetch_eua_carbon_price.py` uses, with the same `domain-id: www` header.
Captured 2026-08-18, full window: 2018-01-02 -> 2026-08-18, 2,227 days.

TWO CONVERSIONS STILL NEEDED BEFORE THIS FEEDS A MARGINAL-COST CALC --
NEITHER IS DONE HERE

Unlike the gas and CO2 series, this one cannot be dropped directly into
`build_implied_marginal_cost.py`'s formula:

  1. **Currency.** This series is in **USD/tonne**, not EUR -- MIBGAS and
     the EUA series are both EUR. This repo has no fetched EUR/USD series;
     converting without one would mean guessing a rate.
  2. **Units.** MIBGAS and the CCGT efficiency figures are EUR per MWh of
     *thermal* fuel input. This series is USD per **tonne** of coal. Getting
     to EUR/MWh(th) needs a calorific value assumption (API2 coal is
     typically quoted around 6,000 kcal/kg NAR, roughly 6.7-7.0 MWh(th)/
     tonne, but this varies by cargo and was not looked up against a cited
     source here) on top of the FX conversion.

Both are ordinary, well-documented conversions -- not another data-
availability problem like CO2 was -- but doing either with an unsourced
constant would put an unverified number in a repo that otherwise cites
every constant it uses (see the CO2 emission factor in
`build_implied_marginal_cost.py`). Left undone on purpose; the next step
for a coal marginal cost is fetching a EUR/USD series and citing a
calorific value, not guessing either here.

COLUMNS

    date          delivery day
    close         settlement price, USD/tonne (what to use)
    open, high, low, volume    the rest of the OHLCV bar, kept for context
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA  # noqa: E402

OUT_DIR = DATA / "investing"
RAW = OUT_DIR / "raw" / "coal_rotterdam_historical.csv"
OUT = OUT_DIR / "coal_price_daily.parquet"


def parse() -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(
            f"\nMissing {RAW}.\n\n"
            "This series has no automated download path -- see the module "
            "docstring, and fetch_eua_carbon_price.py's for the full "
            "explanation. Capture it by hand: open https://www.investing.com/"
            "commodities/rotterdam-coal-futures-historical-data in a real "
            "browser session, widen the date range to cover this repo's "
            "window, and either use the page's own Download button or "
            "replicate the domain-id: www fetch() call documented in "
            f"fetch_eua_carbon_price.py, then save the result to {RAW}.\n"
        )
    df = pd.read_csv(RAW, parse_dates=["date"])
    df = df.sort_values("date").drop_duplicates("date", keep="last").reset_index(drop=True)
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                     help="re-derive coverage facts from the written parquet")
    ap.add_argument("--refresh", action="store_true",
                     help="re-parse the raw CSV even if the output parquet already exists")
    args = ap.parse_args()

    if OUT.exists() and not args.refresh and not args.verify:
        print(f"  {OUT} already exists; pass --refresh to re-parse")
        df = pd.read_parquet(OUT)
    else:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        df = parse()
        df.to_parquet(OUT, index=False)
        print(f"  wrote {OUT}")

    print(f"\n{len(df):,} days, {df.date.min().date()} -> {df.date.max().date()}")
    print(f"  close: mean {df.close.mean():.2f} USD/tonne, "
          f"range {df.close.min():.2f}-{df.close.max():.2f}")

    if args.verify:
        dupe = df.duplicated("date").sum()
        assert dupe == 0, "duplicate date rows -- parse is not a key"
        assert df.date.min().year <= 2018, "series should reach back to 2018"
        expected_trading_days = (df.date.max() - df.date.min()).days * 5 / 7
        coverage = len(df) / expected_trading_days
        assert coverage > 0.85, f"trading-day coverage {coverage:.1%} looks too low"
        print(f"  trading-day coverage vs. calendar span: {coverage:.1%}")
        print("\n  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
