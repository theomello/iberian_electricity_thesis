#!/usr/bin/env python3
"""The cap's pass-through in euros, offer side (notes/rq-crisis-quantity.md, section C, fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_pass_through_eur.py

V = sum over Iberian unit-hours of the B1/B2/B3 main sample (predicted in-money at margin EUR 50, essential
units out, cost defined), 2022-06-15 -> 2023-02-25 with a subsidy, of S_day x offered MW x 1 h. rho x V is the
part of the subsidy attached to in-money offered capacity that went into those offers. Not the consumer's
saving (that needs the price-setting step), and offered MW, not cleared, so V overstates what was paid out.

Writes outputs/tables/gas_cap_pass_through_eur.csv and gas_cap_pass_through_eur_monthly.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_quantity_b1 import PANEL, panel  # noqa: E402

T = ROOT / "outputs" / "tables"
CAP1 = pd.Timestamp("2023-02-25")
RHOS = [("B3 interval low", 0.51), ("B3 with gas controls", 0.54), ("B3 main, low end of quoted range", 0.55),
        ("B3 main", 0.73), ("B3 high end of quoted range", 0.75), ("declared cost low", 0.90),
        ("declared cost high", 1.00), ("B3 interval high", 1.03)]


def main() -> int:
    h = panel()
    h = h[h.iberia & (h.subsidy > 0) & (h.date <= CAP1)]
    mw = pd.read_parquet(PANEL, columns=["unit", "date", "period", "offered_mw"])
    h = h.merge(mw, on=["unit", "date", "period"], how="left")
    assert h.offered_mw.notna().all(), "every main-sample unit-hour must carry offered MW"
    h = h.assign(v=h.subsidy * h.offered_mw)
    m = h.groupby(h.date.dt.to_period("M")).agg(units=("unit", "nunique"), offered_gwh=("offered_mw", "sum"),
                                                mean_subsidy=("subsidy", "mean"), v_eur_m=("v", "sum"))
    m["offered_gwh"] /= 1e3
    m["v_eur_m"] /= 1e6
    print(m.round(1).to_string())
    V = h.v.sum() / 1e6
    print(f"\nV = EUR {V:,.0f} m over {int(h.offered_mw.sum() / 1e3):,} GWh of in-money offered capacity, "
          f"{h.unit.nunique()} units, {h.groupby(['date', 'period']).ngroups:,} hours")
    rows = [{"label": lab, "rho": r, "eur_m": r * V, "v_eur_m": V} for lab, r in RHOS]
    for x in rows:
        print(f"  rho {x['rho']:.2f}  {x['label']:<34} rho x V = EUR {x['eur_m']:,.0f} m")
    pd.DataFrame(rows).to_csv(T / "gas_cap_pass_through_eur.csv", index=False)
    m.reset_index().assign(date=lambda d: d.date.astype(str)).rename(columns={"date": "month"}).to_csv(
        T / "gas_cap_pass_through_eur_monthly.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
