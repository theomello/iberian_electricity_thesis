#!/usr/bin/env python3
"""Fetch GME's Italian day-ahead gas prices (MGP-GAS), the PSV spot price for Italian plants.

    .venv/bin/python scripts/fetch/fetch_gme_gas_prices.py [--start 2018-01] [--end 2026-09]

Writes data/gme/gas/gme_mgp_gas_daily.parquet, one row per trading session and product, and
keeps each month's two zips as served in data/gme/gas/raw/ (a month is fetched again only
until it is complete and more than 10 days old).

Source: GME, MGP-GAS download, "Continuous Trading" and "Auction (AGS)", summary of trading
(`SintesiScambio`), https://gme.mercatoelettrico.org/en-us/Home/Results/Gas/MGP-GAS/Download.
MGP-GAS is GME's day-ahead gas market, delivered at the PSV (*Punto di Scambio Virtuale*, the
Italian gas hub); it is the Italian counterpart of MIBGAS's day-ahead index. Same terms of use
and the same cookie as `fetch_gme_offers.py`. Prices in EUR/MWh (gas, gross calorific), dot
decimal, XML.

One row per `session` (trading day) and `product` (`MGP-YYYY-MM-DD`, the gas day delivered):
`gas_day`, `price_mean` (continuous trading, volume-weighted mean, GME's PrezzoMedio), `price_ref`
(GME's reference price, PrezzoControllo, carried also on days with no trade), first, last,
min and max, `volume_mwh`, `matches`, and the auction's `auction_price`, `auction_volume_mwh`
(auction from 2019-12-31). A product trades on more than one session (weekend and holiday
gas days are traded ahead), so (session, product) is the key, not the gas day.

**For an offer for electricity day D (offers close at 12:00 on D-1) use only sessions dated
D-2 or earlier**, as the Spanish `_bid` costs do: session D-1 is still trading at noon.

Exists for the gas-cap design: the cost of Italian gas plants, the control group.
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "gme" / "gas" / "raw"
OUT = ROOT / "data" / "gme" / "gas" / "gme_mgp_gas_daily.parquet"
API = ("https://gme.mercatoelettrico.org/DesktopModules/GmeDownload/API/ExcelDownload/"
       "downloadzipfile")
HEADERS = {"User-Agent": "Mozilla/5.0 (research; LMU Munich)", "ModuleId": "12135",
           "TabId": "1874"}
COOKIES = {"GmePolicy_en": "true"}
MARKETS = {"cont": ("MGPGAS", "negoziazione_continua"), "auction": ("MGPGASASTA", "Asta")}


def months(a: str, b: str) -> list[date]:
    d, end, out = date.fromisoformat(a + "-01"), date.fromisoformat(b + "-01"), []
    while d <= end:
        out.append(d)
        d = (d.replace(day=28) + timedelta(4)).replace(day=1)
    return out


def fetch(m: date, kind: str, s: requests.Session) -> Path | None:
    market, _ = MARKETS[kind]
    p = RAW / f"{m:%Y%m}_{kind}.zip"
    last = (m.replace(day=28) + timedelta(4)).replace(day=1) - timedelta(1)
    final = date.today() - last > timedelta(10)
    if p.exists() and final and p.stat().st_mtime > time.mktime(last.timetuple()) + 10 * 86400:
        return p
    r = s.get(API, params={"DataInizio": f"{m:%Y%m%d}", "DataFine": f"{min(last, date.today()):%Y%m%d}",
                           "Date": f"{m:%Y%m%d}", "Mercato": market, "Settore": "SintesiScambio",
                           "FiltroDate": "InizioFine"}, timeout=120)
    if r.status_code != 200 or not r.headers.get("content-type", "").startswith("application/zip"):
        print(f"  {m:%Y-%m} {kind}: HTTP {r.status_code} {r.text[:80]!r}")
        return None
    RAW.mkdir(parents=True, exist_ok=True)
    p.write_bytes(r.content)
    time.sleep(2)
    return p


def rows(p: Path, tag: str) -> list[dict]:
    out = []
    with zipfile.ZipFile(p) as z:
        for n in z.namelist():
            for _, el in ET.iterparse(io.BytesIO(z.read(n))):
                if el.tag == tag:
                    out.append({c.tag: c.text for c in el})
                    el.clear()
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2018-01")
    ap.add_argument("--end", default=f"{date.today():%Y-%m}")
    a = ap.parse_args()
    s = requests.Session()
    s.headers.update(HEADERS)
    s.cookies.update(COOKIES)
    cont, auc = [], []
    for m in months(a.start, a.end):
        for kind, acc in (("cont", cont), ("auction", auc)):
            p = fetch(m, kind, s)
            if p is not None:
                acc += rows(p, MARKETS[kind][1])
        print(f"{m:%Y-%m} done", flush=True)
    c = pd.DataFrame(cont).rename(columns={
        "DataSessione": "session", "NomeProdotto": "product", "PrezzoMedio": "price_mean",
        "PrezzoControllo": "price_ref", "PrimoPrezzo": "price_first", "UltimoPrezzo": "price_last",
        "PrezzoMassimo": "price_max", "PrezzoMinimo": "price_min", "Volumi": "volume_mwh",
        "PosizioniAperte": "open_positions", "Abbinamenti": "matches"})
    au = pd.DataFrame(auc).rename(columns={"DataSessione": "session", "NomeProdotto": "product",
                                           "Prezzo": "auction_price", "Volumi": "auction_volume_mwh"})
    au = au[["session", "product", "auction_price", "auction_volume_mwh"]] if len(au) else \
        pd.DataFrame(columns=["session", "product", "auction_price", "auction_volume_mwh"])
    t = c.merge(au, on=["session", "product"], how="outer")
    t = t[t["product"].str.match(r"MGP-\d{4}-\d{2}-\d{2}$", na=False)].copy()
    t["gas_day"] = pd.to_datetime(t["product"].str[4:])
    t["session"] = pd.to_datetime(t.session, format="%Y%m%d")
    for col in [x for x in t.columns if x.startswith(("price", "auction", "volume", "open", "matches"))]:
        t[col] = pd.to_numeric(t[col])
    if t.duplicated(["session", "product"]).any():
        raise SystemExit("duplicate (session, product) rows")
    t = t.sort_values(["gas_day", "session"], ignore_index=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    t.to_parquet(OUT, index=False)
    traded = t.dropna(subset=["price_mean"])
    print(f"wrote {OUT}: {len(t):,} rows, gas days {t.gas_day.min():%Y-%m-%d} .. "
          f"{t.gas_day.max():%Y-%m-%d}; traded {traded.gas_day.nunique():,} gas days")
    return 0


if __name__ == "__main__":
    sys.exit(main())
