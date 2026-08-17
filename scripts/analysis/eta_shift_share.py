#!/usr/bin/env python3
"""How much of the elasticity decline is movement along the curve, and how much
is the curve itself changing?

    .venv/bin/python scripts/analysis/eta_shift_share.py

Residual demand elasticity fell from 1.83 to 0.45. Three things could do that:

  mechanical    the clearing point moved to a steeper part of a fixed stack
  compositional units entered and exited, changing the stack
  behavioural   surviving units submit different curves

`bid_steepness_iv.py` identifies the behavioural channel by putting a unit's own
submitted curve on the left-hand side. This script puts a magnitude on the split,
which the regression alone cannot.

THE DECOMPOSITION

The residual demand slope is a function of the price it is evaluated at:
`|RD'(p)|`. Each year has both its own curves and its own clearing prices, so:

    eta_actual(y)   = slope_y( p*_y )  * p*_y / Q       what happened
    eta_atbase(y)   = slope_y( p*_2018 ) * p*_2018 / Q  same curves, 2018's price

Comparing them separates the two forces:

  * `eta_atbase` falling over time means the **curve itself** got steeper at a
    given price -- composition or behaviour.
  * `eta_actual` falling faster than `eta_atbase` means the market moved to a
    **steeper region** of the curve -- the mechanical channel.

Splitting composition from behaviour then needs the balanced set of units present
throughout, which `--balanced` restricts to. What remains among survivors is
behavioural.

WHY A COUNTERFACTUAL PRICE IS LEGITIMATE HERE

We are not simulating a counterfactual equilibrium -- that would need the whole
market to re-clear and is not identified. We are evaluating an *observed* curve
at a different point on itself, which is just reading off a function that was
submitted. The bids at prices away from the clearing point are real submitted
offers, which is exactly what this market publishes and most do not.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
BAND = 5.0
MONTHS = [f"{y}{m}" for y in range(2018, 2027) for m in ("04", "10")]


def slope_at(g: pd.DataFrame, p: float) -> float:
    """Local slope of residual demand at price p: (sell + buy) within +/- BAND."""
    near = g[g.price_eur_mwh.between(p - BAND, p + BAND)]
    s = near[near.side == "V"].power_mw.sum()
    b = near[near.side == "C"].power_mw.sum()
    return (s + b) / (2 * BAND)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--balanced", action="store_true",
                    help="only units present in every sampled year")
    args = ap.parse_args()

    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es", "price_pt"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)
    px = px[(px.price_es - px.price_pt).abs() < 1e-6]     # coupled periods only

    frames = {}
    for ym in MONTHS:
        f = DATA / "omie/bids/parquet" / f"bids_{ym}.parquet"
        if not f.exists():
            continue
        t = ds.dataset(f).to_table(
            filter=(pc.field("status") == "O"),
            columns=["date", "period", "unit", "side", "price_eur_mwh", "power_mw"]
        ).to_pandas()
        t["date"] = pd.to_datetime(t.date)
        t = t.merge(px, on=["date", "period"], how="inner")
        if not t.empty:
            frames.setdefault(int(ym[:4]), []).append(t)

    if args.balanced:
        per_year = {y: set(pd.concat(v).unit.unique()) for y, v in frames.items()}
        keep = set.intersection(*per_year.values())
        print(f"balanced panel: {len(keep):,} units present in all "
              f"{len(per_year)} years\n")
    else:
        keep = None

    # 2018's median clearing price is the common evaluation point.
    base_p = float(pd.concat(frames[2018]).drop_duplicates(["date", "period"])
                   .price_es.median())

    rows = []
    for y, v in sorted(frames.items()):
        t = pd.concat(v, ignore_index=True)
        if keep is not None:
            t = t[t.unit.isin(keep)]
        for (d, per), g in t.groupby(["date", "period"], sort=False):
            p = g.price_es.iloc[0]
            if p <= 1:
                continue
            q = g[(g.side == "V") & (g.price_eur_mwh <= p)].power_mw.sum()
            qb = g[(g.side == "V") & (g.price_eur_mwh <= base_p)].power_mw.sum()
            sa, sb = slope_at(g, p), slope_at(g, base_p)
            if q <= 0 or qb <= 0 or sa <= 0 or sb <= 0:
                continue
            rows.append((y, sa * p / q, sb * base_p / qb))
    d = pd.DataFrame(rows, columns=["year", "eta_actual", "eta_atbase"])

    g = d.groupby("year").median()
    g["periods"] = d.groupby("year").size()
    print(f"Evaluation price held at 2018's median clearing price: "
          f"{base_p:.1f} EUR/MWh\n")
    print(f"{'year':<7}{'eta actual':>12}{'eta at base price':>20}{'periods':>10}")
    for y, r in g.iterrows():
        print(f"{y:<7}{r.eta_actual:>12.2f}{r.eta_atbase:>20.2f}{int(r.periods):>10,}")

    a0, b0 = g.eta_actual.iloc[0], g.eta_atbase.iloc[0]
    a1, b1 = g.eta_actual.iloc[-1], g.eta_atbase.iloc[-1]
    total = a1 - a0
    curve = b1 - b0
    print(f"\n  total change in eta:              {total:+.2f}")
    print(f"  curve changed at a fixed price:   {curve:+.2f}"
          f"   ({curve/total:.0%} of the total)")
    print(f"  residual, movement along the curve: {total-curve:+.2f}"
          f"   ({(total-curve)/total:.0%})")
    print("\n  'curve changed' = composition + behaviour; run --balanced to hold "
          "\n  the unit set fixed, leaving behaviour.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
