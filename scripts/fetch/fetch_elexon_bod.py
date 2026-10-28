#!/usr/bin/env python3
"""Fetch Great Britain's balancing-mechanism offers (BOD) and physical notifications (PN) per unit.

    .venv/bin/python scripts/fetch/fetch_elexon_bod.py [--start 2021-06-01] [--end 2023-07-01]
        [--fuels CCGT COAL] [--verify]

Writes, per BM unit, data/elexon/{bod,pn}/parquet/<unit>.parquet, and keeps every 7-day answer as
served (gzipped JSON) in data/elexon/raw/{bod,pn}/<unit>/<YYYYMMDD>.json.gz. A chunk already on disk
is never requested again, empty answers included (a unit not yet built or already closed).

Source: Elexon's Insights API (BMRS), free, no key, https://data.elexon.co.uk/bmrs/api/v1:
`/balancing/bid-offer` (dataset BOD) and `/balancing/physical?dataset=PN`, at most 7 days per unit
per request. The unit register is `/reference/bmunits/all`, a snapshot with `fuelType`; it is
saved as data/elexon/bmunits_<fetch date>.parquet. Units are named as National Grid names them
(`PEMB-11`), which is JRC-PPDB-OPEN's `name_g` for British units, so efficiencies join exactly.

What the two datasets are. Great Britain has no day-ahead pool: generators sell bilaterally and on
the power exchanges, then tell the system operator what they will generate (the **final physical
notification**, FPN, a MW level per half-hour settlement period). The balancing mechanism is the
system operator buying deviations from it: each unit submits up to ten pairs per period, each a MW
band relative to its FPN (`pairId` > 0 above, < 0 below) with an **offer** (GBP/MWh to raise output)
and a **bid** (GBP/MWh to lower it; negative bids pay to keep running). So BOD prices output
*above or below the plant's own schedule*, not a day-ahead supply offer. That is the main
difference from OMIE's and GME's offers, and why this is a weak control on its own.

Rows: BOD `settlementDate, settlementPeriod, timeFrom, timeTo, levelFrom, levelTo, bid, offer,
pairId, bmUnit, nationalGridBmUnit`; PN the same without the prices and pair. Times are UTC;
settlement dates are UK local, 48 periods a day (46 and 50 on clock-change days). Chunks overlap
by one period at each end (the API is inclusive), so rows are de-duplicated on parse.

Exists for the gas-cap design: British gas plants, uncapped and not coupled to Iberia, as a second
comparison besides Italy.
"""
from __future__ import annotations

import argparse
import gzip
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
BASE = ROOT / "data" / "elexon"
API = "https://data.elexon.co.uk/bmrs/api/v1"
DATASETS = {"bod": ("/balancing/bid-offer", {}),
            "pn": ("/balancing/physical", {"dataset": "PN"})}
KEYS = {"bod": ["bmUnit", "timeFrom", "pairId"], "pn": ["bmUnit", "timeFrom"]}
PAUSE = 0.3


def session() -> requests.Session:
    s = requests.Session()
    s.headers["User-Agent"] = "research (LMU Munich)"
    return s


def register(s: requests.Session) -> pd.DataFrame:
    r = s.get(f"{API}/reference/bmunits/all", timeout=120)
    r.raise_for_status()
    df = pd.DataFrame(r.json())
    BASE.mkdir(parents=True, exist_ok=True)
    df.to_parquet(BASE / f"bmunits_{date.today():%Y%m%d}.parquet", index=False)
    return df


def get(s: requests.Session, path: str, params: dict) -> list | None:
    for attempt in range(5):
        try:
            r = s.get(API + path, params=params, timeout=120)
        except requests.RequestException as e:
            print(f"    {e!r}, retrying")
            time.sleep(10 * (attempt + 1))
            continue
        if r.status_code == 200:
            return r.json()["data"]
        if r.status_code in (429, 500, 502, 503, 504):
            time.sleep(10 * (attempt + 1))
            continue
        print(f"    HTTP {r.status_code}: {r.text[:200]!r}")
        return None
    return None


