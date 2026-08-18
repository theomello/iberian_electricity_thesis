#!/usr/bin/env python3
"""Parse the daily EUA (EU ETS carbon allowance) price series -- the CO2
term an implied CCGT marginal cost needs and no free bulk-downloadable
source publishes.

    .venv/bin/python scripts/fetch/fetch_eua_carbon_price.py
    .venv/bin/python scripts/fetch/fetch_eua_carbon_price.py --verify

Writes data/investing/eua_carbon_price_daily.parquet from the raw CSV
already captured at data/investing/raw/eua_carbon_emissions_historical.csv.
Unlike every other fetcher in this repo, **this script does not itself
download anything** -- see WHY THE DOWNLOAD STEP IS MANUAL below. If the raw
CSV is missing, it exits with instructions rather than a stack trace.

WHY THIS TOOK EIGHT SOURCES TO FIND

Established 2026-08-18, in this order, before landing on the one that
works:

  * **CBAM Guide's free API** -- real, but a live spot reading only
    (`ets.price`, `ets.date`), no history endpoint.
  * **Sandbag's "Carbon Price Viewer"** -- looks like an interactive
    Plotly chart (the toolbar icons are even in the image). It's a static
    cropped JPEG. Confirmed by inspecting the DOM for `.plotly-graph-div` /
    `.js-plotly-plot` and finding none, and by finding the literal
    `carbon_price_viewer_2026-05-19_cropped.jpg` in the page's network
    requests.
  * **ICAP's Allowance Price Explorer** -- claims downloadable history;
    no static endpoint found from the page.
  * **Ember's API** (`api.ember-energy.org`) -- real, free-with-signup,
    but publishes *carbon intensity* (gCO2/kWh of the grid), not *carbon
    price* (EUR/tCO2). A different quantity entirely; this was wrongly
    recommended once in this project before being checked and withdrawn.
  * **EEX's own market-data widget** (`api.eex-group.com/pub/market-data`)
    -- real EUA primary-auction settlement price, `Environmentals` /
    `Auction` / `EU` / `EUA` in EEX's own "Market Data Hub". But it's a
    free-tier live-price widget: querying `chart/eod` or `table-data` with
    an old `startDate` returns an empty series regardless of the range
    requested -- confirmed by direct request, not assumed. Only a rolling
    ~6-week window is served for free; full history is EEX's paid product.
  * **KRBN** (KraneShares Global Carbon Strategy ETF) via Yahoo Finance's
    public chart API -- works, free, no key, but only from 2020-07-31 (the
    ETF's inception) and is a basket of EUA + California + RGGI allowances,
    not pure EUA.
  * **EU ETS registry data** (EUTL, via datahub.io) -- real and free, but
    it's annual allocation/surrender totals by installation, not a price
    series at any frequency.

**investing.com's own historical-data page** is what actually has it:
ticker `CFI2Z6` ("Carbon Emissions"), the front-month ICE ECX EUA future,
daily back to 2018-01-02.

WHY THE DOWNLOAD STEP IS MANUAL

The page's historical table is server-rendered for only a recent window;
widening the date range and clicking "Apply" fires a request to
`api.investing.com/api/financialdata/historical/{pair_id}` (pair_id 8848
for this instrument) with a required `domain-id: www` header. That part is
straightforward. What isn't: `api.investing.com` sits behind bot protection
that blocks the request outright (HTTP 403) from a plain `requests`/`curl`
client -- confirmed with a full realistic header set (Origin, Referer,
sec-fetch-*, sec-ch-ua, a real Chrome UA string) and it still failed, so
this is TLS/behavioural fingerprinting, not a missing header. It only
succeeds from an authenticated browser session, which is how
`data/investing/raw/eua_carbon_emissions_historical.csv` was captured
(2026-08-18, via `fetch()` from the page's own JS console, `domain-id: www`
added, then saved as a same-origin blob download -- the browser tool's own
text-return channel truncates a payload this size, so extracting it needed
an actual file download rather than a returned string).

**Re-running this script does not refresh the data.** A new pull needs a
human (or a browser-automation session) to repeat that capture and
overwrite the raw CSV. This is the one series in this repo without a
`requests`-only resumable fetch path -- documented here rather than left
implicit, so nobody re-discovers this the hard way.

COLUMNS

    date          delivery day
    close         settlement price, EUR/tCO2 (what to use)
    open, high, low, volume    the rest of the OHLCV bar, kept for context

The window (2018-01-02 -> 2026-08-18) matches this repo's own window almost
exactly -- the raw CSV was pulled with start-date=2017-12-31 for that reason.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA  # noqa: E402

OUT_DIR = DATA / "investing"
RAW = OUT_DIR / "raw" / "eua_carbon_emissions_historical.csv"
OUT = OUT_DIR / "eua_carbon_price_daily.parquet"


def parse() -> pd.DataFrame:
    if not RAW.exists():
        raise SystemExit(
            f"\nMissing {RAW}.\n\n"
            "This series has no automated download path -- see the module "
            "docstring (\"WHY THE DOWNLOAD STEP IS MANUAL\"). Capture it by "
            "hand: open https://www.investing.com/commodities/"
            "carbon-emissions-historical-data in a real browser session, "
            "widen the date range to cover this repo's window, and either "
            "use the page's own Download button or replicate the "
            "domain-id: www fetch() call documented in this script, then "
            f"save the result to {RAW}.\n"
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
    print(f"  close: mean {df.close.mean():.2f} EUR/tCO2, "
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
