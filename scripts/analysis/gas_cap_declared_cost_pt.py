#!/usr/bin/env python3
"""Were the Portuguese gas plants subsidised? The declared-cost event, by country
(notes/rq-crisis-quantity.md, E1, fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_declared_cost_pt.py

J(D) of `gas_cap_declared_cost.py` on Portuguese and on Spanish units separately: 2022-06-15 against every
placebo date 2021-09-08 -> 2022-06-07. Rule: Portuguese plants count as subsidised if J(2022-06-15) is below the
2.5th percentile of their placebo J's and within 0.15 of the J a full pass-through would give.
Writes outputs/tables/gas_cap_declared_cost_pt.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_declared_cost import CAP, jump, panel  # noqa: E402

T = ROOT / "outputs" / "tables"


def main() -> int:
    d = panel()
    rows = []
    for c in ("PT", "ES"):
        x = d[d.country == c]
        first = x[x.date.between(CAP, CAP + pd.Timedelta(days=6))]
        full = float(np.log(first.net_bid / first.gross_bid).median())
        a = jump(x, CAP)
        pl = np.array([jump(x, day) for day in pd.date_range("2021-09-08", CAP - pd.Timedelta(days=8))])
        pl = pl[~np.isnan(pl)]
        q = np.percentile(pl, [2.5, 50, 97.5])
        ok = (a < q[0]) and abs(a - full) <= 0.15
        rows.append({"country": c, "units": x.unit.nunique(), "J_actual": a, "J_full_passthrough": full,
                     "placebo_n": len(pl), "placebo_p2_5": q[0], "placebo_median": q[1], "placebo_p97_5": q[2],
                     "placebo_min": pl.min(), "rank_of_actual": float((pl <= a).mean()), "rule": ok})
        print(f"{c}: {x.unit.nunique()} units; J(2022-06-15) {a:+.3f}; full pass-through {full:+.3f}; placebo n {len(pl)}, "
              f"2.5/50/97.5% {q[0]:+.3f} / {q[1]:+.3f} / {q[2]:+.3f}, min {pl.min():+.3f}; "
              f"{'RULE MET' if ok else 'rule not met'}")
    pt = d[d.country == "PT"]
    w = pt[pt.date.between("2022-06-08", "2022-06-22")].groupby("date").agg(
        declared=("v", "median"), gross=("gross_bid", "median"), subsidy=("s_bid", "median"), net=("net_bid", "median"))
    print("\nPortuguese units, declared variable term around the start (median, EUR/MWh):")
    print(w.round(1).to_string())
    print("\nunits:", sorted(pt.unit.unique()))
    pd.DataFrame(rows).to_csv(T / "gas_cap_declared_cost_pt.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
