#!/usr/bin/env python3
"""The holiday dose by group, day and hour.

    .venv/bin/python scripts/qa/check_holiday_dose.py

Checks `outputs/tables/holiday_dose.parquet` and `holiday_profile.csv`
(`analysis/holiday_first_stage.py --dose`) against step 1's leave-one-year-out
exposures (`holiday_exposure_loyo.csv`):
  - the hourly profile has 24 positive values with mean 1;
  - a day's mean dose equals the exposure from the run that left that day's year out:
    Endesa on the Diada 2024 (Catalonia), Endesa on 2023-10-12 (Spain-only national day,
    all of mainland Spain off: the ES term at share 1), EDP on 2024-04-25 (Portugal),
    Endesa on 2022-09-08 (Asturias and Extremadura, a merged area);
  - zero on a clean weekday (2024-09-18) and on a market-wide holiday (2024-12-25);
  - no dose for the placebo areas: Endesa on 2024-03-01 (Balearic Islands' day) is 0.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
T = ROOT / "outputs" / "tables"


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    prof = pd.read_csv(T / "holiday_profile.csv")
    check(len(prof) == 24 and (prof.p_h > 0).all() and abs(prof.p_h.mean() - 1) < 1e-9,
          f"profile: {len(prof)} hours, min {prof.p_h.min():.2f}, mean {prof.p_h.mean():.3f}")
    dose = pd.read_parquet(T / "holiday_dose.parquet")
    day = dose.groupby(["group", "date"]).dose_mw.mean()
    loyo = pd.read_csv(T / "holiday_exposure_loyo.csv")

    def e(group: str, area: str, year: int) -> float:
        r = loyo[(loyo.group == group) & (loyo.area == area) & (loyo.year_out == year)]
        return float(r.e_mw.iloc[0]) if len(r) else 0.0

    def got(group: str, date: str) -> float:
        return float(day.get((group, pd.Timestamp(date)), 0.0))

    for group, date, area in (("ENDESA", "2024-09-11", "CT"), ("ENDESA", "2023-10-12", "ES"),
                              ("EDP", "2024-04-25", "PT"), ("ENDESA", "2022-09-08", "AS+EX")):
        want, have = e(group, area, int(date[:4])), got(group, date)
        check(abs(have - want) <= 0.5, f"{group} {date} mean dose {have:.1f} = {area} exposure "
                                       f"leaving out {date[:4]} ({want:.1f})")
    for date in ("2024-09-18", "2024-12-25", "2024-03-01"):
        z = dose[dose.date == pd.Timestamp(date)].dose_mw.abs().max() if date != "2024-03-01" \
            else abs(got("ENDESA", date))
        check(z == 0 or pd.isna(z), f"{date}: dose {z}")
    check(not dose.duplicated(["group", "date", "hour"]).any(), "one row per group, date and hour")
    check(dose.hour.between(0, 23).all(), "hours 0-23")

    print(f"\n{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
