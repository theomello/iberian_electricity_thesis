#!/usr/bin/env python3
"""Does forward contracting explain the residual-demand-elasticity puzzle?

    .venv/bin/python scripts/analysis/hortacsu_puller_test.py --month 202401

THE PUZZLE

Residual demand facing the largest Iberian firms has an elasticity **below 1**
-- Iberdrola faces 0.49 against a market-wide 0.79 in January 2024. Static
oligopoly gives Lerner = 1/eta, so eta = 0.49 implies a 204% markup: price below
marginal cost, which is impossible. Measured elasticities below 1 are common in
electricity markets and no static model rationalises them.

THE STANDARD RESOLUTION, AND THE TEST

Hortacsu & Puller (2008) show that a firm holding forward contracts maximises
profit where

    p - MC(q)  =  (q - theta) / |RD'(p)|

The markup scales with the **uncontracted** quantity `q - theta`, not with `q`.
A firm that has sold everything forward optimally bids its marginal cost however
steep its residual demand, because raising the price earns it nothing on volume
already sold at a fixed price.

Invert it and marginal cost becomes observable:

    MC_it  =  p_t  -  (q_it - theta_it) / |RD'_it|

Every term on the right is measured here, which is unusual: `theta` is normally
unobservable, and Hortacsu & Puller had to obtain contract data specially.
MIBEL publishes it daily as PDBF role 4.

WHAT MAKES THIS A TEST RATHER THAN AN ACCOUNTING IDENTITY

The implied `MC` is not free to be anything. It must be **positive**, it must be
**ordered by technology** in the way engineering says (nuclear and hydro below
gas, gas below oil), and it must be **stable** within a firm across hours when
fuel prices have not moved. If contracting is the resolution, imposing theta
should move implied marginal cost toward those properties and away from the
absurd values the no-contract version produces. That comparison -- with theta
against theta set to zero -- is the test.

THE KNOWN BIAS

PDBF publishes *physical* bilateral contracts. A financially settled hedge is
economically identical for this first-order condition and is invisible here, so
measured theta is a **lower bound**. That biases `q - theta` upward and implied
MC downward: the test is conservative, and if implied costs still look sensible
with an understated theta, the true position is stronger.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
BAND = 5.0     # +/- EUR/MWh window for the local slope, as in residual_demand_slope.py


def owner_map() -> dict[str, str]:
    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    o = ul.dropna(subset=["agent_owner"]).drop_duplicates("unit", keep="last")
    return dict(zip(o.unit, o.agent_owner))


def tech_map() -> dict[str, str]:
    ul = pq.read_table(DATA / "omie/registry/omie_unit_lists.parquet").to_pandas()
    t = ul.dropna(subset=["technology"]).drop_duplicates("unit", keep="last")
    return dict(zip(t.unit, t.technology))


def firm_position(ym: str, owner: dict) -> pd.DataFrame:
    """Total scheduled output `q` and contracted volume `theta`, per firm-period.

    `q` must be TOTAL production, not day-ahead cleared volume. In the
    first-order condition `q - theta` is the quantity exposed to the spot price,
    and bilaterally contracted energy never enters the auction -- so day-ahead
    cleared volume is already approximately `q - theta`. Using it as `q` and then
    subtracting theta counts the contracts twice, which is what produced an
    implied theta/q of 2.91 for Iberdrola on a first pass.

    PDBF is the operating schedule and carries every role, so its total positive
    schedule per firm is the right `q`, and role 4 within it is `theta`.
    """
    f = DATA / "omie/pdbf/parquet" / f"pdbf_{ym}.parquet"
    t = pq.read_table(f, columns=["date", "period", "unit", "schedule_mw",
                                  "resolution_min", "role_code"]).to_pandas()
    t = t[t.schedule_mw > 0].copy()
    t["e"] = t.schedule_mw * t.resolution_min / 60.0
    t["firm"] = t.unit.map(owner)
    t["date"] = pd.to_datetime(t.date)
    g = t.groupby(["date", "period", "firm"], as_index=False).agg(
        q=("e", "sum"),
        theta=("e", lambda s: s[t.loc[s.index, "role_code"] == "4"].sum()))
    return g


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--month", default="202401")
    ap.add_argument("--top", type=int, default=6)
    args = ap.parse_args()

    owner, tech = owner_map(), tech_map()
    px = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                       columns=["date", "period", "price_es"]).to_pandas()
    px["date"] = pd.to_datetime(px.date)

    b = ds.dataset(DATA / "omie/bids/parquet" / f"bids_{args.month}.parquet").to_table(
        columns=["date", "period", "unit", "side", "status", "price_eur_mwh",
                 "power_mw", "resolution_min"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b = b.merge(px, on=["date", "period"], how="inner")
    b["firm"] = b.unit.map(owner)
    b["e"] = b.power_mw * b.resolution_min / 60.0

    off = b[b.status == "O"]
    cleared = b[(b.status == "C") & (b.side == "V")]
    pos = firm_position(args.month, owner)

    top = (pos.groupby("firm").q.sum().nlargest(args.top).index.tolist())

    rows = []
    for (d, per), g in off.groupby(["date", "period"], sort=False):
        p = g.price_es.iloc[0]
        if p <= 1:                       # eta degenerates at zero prices
            continue
        near = g[g.price_eur_mwh.between(p - BAND, p + BAND)]
        sell_all = near[near.side == "V"]
        buy = near[near.side == "C"].power_mw.sum()
        for fm in top:
            # Residual demand facing THIS firm: its own offers are removed from
            # the supply that would replace it.
            slope = (sell_all[sell_all.firm != fm].power_mw.sum() + buy) / (2 * BAND)
            if slope <= 0:
                continue
            rows.append((d, per, fm, p, slope))
    sl = pd.DataFrame(rows, columns=["date", "period", "firm", "p", "slope"])

    m = sl.merge(pos, on=["date", "period", "firm"], how="inner")

    m["mc_with_theta"] = m.p - (m.q - m.theta) / m.slope
    m["mc_no_theta"] = m.p - m.q / m.slope

    print(f"HORTACSU-PULLER TEST, {args.month}   "
          f"{m.date.nunique()} days, {len(m):,} firm-periods\n")
    print(f"{'firm':<34}{'theta/q':>9}{'implied MC':>12}{'if theta=0':>12}"
          f"{'MC<0':>8}")
    for fm, x in m.groupby("firm"):
        share = (x.theta.sum() / x.q.sum()) if x.q.sum() > 0 else np.nan
        print(f"{str(fm)[:33]:<34}{share:>9.2f}{x.mc_with_theta.median():>12.1f}"
              f"{x.mc_no_theta.median():>12.1f}"
              f"{(x.mc_with_theta < 0).mean():>8.0%}")

    # ---- validation: does implied MC order by the technology at the firm's
    # margin? This is the sharpest test of the cost model. The FOC is a firm-level
    # condition, so implied MC is the cost of the firm's MARGINAL unit -- which is
    # identifiable as its highest-priced accepted offer that period.
    marg = (cleared[cleared.price_eur_mwh > 0]
            .sort_values("price_eur_mwh")
            .groupby(["date", "period", "firm"]).tail(1)
            [["date", "period", "firm", "unit"]])
    import re as _re
    def band(t):
        t = str(t)
        if "Nuclear" in t: return "nuclear"
        if _re.search(r"Hidr[aá]ulica|Bombeo", t): return "hydro"
        if _re.search(r"E[oó]lica", t): return "wind"
        if "Solar" in t: return "solar"
        if "Ciclo Combinado" in t: return "gas CCGT"
        if _re.search(r"Hulla|Antracita|Carb[oó]n|Lignito", t): return "coal"
        if _re.search(r"T[eé]rmica no", t): return "cogeneration"
        return None
    marg["margtech"] = marg.unit.map(tech).map(band)
    mm = m.merge(marg.drop(columns=["unit"]), on=["date", "period", "firm"], how="left")
    mm = mm.dropna(subset=["margtech"])
    if len(mm) > 50:
        print("\n  IMPLIED MC BY THE TECHNOLOGY AT THE FIRM'S MARGIN")
        print(f"    {'technology':<16}{'n':>7}{'implied MC':>12}{'if theta=0':>12}")
        for tname, x in mm.groupby("margtech"):
            if len(x) < 20:
                continue
            print(f"    {tname:<16}{len(x):>7,}{x.mc_with_theta.median():>12.1f}"
                  f"{x.mc_no_theta.median():>12.1f}")

    print(f"\n  median clearing price {m.p.median():.1f} EUR/MWh")
    print(f"  share of firm-periods with implied MC below zero: "
          f"with theta {(m.mc_with_theta < 0).mean():.0%}, "
          f"without {(m.mc_no_theta < 0).mean():.0%}")
    print(f"  median implied MC: with theta {m.mc_with_theta.median():.1f}, "
          f"without {m.mc_no_theta.median():.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
