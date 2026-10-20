#!/usr/bin/env python3
"""OMIE's PDVD, the day-ahead schedule after REE's technical constraints.

    .venv/bin/python scripts/qa/check_pdvd.py

Checks `data/omie/pdvd/parquet/` (`fetch/fetch_omie_pdvd.py`):
  - 2019-01-03: Naturgy's Sagunto 1, withdrawn in the auction by its minimum-income
    condition, is scheduled by REE: 24 rows, role 1, mean 51.67 MW, max 155;
    San Roque 1, accepted for 20 hours, averages 235.63 MW over 24 periods;
  - every day of 2019-01 has 24 periods;
  - (date, period, unit, role_code) is a key in every month on disk;
  - months 2019-01 → 2025-03 are all present.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PDVD = ROOT / "data" / "omie" / "pdvd" / "parquet"
KEY = ["date", "period", "unit", "role_code"]


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    want = [p.strftime("%Y%m") for p in pd.period_range("2019-01", "2025-03", freq="M")]
    have = sorted(f.stem.split("_")[1] for f in PDVD.glob("pdvd_*.parquet"))
    missing = sorted(set(want) - set(have))
    check(not missing, f"months 2019-01 → 2025-03 present ({len(missing)} missing: {missing[:5]})")
    if not (PDVD / "pdvd_201901.parquet").exists():
        print(f"FAIL: {len(fails)}")
        return 1

    jan = pd.read_parquet(PDVD / "pdvd_201901.parquet")
    jan["date"] = pd.to_datetime(jan.date)
    d = jan[jan.date == "2019-01-03"]
    s = d[d.unit == "SAGU1"]
    check(len(s) == 24 and set(s.role_code) == {"1"} and abs(s.schedule_mw.mean() - 51.67) < 0.05
          and abs(s.schedule_mw.max() - 155) < 1e-6,
          f"SAGU1 2019-01-03: {len(s)} rows, roles {sorted(set(s.role_code))}, "
          f"mean {s.schedule_mw.mean():.2f}, max {s.schedule_mw.max():.1f}")
    r = d[d.unit == "SROQ1"]
    check(len(r) == 24 and abs(r.schedule_mw.mean() - 235.63) < 0.05,
          f"SROQ1 2019-01-03: {len(r)} rows, mean {r.schedule_mw.mean():.2f}")
    per = jan.groupby("date").period.max()
    check((per == 24).all() and len(per) == 31, f"2019-01: {len(per)} days, periods {sorted(set(per))}")
    check(set(jan.resolution_min.unique()) == {60}, f"2019-01 resolution {sorted(set(jan.resolution_min))}")

    dup = []
    for f in sorted(PDVD.glob("pdvd_*.parquet")):
        m = pd.read_parquet(f, columns=KEY)
        if m.duplicated(KEY).any():
            dup.append(f.stem)
    check(not dup, f"(date, period, unit, role_code) is a key in every month ({len(dup)} not: {dup[:5]})")

    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
