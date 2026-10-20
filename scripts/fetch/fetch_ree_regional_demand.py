#!/usr/bin/env python3
"""Fetch REE's monthly electricity demand by autonomous community (REData, token-free).

    .venv/bin/python scripts/fetch/fetch_ree_regional_demand.py [--start 2018 --end 2026]
    .venv/bin/python scripts/fetch/fetch_ree_regional_demand.py --verify

Source
------
REData `demanda/evolucion`, `time_trunc=month`, `geo_trunc=electric_system`,
`geo_limit=ccaa`, one request per area and year, cached as returned in
`data/ree/raw/ccaa/<area>_<year>.json`. **Monthly is the finest regional
resolution**: the same request at `time_trunc=day` or `hour` answers HTTP 400 ("not
available"), and `balance/balance-electrico` by region returns one aggregate value
(checked 2026-10-20). REData now and then answers 400/502 to a valid request;
the fetcher retries.

The geo ids are not documented on REE's page; they were identified on 2026-10-20 from
2023 totals (Cataluña 44.4 TWh, Andalucía 38.7, Madrid 27.3, Valencia 26.6, La Rioja
1.5, Ceuta 0.2), and `--verify` checks them: the 15 mainland regions must sum to the
peninsular total (`geo_limit=peninsular`, id 8741) within 2% in every year.

Output
------
data/ree/ree_demand_ccaa_monthly.parquet: month (first day), area (ISO 3166-2:ES code,
as `lib/holidays.py`), demand_mwh. Used for the size check of the regional-holiday
exposures (`build/build_holiday_exposure.py`).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from holidays import ES_MAINLAND  # noqa: E402

RAW = ROOT / "data" / "ree" / "raw" / "ccaa"
OUT = ROOT / "data" / "ree" / "ree_demand_ccaa_monthly.parquet"
URL = ("https://apidatos.ree.es/es/datos/demanda/evolucion?start_date={y}-01-01T00:00"
       "&end_date={y}-12-31T23:59&time_trunc=month&geo_trunc=electric_system"
       "&geo_limit={limit}&geo_ids={gid}")
GEO = {"AN": 4, "AR": 5, "CB": 6, "CM": 7, "CL": 8, "CT": 9, "PV": 10, "AS": 11, "MD": 13,
       "NC": 14, "VC": 15, "EX": 16, "GA": 17, "RI": 20, "MC": 21,
       "CN": 8742, "IB": 8743, "CE": 8744, "ML": 8745}
PENINSULAR = ("ES_PEN", "peninsular", 8741)


def fetch(area: str, limit: str, gid: int, year: int) -> Path:
    path = RAW / f"{area}_{year}.json"
    complete = year < pd.Timestamp.today().year
    if path.exists() and complete:
        return path
    for attempt in range(5):
        r = requests.get(URL.format(y=year, limit=limit, gid=gid), timeout=60)
        if r.ok and "included" in r.text:
            RAW.mkdir(parents=True, exist_ok=True)
            path.write_text(r.text, encoding="utf-8")
            time.sleep(1)
            return path
        time.sleep(5 * (attempt + 1))
    raise SystemExit(f"{area} {year}: REData answered {r.status_code} {r.text[:120]}")


def parse(path: Path, area: str) -> pd.DataFrame:
    d = json.loads(path.read_text(encoding="utf-8"))
    series = [s for s in d["included"] if s["attributes"]["title"] == "Demanda"]
    if len(series) != 1:
        raise SystemExit(f"{path.name}: {len(series)} 'Demanda' series")
    v = series[0]["attributes"]["values"]
    month = pd.to_datetime([x["datetime"][:10] for x in v])
    return pd.DataFrame({"month": month, "area": area, "demand_mwh": [x["value"] for x in v]})


def build(years: range) -> pd.DataFrame:
    parts = []
    for year in years:
        for area, gid in GEO.items():
            parts.append(parse(fetch(area, "ccaa", gid, year), area))
        parts.append(parse(fetch(PENINSULAR[0], PENINSULAR[1], PENINSULAR[2], year), PENINSULAR[0]))
    df = pd.concat(parts, ignore_index=True)
    df["month"] = df.month.astype("datetime64[ns]")
    if df.duplicated(["month", "area"]).any():
        raise SystemExit("duplicate month-area rows")
    return df


def verify(df: pd.DataFrame) -> int:
    """Compare on months every mainland region and the peninsula have: regions are
    published later (2026: to August, the peninsula to October)."""
    wide = df.pivot(index="month", columns="area", values="demand_mwh")
    common = wide.index[wide[list(ES_MAINLAND) + [PENINSULAR[0]]].notna().all(axis=1)]
    y = df[df.month.isin(common)].assign(year=lambda x: x.month.dt.year)
    pen = y[y.area == PENINSULAR[0]].groupby("year").demand_mwh.sum()
    reg = y[y.area.isin(ES_MAINLAND)].groupby("year").demand_mwh.sum()
    n = y[y.area.isin(ES_MAINLAND)].groupby("year").area.nunique()
    gap = (reg / pen - 1) * 100
    print(pd.DataFrame({"mainland_regions_TWh": reg / 1e6, "peninsular_TWh": pen / 1e6,
                        "gap_pct": gap, "regions": n}).round(2))
    # The current year's regional months are provisional and need not add up: on
    # 2026-10-20, January-August 2026 summed 5.8% above the peninsula. Only closed
    # years must match.
    closed = gap.index < pd.Timestamp.today().year
    bad = (gap.abs().gt(2) | n.ne(len(ES_MAINLAND))) & closed
    if (~closed).any():
        print(f"note: {list(gap.index[~closed])} provisional, not checked")
    print("verify:", "FAIL" if bad.any() else "ok")
    return 1 if bad.any() else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=2018)
    ap.add_argument("--end", type=int, default=2026)
    ap.add_argument("--verify", action="store_true", help="check the stored file only")
    a = ap.parse_args()
    if a.verify:
        if not OUT.exists():
            print(f"verify: FAIL, {OUT.relative_to(ROOT)} missing")
            return 1
        return verify(pd.read_parquet(OUT))
    df = build(range(a.start, a.end + 1))
    OUT.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(df):,} rows, {df.month.min():%Y-%m} -> {df.month.max():%Y-%m}")
    return verify(df)


if __name__ == "__main__":
    sys.exit(main())
