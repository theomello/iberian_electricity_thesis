#!/usr/bin/env python3
"""Each firm's net position in the day-ahead auction, against the panel's q - theta.

    .venv/bin/python scripts/analysis/firm_net_position.py

WHY

`notes/rq-descriptive-price-formation.md` §4.5 reads Iberdrola, Naturgy, Endesa
and Repsol as NET DAY-AHEAD BUYERS from `incentive_h* = ability * (q - theta)/q`
in `firm_residual_demand_full_owner.parquet`. There q is the firm's auction-
cleared SELL volume and theta its BILATERAL schedule (PDBF role 4). Bilateral
energy never enters the auction, so `q - theta` subtracts the contracts twice --
the error `hortacsu_puller_test.py` caught in its first pass (commit 6c900ec).
`theta > q` says a firm sells more through contracts than through the auction,
not that it is a net buyer.

What does say it: cleared sales minus cleared purchases over every unit the
firm owns. For a firm with a retail arm, the retail load bought in the auction
is the fixed-price commitment that offsets its sales; physical bilateral energy
drops out of both sides.

Three sample months a year (Feb, Jun, Oct), all periods. The panel column is
over the periods the firm panel keeps (p* > 0, no splitting), so the two are
comparable in sign, not in level.

Describes the AS-BUILT net position. The exposed position (regulated
pass-through suppliers excluded, framework spec §2.4) is computed in firm_x.py.

Owners by date and by share (lib/unit_ownership.py, 2026-10-05): a unit's cleared
volume counts for each owner in force that day, times its share, so a co-owned
reactor is split among its co-owners and a sold business sits with its owner at
the time. EDP COMERCIAL is part of EDP since the GROUP_MERGES of 2026-09-30.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from unit_ownership import attach_owners, spells  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
FIRM_PANEL = ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet"
FIRMS = ["IBERDROLA", "ENDESA", "NATURGY", "REPSOL", "EDP"]
MONTHS = ("02", "06", "10")


def auction_net() -> pd.DataFrame:
    sp = spells()
    sp = sp[sp.unit.isin(set(sp.loc[sp.group.isin(FIRMS), "unit"]))]
    rows = []
    for y in range(2018, 2027):
        for mm in MONTHS:
            f = BIDS / f"bids_{y}{mm}.parquet"
            if not f.exists():
                continue
            b = pq.read_table(f, columns=["date", "unit", "side", "status", "power_mw", "resolution_min"],
                              filters=[("status", "==", "C"), ("unit", "in", sorted(set(sp.unit)))]
                              ).to_pandas()
            b["date"] = pd.to_datetime(b.date)
            b["unit"] = b.unit.astype(str)
            b = attach_owners(b, sp).rename(columns={"group": "firm"})   # power_mw x share
            b = b[b.firm.isin(FIRMS)]
            b["twh"] = b.power_mw * b.resolution_min / 60 / 1e6
            t = b.pivot_table(index="firm", columns="side", values="twh", aggfunc="sum",
                              observed=True).fillna(0.0)
            rows.append(t.assign(year=y).reset_index())
    a = pd.concat(rows).groupby(["firm", "year"])[["V", "C"]].sum()
    a["net"] = a.V - a.C
    return a.rename(columns={"V": "sell", "C": "buy"})


def panel_q_minus_theta() -> pd.Series:
    f = pq.read_table(FIRM_PANEL, columns=["date", "firm", "q_firm_mw", "theta_mw", "resolution_min"],
                      filters=[("firm", "in", FIRMS)]).to_pandas()
    f["date"] = pd.to_datetime(f.date)
    f = f[f.date.dt.month.isin([int(m) for m in MONTHS])]
    f["year"] = f.date.dt.year
    f["v"] = (f.q_firm_mw - f.theta_mw) * f.resolution_min / 60 / 1e6
    return f.groupby(["firm", "year"]).v.sum().rename("panel_q_minus_theta")


def main() -> int:
    out = auction_net().join(panel_q_minus_theta()).round(2)
    print("TWh over Feb + Jun + Oct of each year")
    for firm in FIRMS:
        if firm in out.index.get_level_values(0):
            print(f"\n{firm}")
            print(out.loc[firm].T.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
