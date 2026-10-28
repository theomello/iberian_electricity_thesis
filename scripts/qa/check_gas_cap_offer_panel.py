#!/usr/bin/env python3
"""Checks on the gas-cap offer panel's gross-cost columns and essential-unit flag (step B0 of
docs/specs/2026-10-28-crisis-quantity-design.md).

    .venv/bin/python scripts/qa/check_gas_cap_offer_panel.py

1. Where there is no subsidy (all of Italy, Iberia before 2022-06-15), `run{10,20,50}_gross` equals
   `run{10,20,50}` exactly, cost and gross cost being the same number.
2. Where the subsidy is positive, `run20_gross >= run20` (a higher threshold counts at least the
   same MW), and strictly greater on some unit-hours.
3. `essential` is True exactly for UP_PORCARI_1 and UP_SARLUX_1 and False on every Iberian row.

Exits non-zero on any failure.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
ESSENTIAL = {"UP_PORCARI_1", "UP_SARLUX_1"}


def main() -> int:
    h = pd.read_parquet(PANEL)
    fails = []
    need = [f"run{x}_gross" for x in (10, 20, 50)] + ["essential"]
    missing = [c for c in need if c not in h.columns]
    if missing:
        print(f"FAIL: columns missing: {missing}")
        return 1
    nosub = h.subsidy.fillna(0) == 0
    for x in (10, 20, 50):
        a, b = h.loc[nosub, f"run{x}"], h.loc[nosub, f"run{x}_gross"]
        same = np.isclose(a, b, equal_nan=True).all()
        print(f"run{x}_gross == run{x} without subsidy ({nosub.sum():,} unit-hours): {same}")
        if not same:
            fails.append(f"run{x}")
    sub = h.subsidy > 0
    d = h.loc[sub, "run20_gross"] - h.loc[sub, "run20"]
    ok = (d.dropna() >= -1e-9).all() and (d > 1e-9).any()
    print(f"with subsidy ({sub.sum():,} unit-hours): run20_gross >= run20 always and > on {(d > 1e-9).mean():.1%}: {ok}")
    if not ok:
        fails.append("gross >= net")
    flagged = set(h.loc[h.essential, "unit"])
    ok = flagged == ESSENTIAL and not h.loc[h.iberia, "essential"].any()
    print(f"essential units {sorted(flagged)}: {ok}")
    if not ok:
        fails.append("essential")
    print("FAIL: " + ", ".join(fails) if fails else "all checks pass")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main())
