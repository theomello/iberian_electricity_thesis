#!/usr/bin/env python3
"""Interconnection capacity after the day-ahead market: the parser, coverage, and congestion.

    .venv/bin/python scripts/qa/check_omie_interconnection.py

Checks `fetch/fetch_omie_interconnection.py`:
  - both published formats parse (hourly `Hora` to 2025-09-30, quarter-hour
    `Periodo` = HhQq from 2025-10-01), and an unknown border code fails loudly;
  - every day is present, with 23-25 or 92-100 periods per border, four borders;
  - when the Spanish and Portuguese prices differ, the Spain-Portugal link has no
    free capacity left in one direction (market splitting means congestion).
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "fetch"))
from fetch_omie_interconnection import OUT, parse_text, to_market_resolution  # noqa: E402

PRICES = ROOT / "data/omie/prices/omie_day_ahead_prices.parquet"
HEAD = ("OMIE - Mercado de electricidad;Fecha Emisión :14/01/2024 - 13:29;;15/01/2024;"
        "Capacidad y ocupación de impor/expor casación (MWh B.C.);;;;\r\n\r\n")
COLS = ("Capacidad importación;Ocupación Importación;Capacidad libre de importación;"
        "Capacidad exportación;Ocupación exportación;Capacidad libre de exportación;\r\n")
HOURLY = (HEAD + "Hora;Fecha;Frontera;" + COLS
          + "1;15/01/2024;2;-2.925,0;0;-4.526,6;2.772,0;1.601,6;1.170,4;\r\n"
          + "2;15/01/2024;2;-3.420,0;0;-5.199,6;2.772,0;1.779,6;992,4;\r\n"
          + "1;15/01/2024;3;-2.867,0;-1.000,5;-1.866,5;2.728,0;0;3.728,5;\r\n"
          + ";;;;;;;;;\r\n")
PERIODO_HOURLY = (HEAD + "Periodo;Fecha;Frontera;" + COLS
                  + "1;19/03/2025;2;-3.000,0;0;-3.500,0;2.700,0;500,0;2.200,0;\r\n"
                  + "24;19/03/2025;4;-133,0;0;-133,0;138,8;0;138,8;\r\n")
QUARTER = (HEAD.replace("MWh", "MW") + "Periodo;Fecha;Frontera;" + COLS
           + "H1Q1;10/11/2025;2;-3.690,0;0;-5.354,8;3.330,0;1.664,8;1.665,2;\r\n"
           + "H2Q3;10/11/2025;5;-600,0;0;-914,9;914,4;320,0;594,4;\r\n"
           + ";;;;;;;;;\r\n")


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    h = parse_text(HOURLY)
    check(len(h) == 3 and list(h.border) == ["PT", "PT", "FR"], "hourly: three rows, codes 2 -> PT, 3 -> FR")
    r = h.iloc[0]
    check(r.date == date(2024, 1, 15) and r.period == 1 and r.resolution_min == 60,
          "hourly: date, period from Hora, 60 minutes")
    check((r.import_capacity_mw, r.import_free_mw, r.export_occupied_mw, r.export_free_mw)
          == (-2925.0, -4526.6, 1601.6, 1170.4), "hourly: comma decimals, dot thousands, signs kept")
    check(h.iloc[2].import_occupied_mw == -1000.5, "hourly: import occupation negative as published")
    q = parse_text(QUARTER)
    check(list(q.period) == [1, 7] and set(q.resolution_min) == {15},
          "quarter-hour: H1Q1 -> period 1, H2Q3 -> period 7, 15 minutes")
    check(list(q.border) == ["PT", "MA"], "quarter-hour: code 5 -> MA")
    ph = parse_text(PERIODO_HOURLY)
    check(list(ph.period) == [1, 24] and set(ph.resolution_min) == {60} and list(ph.border) == ["PT", "AD"],
          "Periodo header with integer labels (2025-03-19 on): hourly, code 4 -> AD")
    # A quarter-hour file inside the hourly era (2025-07-15, re-emitted in the new format)
    # holds hourly data with four identical quarters: it must come out hourly.
    rows = "".join(f"H{h}Q{k};15/07/2025;2;-3.000,0;0;-3.000,0;{2700 + h},0;0;{2700 + h},0;\r\n"
                   for h in (1, 2) for k in (1, 2, 3, 4))
    qh = to_market_resolution(parse_text(HEAD.replace("MWh", "MW") + "Periodo;Fecha;Frontera;" + COLS + rows))
    check(list(qh.period) == [1, 2] and set(qh.resolution_min) == {60} and list(qh.export_capacity_mw) == [2701.0, 2702.0],
          "a quarter-hour file before 2025-10-01 collapses to hours")
    try:
        to_market_resolution(parse_text(HEAD.replace("MWh", "MW") + "Periodo;Fecha;Frontera;" + COLS
                                        + rows.replace("H2Q4;15/07/2025;2;-3.000,0;0;-3.000,0;2702,0",
                                                       "H2Q4;15/07/2025;2;-3.000,0;0;-3.000,0;2999,0")))
        check(False, "quarters that differ within an hour raise")
    except ValueError:
        check(True, "quarters that differ within an hour raise")
    try:
        parse_text(HOURLY.replace(";15/01/2024;3;", ";15/01/2024;9;"))
        check(False, "an unknown border code raises")
    except ValueError:
        check(True, "an unknown border code raises")

    if not OUT.exists():
        check(False, f"{OUT.relative_to(ROOT)} missing -- run scripts/fetch/fetch_omie_interconnection.py")
        print(f"{len(fails)} failure(s)")
        return 1
    d = pd.read_parquet(OUT)
    d["date"] = pd.to_datetime(d.date)
    print(f"{len(d):,} rows, {d.date.min().date()} -> {d.date.max().date()}")
    check(not d.duplicated(["date", "period", "border"]).any(), "no duplicate (date, period, border)")
    days = pd.date_range("2018-01-01", d.date.max())
    missing = days.difference(pd.DatetimeIndex(d.date.unique()))
    check(len(missing) == 0, f"every day from 2018-01-01 present (missing {len(missing)}: {list(missing[:5].date)})")
    per_day = d.groupby(["date", "border"]).agg(n=("period", "size"), res=("resolution_min", "first"))
    q15 = per_day.index.get_level_values("date") >= "2025-10-01"
    check(per_day.loc[~q15, "n"].isin([23, 24, 25]).all() and (per_day.loc[~q15, "res"] == 60).all(),
          "before 2025-10-01: 23-25 hourly periods per border")
    check(per_day.loc[q15, "n"].isin([92, 96, 100]).all() and (per_day.loc[q15, "res"] == 15).all(),
          "from 2025-10-01: 92-100 quarter-hour periods per border")
    nb = d.groupby("date").border.nunique()
    check((nb == 4).all(), f"four borders every day (days with fewer: {(nb < 4).sum()})")

    if PRICES.exists():
        p = pd.read_parquet(PRICES, columns=["date", "period", "resolution_min", "price_pt", "price_es"])
        p["date"] = pd.to_datetime(p.date)
        pt = d[d.border == "PT"].merge(p, on=["date", "period", "resolution_min"])
        check(len(pt) == len(p), f"every priced period joins at its own resolution ({len(pt):,} of {len(p):,})")
        split = pt[(pt.price_es - pt.price_pt).abs() > 0.005]
        full = (split.export_free_mw.abs() <= 1.0) | (split.import_free_mw.abs() <= 1.0)
        print(f"split periods: {len(split):,} of {len(pt):,}; Portugal link full in one direction in "
              f"{full.mean():.4f}")
        check(len(split) > 0 and full.mean() >= 0.99, "market splitting means the Portugal link is full")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
