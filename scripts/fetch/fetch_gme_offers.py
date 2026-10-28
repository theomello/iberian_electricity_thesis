#!/usr/bin/env python3
"""Fetch GME's public offers for the Italian day-ahead market (MGP), unit by unit.

    .venv/bin/python scripts/fetch/fetch_gme_offers.py                 # download, then parse
    .venv/bin/python scripts/fetch/fetch_gme_offers.py --start 2021-06-01 --end 2023-06-30
    .venv/bin/python scripts/fetch/fetch_gme_offers.py --parse-only --jobs 4
    .venv/bin/python scripts/fetch/fetch_gme_offers.py --verify

Writes one zip per day to data/gme/raw/YYYYMM/ (as served, never modified) and one parquet
per day to data/gme/offers/parquet/offers_YYYYMMDD.parquet.

Source: GME (Gestore dei Mercati Energetici), MGP download, "Public Domain" /
`OffertePubbliche` (https://gme.mercatoelettrico.org/en-us/Home/Results/Electricity/MGP/Download).
GME keeps offers confidential for seven days after each sitting (DM 29 April 2009), then
publishes every offer and bid: unit code, operator, hour, quantity, price, status, zone.
Field meanings are in GME's legend on that page and in its *Vademecum* of the power exchange.
Access is subject to GME's terms of use, accepted by the user in a browser on 2026-10-28;
the API checks only the cookie that acceptance sets (`GmePolicy_en=true`), no login or token.
One XML per day, ~2.6 MB zipped and ~100 MB unzipped in 2022; the XML is parsed from the zip
and never written out.

Exists for the gas-cap design: Italian gas plants as the control group for Iberian gas
plants' offers around the Iberian exception (RDL 10/2022, from 2022-06-15).

Columns kept, renamed from GME's: `side` (OFF sell / BID buy, GME's PURPOSE_CD), `type`
(REG, ...), `status` (ACC accepted, REJ rejected, PREJ paradoxically rejected, REP replaced,
REV revoked, INC inadequate, SUB submitted), `unit`, `operator`, `period` (INTERVAL_NO,
1..23/24/25 by the Italian, i.e. CET, local day), `date`, `quantity_mwh`, `awarded_mwh`,
`price_eur_mwh` (offered), `awarded_price_eur_mwh`, `merit_order`, `partial`, `zone`,
`grid_point`, `submitted`, `bilateral`, `transaction`. Numbers use a dot decimal.

**REP and REV rows repeat quantities** of a later or withdrawn offer: for a supply curve keep
ACC, REJ and PREJ only (the offered curve, like OMIE's `O`), and ACC alone for cleared volume.
Bilateral positions carry operator "Bilateralista".
"""
from __future__ import annotations

import argparse
import io
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
RAW = ROOT / "data" / "gme" / "raw"
OUT = ROOT / "data" / "gme" / "offers" / "parquet"
API = ("https://gme.mercatoelettrico.org/DesktopModules/GmeDownload/API/ExcelDownload/"
       "downloadzipfile")
HEADERS = {"User-Agent": "Mozilla/5.0 (research; LMU Munich)", "ModuleId": "12103",
           "TabId": "1749"}
COOKIES = {"GmePolicy_en": "true"}
PAUSE_S = 3.0

RENAME = {"PURPOSE_CD": "side", "TYPE_CD": "type", "STATUS_CD": "status",
          "UNIT_REFERENCE_NO": "unit", "OPERATORE": "operator", "INTERVAL_NO": "period",
          "BID_OFFER_DATE_DT": "date", "QUANTITY_NO": "quantity_mwh",
          "AWARDED_QUANTITY_NO": "awarded_mwh", "ENERGY_PRICE_NO": "price_eur_mwh",
          "AWARDED_PRICE_NO": "awarded_price_eur_mwh", "MERIT_ORDER_NO": "merit_order",
          "PARTIAL_QTY_ACCEPTED_IN": "partial", "ZONE_CD": "zone",
          "GRID_SUPPLY_POINT_NO": "grid_point", "SUBMITTED_DT": "submitted",
          "BILATERAL_IN": "bilateral", "TRANSACTION_REFERENCE_NO": "transaction"}
NUMERIC = ["quantity_mwh", "awarded_mwh", "price_eur_mwh", "awarded_price_eur_mwh"]
CATEG = ["side", "type", "status", "unit", "operator", "zone", "grid_point", "partial"]


def raw_path(d: date) -> Path:
    return RAW / f"{d:%Y%m}" / f"{d:%Y%m%d}MGPOffertePubbliche.zip"


def out_path(d: date) -> Path:
    return OUT / f"offers_{d:%Y%m%d}.parquet"


def valid_zip(p: Path) -> bool:
    try:
        with zipfile.ZipFile(p) as z:
            return z.testzip() is None and len(z.namelist()) == 1
    except (zipfile.BadZipFile, OSError):
        return False