def fetch_unit(s: requests.Session, unit: str, kind: str, start: date, end: date) -> int:
    path, extra = DATASETS[kind]
    d, new = start, 0
    while d < end:
        p = BASE / "raw" / kind / unit / f"{d:%Y%m%d}.json.gz"
        if not p.exists():
            to = min(d + timedelta(7), end)
            data = get(s, path, {"bmUnit": unit, "from": f"{d}T00:00Z", "to": f"{to}T00:00Z", **extra})
            if data is None:
                return -1
            p.parent.mkdir(parents=True, exist_ok=True)
            with gzip.open(p, "wt") as f:
                json.dump(data, f)
            new += 1
            time.sleep(PAUSE)
        d += timedelta(7)
    return new


def parse_unit(unit: str, kind: str) -> pd.DataFrame:
    rows = []
    for p in sorted((BASE / "raw" / kind / unit).glob("*.json.gz")):
        with gzip.open(p, "rt") as f:
            rows += json.load(f)
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop(columns=[c for c in ("dataset",) if c in df])
    df["timeFrom"] = pd.to_datetime(df.timeFrom, utc=True)
    df["timeTo"] = pd.to_datetime(df.timeTo, utc=True)
    df["settlementDate"] = pd.to_datetime(df.settlementDate).dt.date
    df = df.drop_duplicates(KEYS[kind]).sort_values(KEYS[kind]).reset_index(drop=True)
    out = BASE / kind / "parquet" / f"{unit}.parquet"
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out, index=False)
    return df


def verify(units: list[str], start: date, end: date) -> int:
    """PN must cover every settlement period, with no repeated segment; report day coverage.

    A period can hold several PN segments (a ramp is notified as points within the half-hour),
    so the duplicate test is on the segment start, not on the period."""
    bad = 0
    for u in units:
        p = BASE / "pn" / "parquet" / f"{u}.parquet"
        if not p.exists():
            print(f"  {u:12s} no PN (not running in the window)")
            continue
        pn = pd.read_parquet(p)
        pn = pn[(pn.settlementDate >= start) & (pn.settlementDate < end)]
        per = pn.groupby("settlementDate").settlementPeriod.nunique()
        odd = per[~per.isin([46, 48, 50])]
        dup = pn.duplicated(["timeFrom"]).sum()
        bp = BASE / "bod" / "parquet" / f"{u}.parquet"
        nb = len(pd.read_parquet(bp)) if bp.exists() else 0
        flag = "" if dup == 0 else "  <-- CHECK"
        bad += bool(flag)
        print(f"  {u:12s} PN days {len(per):4d}  part days {len(odd):3d}  dup segments {dup:3d}"
              f"  BOD rows {nb:7d}{flag}")
    return bad


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2021-06-01")
    ap.add_argument("--end", default="2023-07-01", help="exclusive")
    ap.add_argument("--fuels", nargs="+", default=["CCGT", "COAL"])
    ap.add_argument("--units", nargs="*", help="override: these Elexon unit ids (T_PEMB-11)")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    start, end = date.fromisoformat(a.start), date.fromisoformat(a.end)
    s = session()
    reg = register(s)
    units = a.units or sorted(reg[reg.fuelType.isin(a.fuels)].elexonBmUnit.dropna())
    print(f"{len(units)} units ({', '.join(a.fuels)}), {start} -> {end}")
    if a.verify:
        return 1 if verify(units, start, end) else 0
    for i, u in enumerate(units, 1):
        for kind in DATASETS:
            n = fetch_unit(s, u, kind, start, end)
            if n < 0:
                print(f"  {u} {kind}: failed, stopping")
                return 1
            df = parse_unit(u, kind)
            print(f"  [{i}/{len(units)}] {u} {kind}: {n} new chunks, {len(df)} rows", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
