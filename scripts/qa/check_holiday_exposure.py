#!/usr/bin/env python3
"""The retail day panel behind the regional-holiday exposures.

    .venv/bin/python scripts/qa/check_holiday_exposure.py

Checks `outputs/tables/holiday_retail_days.parquet` (`build/build_holiday_exposure.py`):
  - the Diada 2024 (11 September): Endesa's retail schedule, auction plus bilateral,
    is 457 MW below the mean of 4 and 18 September, and all free-market retail units' 623 MW
    (both from PDBF with a throwaway query on 2026-10-20, before the builder existed);
  - one row per group and day;
  - DST days divide by the hours in the local day: 23 on 2024-03-31, 25 on
    2024-10-27, and each is within 5% of the neighbouring Sundays;
  - a weekday in the 15-minute era (2025-06-11) reads 20-35 GW for all retail
    units, so a quarter-hour row is not read as MWh per hour.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "outputs" / "tables" / "holiday_retail_days.parquet"


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    p = pd.read_parquet(PANEL)
    row = p.set_index(["group", "date"])

    e = row.loc[("ENDESA", pd.Timestamp("2024-09-11"))]
    check(e.ref_dates == "2024-09-04,2024-09-18", f"Endesa Diada references {e.ref_dates}")
    check(abs(e.delta_mw + 457) <= 2, f"Endesa Diada delta {e.delta_mw:.1f} MW (expect -457 +/- 2)")
    # ALL also holds the regulated pass-through suppliers (PASS); the -623 was measured
    # on the free-market retail units alone, which are ALL less PASS.
    d = pd.Timestamp("2024-09-11")
    free = row.loc[("ALL", d)].delta_mw - row.loc[("PASS", d)].delta_mw
    check(abs(free + 623) <= 3, f"free-market retail Diada delta {free:.1f} MW (expect -623 +/- 3)")
    check(row.loc[("PASS", d)].delta_mw < 0, f"pass-through suppliers buy less on the Diada "
                                              f"({row.loc[('PASS', d)].delta_mw:.1f} MW)")
    check(not p.duplicated(["group", "date"]).any(), "one row per group and day")

    al = row.xs("ALL", level="group")
    for day, h in (("2024-03-31", 23), ("2024-10-27", 25)):
        d = pd.Timestamp(day)
        near = al.loc[[d - pd.Timedelta(days=7), d + pd.Timedelta(days=7)], "retail_mw"].mean()
        check(al.loc[d, "hours"] == h, f"{day} divided by {al.loc[d, 'hours']} hours (expect {h})")
        check(abs(al.loc[d, "retail_mw"] / near - 1) < 0.05,
              f"{day} retail {al.loc[d, 'retail_mw']:.0f} MW vs neighbouring Sundays {near:.0f}")
    q = al.loc[pd.Timestamp("2025-06-11"), "retail_mw"]
    check(20_000 <= q <= 35_000, f"2025-06-11 all retail {q:.0f} MW (expect 20-35 GW)")

    print(f"\n{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
