#!/usr/bin/env python3
"""Parse the UK ETS allowance (UKA) futures price, captured by hand from investing.com.

    .venv/bin/python scripts/fetch/fetch_uka_carbon_price.py

Reads data/investing/raw/uka_carbon_historical.csv and writes
data/investing/uka_carbon_price_daily.parquet (`date`, `close`, `open`, `high`, `low`, GBP per
tCO2). Like `fetch_eua_carbon_price.py`, it fetches nothing: investing.com refuses scripted
requests, so the file is the page's own "Download" export, saved by a person.

Source: investing.com, "UK Emissions Allowances Energy c1" (the ICE UKA front-month future),
https://www.investing.com/commodities/uk-emissions-allowances-energy-c1-futures-historical-data,
daily. Captured 2026-10-28: 2021-05-20 -> 2026-10-27. The UK ETS replaced the EU ETS for British
plants from 2021-01-01; its first auction was 2021-05-19, so nothing earlier exists. The export
format differs from the EUA file's: quoted fields, US dates (MM/DD/YYYY), a byte-order mark, and
volume as "0.29K".

British plants also pay the **Carbon Price Support**, GBP 18/tCO2 throughout this window; it is
not in this series and has to be added to it.

Exists for the gas-cap design: the carbon cost of British gas plants.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "investing" / "raw" / "uka_carbon_historical.csv"
OUT = ROOT / "data" / "investing" / "uka_carbon_price_daily.parquet"
URL = "https://www.investing.com/commodities/uk-emissions-allowances-energy-c1-futures-historical-data"


def main() -> int:
    if not RAW.exists():
        print(f"Missing {RAW}.\nOpen {URL}, choose Daily and a range from 2021-05-01, press Download "
              f"and save the file there.")
        return 1
    df = pd.read_csv(RAW, encoding="utf-8-sig", thousands=",")
    df = df.rename(columns={"Date": "date", "Price": "close", "Open": "open", "High": "high", "Low": "low"})
    df["date"] = pd.to_datetime(df.date, format="%m/%d/%Y").dt.date
    df = df[["date", "close", "open", "high", "low"]].sort_values("date").reset_index(drop=True)
    assert df.date.is_unique and df.close.between(10, 200).all(), "unexpected values"
    df.to_parquet(OUT, index=False)
    y = df.assign(y=pd.to_datetime(df.date).dt.year).groupby("y").close.agg(["mean", "min", "max", "size"])
    print(f"wrote {OUT}: {len(df)} days {df.date.min()} -> {df.date.max()}\n{y.round(1).to_string()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
