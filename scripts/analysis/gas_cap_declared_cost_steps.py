#!/usr/bin/env python3
"""The reference-price steps (PRGN 40 -> 45 -> 50 -> 55) read on the declared cost (notes/rq-crisis-quantity.md, I3, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_declared_cost_steps.py

For each step date: actual J (median over units of the change in mean log(declared / gross) from the 7 days before to the 7 days from the date), the J
predicted at rho = 0 and 1 from the same unit-days, the implied rho, and the power rule against the 273 pre-cap placebo dates.
Writes outputs/tables/gas_cap_declared_cost_steps.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_declared_cost import jump, panel  # noqa: E402

T = ROOT / "outputs" / "tables"
STEPS = [pd.Timestamp("2023-01-01"), pd.Timestamp("2023-02-01"), pd.Timestamp("2023-03-01")]


def predicted(d: pd.DataFrame, day: pd.Timestamp, rho: float) -> float:
    x = d[d.date.between(day - pd.Timedelta(days=7), day + pd.Timedelta(days=6))].copy()
    x["post"] = x.date >= day
    x["lr"] = np.log(np.clip(1 - rho * x.s_bid / x.gross_bid, 1e-6, None))
    m = x.groupby(["unit", "post"]).lr.mean().unstack()
    return float((m[True] - m[False]).dropna().median())


def main() -> int:
    d = panel()
    ev = pd.read_csv(T / "gas_cap_declared_cost_event.csv")
    sd_pl = float(ev[ev.kind == "placebo"].J.std())
    print(f"placebo J (273 pre-cap dates): sd {sd_pl:.3f}")
    grid = np.linspace(-1, 2, 301)
    rows = []
    for D in STEPS:
        w = d[d.date.between(D - pd.Timedelta(days=7), D + pd.Timedelta(days=6))]
        s_mean = w.s_bid.mean()
        units = w.unit.nunique()
        if not (s_mean > 0 and (w.s_bid > 0).mean() > 0.5):
            print(f"{D.date()}: S > 0 on {(w.s_bid > 0).mean():.0%} of unit-days in the windows (mean S {s_mean:.1f}); skipped")
            rows.append({"step": D.date(), "skipped": True, "mean_s": s_mean})
            continue
        J = jump(d, D)
        J0, J1 = predicted(d, D, 0.0), predicted(d, D, 1.0)
        gap = abs(J1 - J0)
        pred = np.array([predicted(d, D, r) for r in grid[::10]])
        rhos = grid[::10]
        implied = float(np.interp(J, pred[np.argsort(pred)], rhos[np.argsort(pred)])) if gap > 0 else np.nan
        powered = gap >= 2 * sd_pl
        print(f"{D.date()}: {units} units, mean S {s_mean:.1f}; J actual {J:+.3f}, at rho 0 {J0:+.3f}, at rho 1 {J1:+.3f}; "
              f"|J1 - J0| {gap:.3f} vs 2 sd {2 * sd_pl:.3f} -> {'powered' if powered else 'cannot size rho'}; implied rho {implied:.2f}")
        rows.append({"step": D.date(), "skipped": False, "units": units, "mean_s": s_mean, "J": J, "J_rho0": J0, "J_rho1": J1,
                     "gap": gap, "two_sd_placebo": 2 * sd_pl, "powered": powered, "implied_rho": implied if powered else np.nan})
    pd.DataFrame(rows).to_csv(T / "gas_cap_declared_cost_steps.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
