#!/usr/bin/env python3
"""The hourly panel of the holiday quantity test.

    .venv/bin/python scripts/qa/check_holiday_quantity.py

Checks `outputs/tables/holiday_quantity_panel.parquet` (`analysis/holiday_quantity_test.py --panel`):
  - the panel's daily means, regressed as in `holiday_schedule_legs.py` (each leg's change
    against the step-1 reference days on the daily dose, date and firm × year effects, date
    clusters), give generation sold bilaterally within 2 se of −0.54 and retail bought
    bilaterally within 2 se of +0.69 (step 2's numbers, `holiday_schedule_legs.csv`);
  - the firm's own offer slope s is positive in ≥ 99% of hours priced at or below €5 (where every
    firm offers its renewables), and never above its offered sell MW / 10 (all of it within ±€5);
  - P = dose / slope exactly.
Exits non-zero on any failure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
for s in ("lib", "analysis", "build"):
    sys.path.insert(0, str(ROOT / "scripts" / s))
from build_holiday_exposure import add_deltas  # noqa: E402
from midday_hydro_iv import cluster_meat  # noqa: E402
from step_estimator import wdemean  # noqa: E402

PANEL = ROOT / "outputs/tables/holiday_quantity_panel.parquet"
LEGS = ROOT / "outputs/tables/holiday_schedule_legs.csv"


def daily_leg(p: pd.DataFrame, leg: str) -> tuple[float, float]:
    d = p.groupby(["group", "date"]).agg(retail_mw=(leg, "mean"), dose=("dose_mw", "mean")).reset_index()
    d = add_deltas(d)
    d = d[d.delta_mw.notna()]
    codes = [pd.factorize(d.date)[0], pd.factorize(d.group + d.date.dt.strftime("%Y"))[0]]
    M = wdemean(d[["delta_mw", "dose"]].to_numpy(float), codes, np.ones(len(d)))
    b = (M[:, 1] @ M[:, 0]) / (M[:, 1] @ M[:, 1])
    se = np.sqrt(cluster_meat(M[:, [1]], M[:, 0] - b * M[:, 1], d.date.to_numpy())[0, 0]) / (M[:, 1] @ M[:, 1])
    return float(b), float(se)


def main() -> int:
    fails: list[str] = []

    def check(ok: bool, what: str) -> None:
        print(f"  {'ok  ' if ok else 'FAIL'} {what}")
        if not ok:
            fails.append(what)

    if not PANEL.exists():
        print(f"  FAIL {PANEL.relative_to(ROOT)} missing\nFAIL: 1")
        return 1
    p = pd.read_parquet(PANEL)
    ref = pd.read_csv(LEGS).set_index("leg")
    for leg in ("gen_bilateral", "retail_bilateral"):
        b, se = daily_leg(p, leg)
        want, wse = ref.loc[leg, "b"], ref.loc[leg, "se"]
        check(abs(b - want) < 2 * wse, f"{leg}: {b:+.3f} (se {se:.3f}) against step 2's {want:+.3f} (se {wse:.3f})")
    s = p[p.s.notna()].copy()
    hrs = pd.concat([pd.read_parquet(f, columns=["date", "period", "p_star"])
                     for f in sorted((ROOT / "outputs/cache/step").glob("hours_2*.parquet"))])
    hrs["date"], hrs["hour"] = pd.to_datetime(hrs.date), hrs.period - 1
    s = s.merge(hrs[["date", "hour", "p_star"]], on=["date", "hour"], how="left")
    low = s[s.p_star <= 5]
    # at prices near zero every firm offers its renewables there, so s must be positive; at higher
    # prices a firm can have nothing within ±€5 (31–42% of hours for four of the five firms)
    check((low.s > 0).mean() >= 0.99, f"s > 0 on {(low.s > 0).mean():.1%} of {len(low):,} hours priced ≤ €5 "
                                      f"({(s.s > 0).mean():.1%} of all {len(s):,})")
    check((s.s <= s.offered_mw / 10 + 1e-9).all(), "s ≤ offered sell MW / 10")
    q = p[p.slope.notna()]
    check(np.allclose(q.P, q.dose_mw / q.slope), "P = dose / slope")
    print("PASS" if not fails else f"FAIL: {len(fails)}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
