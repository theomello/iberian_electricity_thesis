#!/usr/bin/env python3
"""Leg C panel: the margin rule on synthetic data, then the full panel's invariants.

    .venv/bin/python scripts/qa/check_leg_c_panel.py

Framework spec §4, leg C. Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from leg_c_panel import OUT, at_margin  # noqa: E402

TABLES = ROOT / "outputs/tables"


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    # A: partly dispatched at 22:00 and 23:00 UTC on Jan 31, neighbours cleared, the next one in
    # February. B: across the spring DST change (UTC is continuous), partly at 01:00, not
    # cleared at 02:00. C: partly dispatched, but the unit offered nothing the period before.
    t = pd.to_datetime(["2022-01-31 21:00", "2022-01-31 22:00", "2022-01-31 23:00", "2022-02-01 00:00",
                        "2022-03-27 00:00", "2022-03-27 01:00", "2022-03-27 02:00",
                        "2022-05-01 10:00", "2022-05-01 11:00"], utc=True)
    up = pd.DataFrame({"unit": ["A"] * 4 + ["B"] * 3 + ["C"] * 2, "utc": t, "resolution_min": 60,
                       "offered_mw": [100.0] * 9,
                       "cleared_mw": [100, 50, 60, 100, 100, 40, 0, 50, 100]})
    got = at_margin(up).tolist()
    check(got == [False, True, True, False, False, False, False, False, False],
          f"at_margin: partly dispatched with both UTC neighbours cleared, across month ends ({got})")

    if not OUT.exists():
        check(False, f"{OUT.relative_to(ROOT)} missing -- run scripts/analysis/leg_c_panel.py")
        print(f"{len(fails)} failure(s)")
        return 1
    d = pd.read_parquet(OUT)
    print(f"{len(d):,} unit-periods, {d.unit.nunique()} units, {d.date.min().date()} -> {d.date.max().date()}")
    check(not d.duplicated(["unit", "date", "period"]).any(), "keys unique")
    check(d.date.dt.year.between(2018, 2023).all(), "2018-2023 only")
    check(((d.cleared_mw > 0) & (d.cleared_mw < d.offered_mw)).all(), "every row partly dispatched")
    check(not ((d.firm == "REPSOL") & (d.date < "2018-11-02")).any(), "no REPSOL before 2018-11-02")
    for unit, before, after, when in (("CTJON1", "EDP", "TOTALENERGIES", "2022-02-08"),
                                      ("CTJON3", "EDP", "TOTALENERGIES", "2022-02-08"),
                                      ("PVENT1", "RWE", "NATURGY", "2019-07-18")):
        u = d[d.unit == unit]
        ok = (u.loc[u.date < when, "firm"].isin([before]).all()
              and u.loc[u.date >= when, "firm"].isin([after]).all() and len(u) > 0)
        check(ok, f"{unit}: {before} before {when}, {after} from it ({len(u)} rows)")
    gas, coal = d[d.fuel == "gas"], d[d.fuel == "coal"]
    capped = gas[(gas.c - gas.c_uncapped).abs() > 1e-9]
    check(capped.date.between("2022-06-15", "2023-12-31").all() and len(capped) > 0,
          f"gas cost differs from market cost only 2022-06-15..2023-12-31 ({len(capped):,} rows)")
    check(((coal.c - coal.c_uncapped).abs() < 1e-9).all(), "coal never capped")
    check(((d.fuel_index / d.eff - d.c).abs() < 1e-6).all(), "fuel_index / eff == c")
    check(d[["X", "zw", "zs", "p", "c"]].notna().all().all(), "X, instruments, price and cost present")
    cost = pd.read_parquet(ROOT / "data/jrc_ppdb/implied_marginal_cost_daily.parquet", columns=["unit", "date"])
    cost = cost[cost.date.between("2018-01-02", "2023-12-31")]
    per_unit = cost.groupby("unit").date.nunique()
    days = len(pd.date_range("2018-01-02", "2023-12-31"))
    check((per_unit >= days - 3).all(), f"the cost file covers every calendar day, weekends included "
          f"(fewest days for a unit: {per_unit.min()} of {days})")
    check(d.date.dt.dayofweek.isin([5, 6]).any(), "weekend periods present in the panel")
    check(((d.zw >= 0) & (d.zs >= 0)).all(), "rivals' offered renewables non-negative")
    rw = pd.read_parquet(TABLES / "rival_wind.parquet", columns=["date", "period", "z_rival_EDP"])
    rw["date"] = pd.to_datetime(rw.date).astype("datetime64[us]")
    m = d[d.firm == "EDP"].assign(date=d.date.astype("datetime64[us]")).merge(rw, on=["date", "period"])
    check(len(m) > 0 and np.allclose(m.zw, m.z_rival_EDP / 1000), "EDP rows carry EDP's rivals' wind, in GW")
    print("rows by year and fuel:\n", d.groupby([d.date.dt.year, "fuel"]).size().unstack(fill_value=0))
    print("rows by firm:", d.firm.value_counts().to_dict())
    print(f"plant-specific efficiency: {(~d.eff_is_generic).mean():.3f}; declaring a variable term: "
          f"{(d.var_term > 0).mean():.3f}")
    print("OK" if not fails else f"{len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
