#!/usr/bin/env python3
"""Fetch Great Britain's daily gas price, the System Average Price (SAP), from the ONS.

    .venv/bin/python scripts/fetch/fetch_ons_gas_sap.py

Writes data/ons/gas_sap_daily.parquet (`gas_day`, `sap_p_kwh`, `sap_gbp_mwh`) and keeps the
workbook as served in data/ons/raw/. The page lists one workbook per edition; the newest covers
2018-01-01 to its publication date, so only that one is read. Re-running fetches it again only
if the page names a newer one.

Source: Office for National Statistics, "System Average Price (SAP) of gas", real-time
indicators, https://www.ons.gov.uk/economy/economicoutputandproductivity/output/datasets/
systemaveragepricesapofgas; data from National Gas Transmission. SAP is the volume-weighted
average of trades on the On-the-Day Commodity Market for gas day D (06:00 to 06:00 UK time), the
British within-day price; NBP day-ahead quotes are not free. Pence per kWh; x10 gives GBP/MWh
(gross calorific). ONS labels it official statistics in development.

**SAP for day D is set during day D**, so an offer made at D-1 can use at most D-2's.

Exists for the gas-cap design: the fuel cost of British gas plants.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "ons" / "raw"
OUT = ROOT / "data" / "ons" / "gas_sap_daily.parquet"
SITE = "https://www.ons.gov.uk"
PAGE = SITE + "/economy/economicoutputandproductivity/output/datasets/systemaveragepricesapofgas"


def main() -> int:
    s = requests.Session()
    s.headers["User-Agent"] = "research (LMU Munich)"
    html = s.get(PAGE, timeout=60).text
    links = re.findall(r'href="(/file\?uri=[^"]+\.xlsx)"', html)
    if not links:
        print("no workbook link on the ONS page")
        return 1
    newest = links[0]
    path = RAW / newest.rsplit("/", 1)[1]
    if not path.exists():
        RAW.mkdir(parents=True, exist_ok=True)
        r = s.get(SITE + newest, timeout=120)
        r.raise_for_status()
        path.write_bytes(r.content)
    raw = pd.read_excel(path, sheet_name="1.Daily SAP Gas", header=None)
    head = raw.index[raw[0].astype(str).eq("Date")][0]
    df = raw.iloc[head + 1:, :2].set_axis(["gas_day", "sap_p_kwh"], axis=1)
    df = df[pd.to_numeric(df.sap_p_kwh, errors="coerce").notna()].copy()
    df["gas_day"] = pd.to_datetime(df.gas_day).dt.date
    df["sap_p_kwh"] = df.sap_p_kwh.astype(float)
    df["sap_gbp_mwh"] = df.sap_p_kwh * 10
    assert df.gas_day.is_unique and df.gas_day.is_monotonic_increasing
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.reset_index(drop=True).to_parquet(OUT, index=False)
    days = pd.date_range(df.gas_day.min(), df.gas_day.max())
    print(f"{path.name}: {len(df)} days {df.gas_day.min()} -> {df.gas_day.max()}, "
          f"{len(days) - len(df)} missing; GBP/MWh mean {df.sap_gbp_mwh.mean():.1f}, "
          f"max {df.sap_gbp_mwh.max():.1f} on {df.gas_day[df.sap_gbp_mwh.idxmax()]}")
    print(df.assign(y=pd.to_datetime(df.gas_day).dt.year).groupby("y").sap_gbp_mwh.mean().round(1).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
