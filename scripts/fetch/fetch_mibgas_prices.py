#!/usr/bin/env python3
"""Fetch MIBGAS Iberian natural gas prices.

    .venv/bin/python scripts/fetch/fetch_mibgas_prices.py
    .venv/bin/python scripts/fetch/fetch_mibgas_prices.py --year 2021

Writes data/mibgas/mibgas_prices.parquet (one row per trading day and product).

WHY THIS EXISTS

The 2021 Spanish clawback on non-emitting generation (RDL 17/2021) sets the levy
per installation i in month t as

    Y_it = Q_it * FMIG_t * (PGN_t - 20) * alpha,     alpha = 0.9

where `PGN_t` is the **monthly average natural gas price at the Iberian virtual
balancing point (PVB)** and the levy is zero if that average falls below
20 EUR/MWh. `Q_it` is energy actually produced, so this is a **per-MWh output
levy whose rate varies month to month with the gas price** -- not a lump sum.

That is what makes a continuous treatment-intensity design possible: rather than
one before/after break in September 2021, treatment intensity varies over the
27 months the levy ran, and the interaction of that intensity with Spanish
(treated) versus Portuguese (untreated) hydro identifies the response.

`GDAES_D+1` at `PVB`, area `ES`, is the series the formula refers to. Monthly
means of it reconstruct `PGN_t` directly.

FMIG -- the factor measuring how much of the day-ahead electricity price is
attributable to gas -- is NOT published in a machine-readable form found so far;
REE publishes only PDFs. Two options, in order of preference: take it from those
PDFs, or estimate it from this repo's own marginal-technology series, which
measures the same object (the share of periods where gas sets the price) from
bid microdata. Do not silently substitute one for the other.

SOURCE AND FORMAT

`mibgas.es`, token-free. One CSV per year at

    /en/file-access/MIBGAS_Data_YYYY.csv?path=AGNO_YYYY/XLS

**The first line is a publication timestamp, not a header** -- skip it or every
column is mislabelled. Semicolon-separated, **comma decimal**, latin-1. Dates
are `DD/MM/YYYY`.

Products include daily (`GDAES_D+1`), monthly (`GMAES`), quarterly (`GQES_Q+1`)
and further forward gas contracts; all are kept, since the forward gas curve is
itself an input to a water-value model. Filter on `product` when reconstructing
PGN -- mixing daily and forward products would bias the monthly mean.
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA, END, START, session  # noqa: E402

OUT = DATA / "mibgas"
URL = "https://www.mibgas.es/en/file-access/MIBGAS_Data_{y}.csv"

SCHEMA = pa.schema([
    ("trading_day", pa.date32()),
    ("product", pa.string()),
    ("place_of_delivery", pa.string()),
    ("area", pa.string()),
    ("first_delivery", pa.date32()),
    ("last_delivery", pa.date32()),
    ("price_eur_mwh", pa.float64()),
])


def fetch_year(sess, year: int) -> pd.DataFrame | None:
    r = sess.get(URL.format(y=year), params={"path": f"AGNO_{year}/XLS"},
                 timeout=300)
    if r.status_code != 200 or not r.content:
        return None
    txt = r.content.decode("latin-1")
    # First line is "Fecha Emision : ...", not a header. skiprows=1 is load-bearing.
    df = pd.read_csv(io.StringIO(txt), sep=";", decimal=",", skiprows=1,
                     dtype=str, engine="python")
    df.columns = [c.strip().strip('"') for c in df.columns]
    keep = {
        "Trading day": "trading_day", "Product": "product",
        "Place of delivery": "place_of_delivery", "Area": "area",
        "First Day Delivery": "first_delivery",
        "Last Day Delivery": "last_delivery",
    }
    price_col = next((c for c in df.columns if "Price" in c), None)
    if price_col is None:
        return None
    df = df.rename(columns={**keep, price_col: "price_eur_mwh"})
    cols = [c for c in SCHEMA.names if c in df.columns]
    df = df[cols].copy()
    for c in ("trading_day", "first_delivery", "last_delivery"):
        if c in df:
            df[c] = pd.to_datetime(df[c], format="%d/%m/%Y",
                                   errors="coerce").dt.date
    df["price_eur_mwh"] = pd.to_numeric(
        df.price_eur_mwh.astype(str).str.replace(",", ".", regex=False),
        errors="coerce")
    return df.dropna(subset=["trading_day", "price_eur_mwh"])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int)
    args = ap.parse_args()
    sess = session()
    years = [args.year] if args.year else range(START.year, END.year + 1)
    frames = []
    for y in years:
        df = fetch_year(sess, y)
        if df is None or df.empty:
            print(f"  {y}  NO DATA")
            continue
        frames.append(df)
        d = df[df["product"].eq("GDAES_D+1")] if "product" in df else df
        print(f"  {y}  {len(df):,} rows   daily-product mean "
              f"{d.price_eur_mwh.mean():7.2f} EUR/MWh")
    if not frames:
        return 1
    out = pd.concat(frames, ignore_index=True)
    OUT.mkdir(parents=True, exist_ok=True)
    tbl = pa.Table.from_pandas(out[list(SCHEMA.names)], schema=SCHEMA,
                               preserve_index=False)
    pq.write_table(tbl, OUT / "mibgas_prices.parquet", compression="zstd")
    print(f"\n{tbl.num_rows:,} rows in {OUT / 'mibgas_prices.parquet'}")
    daily = out[out["product"].eq("GDAES_D+1")].copy()
    daily["m"] = pd.to_datetime(daily.trading_day).dt.to_period("M")
    pgn = daily.groupby("m").price_eur_mwh.mean()
    live = pgn[(pgn.index >= "2021-09") & (pgn.index <= "2023-12")]
    print(f"\nPGN monthly mean over the levy window: min {live.min():.1f}, "
          f"max {live.max():.1f}, months below the 20 EUR floor: "
          f"{(live < 20).sum()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
