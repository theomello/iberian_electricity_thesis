#!/usr/bin/env python3
"""The holiday table: known dates, counts, and the area x day indicators.

    .venv/bin/python scripts/qa/check_holidays.py

Checks `data/holidays/holidays_es_pt.parquet` (built by
`fetch/fetch_holidays.py`) and `lib/holidays.py` against dates read off the
BOE resolutions and Portugal's Código do Trabalho (art. 234):
  - 2019: Día de Andalucía (28 Feb), San José (19 Mar) in five regions and not
    Cataluña, Holy Thursday everywhere but Cataluña and Valencia, the Monday
    after Epiphany (7 Jan) in Andalucía and not Cataluña;
  - the Diada (11 Sep) in Cataluña in every year it falls on a weekday;
  - Portugal's 25 April and 10 June every year, Corpus Christi 2019-06-20;
  - Good Friday holiday in every MIBEL area every year;
  - 12 to 14 rows per Spanish area and year;
  - `unshared` is zero on market-wide days; `bridges` flags 2019-03-18 in
    Valencia (the Monday before San José).
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from dateutil.easter import easter

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from holidays import AREAS, ES_MAINLAND, MIBEL, bridges, load, market_wide, unshared  # noqa: E402

YEARS = range(2018, 2027)


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    h = load()
    on = {(d, a) for d, a in zip(h.date, h.area)}

    def has(day: str, area: str) -> bool:
        return (pd.Timestamp(day), area) in on

    spanish = [a for a in AREAS if a != "PT"]
    check(set(AREAS) == set(h.area.unique()), f"all {len(AREAS)} areas present")
    check(has("2019-02-28", "AN") and h[(h.date == "2019-02-28") & (h.area == "AN")].mark.iloc[0] == "regional",
          "2019-02-28 Andalucía, regional")
    check(all(has("2019-03-19", a) for a in ("VC", "GA", "MC", "NC", "PV")) and not has("2019-03-19", "CT"),
          "2019-03-19 San José in VC GA MC NC PV, not CT")
    check(all(has("2019-04-18", a) == (a not in ("CT", "VC")) for a in spanish),
          "2019-04-18 Holy Thursday in every Spanish area but CT and VC")
    check(has("2019-01-07", "AN") and not has("2019-01-07", "CT"), "2019-01-07 in AN, not CT")
    diada = [pd.Timestamp(f"{y}-09-11") for y in YEARS]
    check(all(has(d, "CT") for d in diada if d.dayofweek < 5), "Diada in CT every weekday year")
    check(all(has(f"{y}-04-25", "PT") and has(f"{y}-06-10", "PT") for y in YEARS), "PT 25 Apr and 10 Jun every year")
    check(has("2019-06-20", "PT"), "PT Corpus Christi 2019-06-20")
    gf = [pd.Timestamp(easter(y)) - pd.Timedelta(days=2) for y in YEARS]
    check(all(has(d, a) for d in gf for a in MIBEL), "Good Friday in every MIBEL area every year")
    n = h[h.area != "PT"].assign(year=h.date.dt.year).groupby(["area", "year"]).size()
    # The Canary Islands list 11: the twelfth is each island's own day, in the footnotes.
    cn = n.xs("CN", level="area")
    rest = n.drop("CN", level="area")
    check(rest.between(12, 14).all(), f"12-14 rows per Spanish area-year but CN (range {rest.min()}-{rest.max()})")
    check(cn.eq(11).all(), "CN 11 rows a year (island days in footnotes, left out)")

    days = pd.date_range("2018-01-01", "2026-12-31")
    mw, un, br = market_wide(days), unshared(days), bridges(days)
    check(list(un.columns) == list(AREAS) and list(br.columns) == list(AREAS), "indicator columns are AREAS")
    check(un[mw.to_numpy()].to_numpy().sum() == 0, "unshared is 0 on market-wide days")
    check(bool(mw.loc["2019-04-19"]) and not bool(mw.loc["2019-04-18"]), "Good Friday market-wide, Holy Thursday not")
    check(un.loc["2019-09-11", "CT"] == 1 and un.loc["2019-09-11"].drop("CT").sum() == 0, "Diada 2019 unshared in CT only")
    check(br.loc["2019-03-18", "VC"] == 1 and br.loc["2019-03-18", "CT"] == 0, "2019-03-18 bridge in VC, not CT")
    check(set(ES_MAINLAND) | {"PT"} == set(MIBEL) and len(ES_MAINLAND) == 15, "15 mainland regions plus PT")

    print(f"\n{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