def download(d: date, s: requests.Session) -> str:
    p = raw_path(d)
    if p.exists() and valid_zip(p):
        return "kept"
    params = {"DataInizio": "0", "DataFine": "0", "Date": f"{d:%Y%m%d}", "Mercato": "MGP",
              "Settore": "OffertePubbliche", "FiltroDate": "OneData"}
    for attempt in range(3):
        try:
            r = s.get(API, params=params, timeout=300)
        except requests.RequestException as e:
            err = str(e)
        else:
            if r.status_code == 200 and r.headers.get("content-type", "").startswith("application/zip"):
                p.parent.mkdir(parents=True, exist_ok=True)
                tmp = p.with_suffix(".part")
                tmp.write_bytes(r.content)
                if not valid_zip(tmp):
                    tmp.unlink()
                    err = "invalid zip"
                else:
                    tmp.rename(p)
                    return f"{len(r.content) / 1e6:.1f} MB"
            else:
                # A refused terms cookie answers 401 with JSON; a day without data answers
                # with a message, not a zip. Neither is retried past three attempts.
                err = f"HTTP {r.status_code} {r.headers.get('content-type')} {r.text[:120]!r}"
        time.sleep(PAUSE_S * (attempt + 2))
    raise RuntimeError(f"{d}: {err}")


def parse(d: date) -> str:
    p, o = raw_path(d), out_path(d)
    if o.exists():
        return "kept"
    with zipfile.ZipFile(p) as z:
        (name,) = z.namelist()
        rows = []
        with z.open(name) as f:
            for _, el in ET.iterparse(io.BufferedReader(f), events=("end",)):
                if el.tag == "OfferteOperatori":
                    rows.append({c.tag: c.text for c in el})
                    el.clear()
    t = pd.DataFrame(rows)
    missing = set(RENAME) - set(t.columns)
    if missing:
        raise RuntimeError(f"{d}: fields missing {sorted(missing)}")
    t = t[list(RENAME)].rename(columns=RENAME)
    for c in NUMERIC:
        t[c] = pd.to_numeric(t[c]).astype("float64")
    t["period"] = pd.to_numeric(t.period).astype("int8")
    t["merit_order"] = pd.to_numeric(t.merit_order).astype("Int32")
    t["bilateral"] = t.bilateral.eq("true")
    dates = t.date.unique()
    if list(dates) != [f"{d:%Y%m%d}"]:
        raise RuntimeError(f"{d}: file carries dates {list(dates)}")
    t["date"] = pd.Timestamp(d)
    for c in CATEG:
        t[c] = t[c].astype("category")
    OUT.mkdir(parents=True, exist_ok=True)
    tmp = o.with_suffix(".part")
    t.to_parquet(tmp, index=False)
    tmp.rename(o)
    return f"{len(t):,} rows"


def days(start: date, end: date) -> list[date]:
    return [start + timedelta(n) for n in range((end - start).days + 1)]


def verify(ds: list[date]) -> int:
    """Per day: periods match the CET day's length, and accepted buy minus accepted sell
    stays within the coupled borders' reach. The two are NOT equal: imports over the borders
    under market coupling (France, Austria, Slovenia, Greece) clear implicitly and appear in
    no offer, like OMIE's France flow. On 2022-09-15 buy exceeds sell by 4.4 GW at night and
    0.5 GW at midday, Italy's import pattern. Switzerland and Montenegro are explicit zones
    (`SVIZ`, `MONT`) and are inside the offers. A gap beyond +-12 GW flags a broken day."""
    bad = 0
    for d in ds:
        o = out_path(d)
        if not o.exists():
            print(f"{d} missing"); bad += 1; continue
        t = pd.read_parquet(o, columns=["side", "status", "period", "awarded_mwh"])
        n = t.period.nunique()
        expect = len(pd.date_range(pd.Timestamp(d, tz="Europe/Rome"),
                                   pd.Timestamp(d + timedelta(1), tz="Europe/Rome"),
                                   freq="h", inclusive="left"))
        a = t[t.status == "ACC"].groupby(["period", "side"], observed=True).awarded_mwh.sum().unstack()
        g = (a["BID"] - a["OFF"]) if {"OFF", "BID"} <= set(a.columns) else pd.Series([float("nan")])
        flag = n != expect or not g.abs().max() <= 12_000
        bad += flag
        if flag or d.day == 1:
            print(f"{d} periods {n}/{expect} implied coupled imports {g.min():,.0f} .. "
                  f"{g.max():,.0f} MW{'  <-- CHECK' if flag else ''}")
    print(f"{len(ds)} days checked, {bad} flagged")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default="2021-06-01")
    ap.add_argument("--end", default="2023-06-30")
    ap.add_argument("--parse-only", action="store_true")
    ap.add_argument("--download-only", action="store_true")
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    ds = days(date.fromisoformat(a.start), date.fromisoformat(a.end))
    if a.verify:
        return verify(ds)
    if not a.parse_only:
        s = requests.Session()
        s.headers.update(HEADERS)
        s.cookies.update(COOKIES)
        for d in ds:
            had = raw_path(d).exists()
            print(f"{d} download {download(d, s)}", flush=True)
            if not had:
                time.sleep(PAUSE_S)
    if not a.download_only:
        todo = [d for d in ds if not out_path(d).exists()]
        with ProcessPoolExecutor(a.jobs) as ex:
            for d, msg in zip(todo, ex.map(parse, todo)):
                print(f"{d} parse {msg}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
