#!/usr/bin/env python3
"""The cogeneration unit-day panel: keys, coverage, and the monthly totals pinned in the design spec.

    .venv/bin/python scripts/qa/check_cogeneration_panel.py

Checks outputs/tables/cogeneration_panel/ (built by `build/build_cogeneration_panel.py`) against
docs/specs/2026-11-10-cogeneration-design.md §1: mean scheduled MW of non-renewable units existing before June 2022
(3,549 in 2022-03, 1,386 in 2022-09) and of renewable thermal units (599, 557), each within 2%. Also: unique
(date, unit); all 60 months; load factor within capacity; no load factor without a capacity; cleared <= offered;
energy within capacity x 25 hours on the two clock-change days of 2022. Exits non-zero on any failure.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DIR = ROOT / "outputs" / "tables" / "cogeneration_panel"
REG = ROOT / "data" / "omie" / "registry" / "cogeneration_units.parquet"
fails: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'ok  ' if ok else 'FAIL'} {name} {detail}")
    if not ok:
        fails.append(name)


def main() -> int:
    files = sorted(glob.glob(str(DIR / "panel_*.parquet")))
    months = {Path(f).stem[-6:] for f in files}
    want = {p.strftime("%Y%m") for p in pd.period_range("2019-01", "2023-12", freq="M")}
    check("all 60 months present", months == want, f"({len(months)})")
    if not files:
        return 1
    p = pd.concat(pd.read_parquet(f) for f in files)
    reg = pd.read_parquet(REG)[["unit", "label", "new_after_cap"]]
    p = p.merge(reg, on="unit")
    check("(date, unit) unique", not p.duplicated(["date", "unit"]).any(), f"({len(p):,} rows)")

    def mean_mw(ym: str, mask) -> float:
        m = p[p.date.str.startswith(ym) & mask]
        return m.energy_mwh.sum() / m.groupby("date").hours.first().sum()

    old_non = (p.label == "nonren") & ~p.new_after_cap
    for ym, mask, want_mw, name in [("2022-03", old_non, 3549, "non-renewable, earlier units"),
                                    ("2022-09", old_non, 1386, "non-renewable, earlier units"),
                                    ("2022-03", p.label == "renew", 599, "renewable thermal"),
                                    ("2022-09", p.label == "renew", 557, "renewable thermal")]:
        got = mean_mw(ym, mask)
        check(f"{name} {ym}: {want_mw:,} MW +/- 2%", abs(got / want_mw - 1) <= 0.02, f"({got:,.0f})")

    lf = p.load_factor.dropna()
    check("load factor <= 1.05 on 99% of rows", (lf <= 1.05).mean() >= 0.99, f"({(lf <= 1.05).mean():.2%})")
    nocap = p[~(p.max_power_mw > 0)]
    check("no load factor without a capacity", nocap.load_factor.isna().all(), f"({len(nocap):,} rows without)")
    check("cleared <= offered", (p.cleared_mwh <= p.offered_mwh + 0.01).all(),
          f"({(p.cleared_mwh > p.offered_mwh + 0.01).sum()} rows above)")
    dst = p[p.date.isin(["2022-03-27", "2022-10-30"])]
    check("clock-change days: 23 and 25 hours", set(dst.groupby("date").hours.first()) == {23.0, 25.0})
    d = dst[dst.max_power_mw > 0]
    check("clock-change days: energy within capacity x 25 h on 99%",
          (d.energy_mwh <= d.max_power_mw * 25 * 1.05).mean() >= 0.99)

    print("\nFAILED: " + ", ".join(fails) if fails else "\nall checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
