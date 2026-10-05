#!/usr/bin/env python3
"""Does Iberdrola's retail arm anticipate its own hydro self-supply?

    .venv/bin/python scripts/analysis/iberdrola_self_supply.py

Step 2d of `notes/rq-midday-hydro.md`. Iberdrola's storage hydro sells mostly
through two bilateral contracts whose only buyers are its own retail units
(§3.8), and P.O. 3.1 lets a domestic bilateral be nominated AFTER the day-ahead
auction. The note inferred that the allocation is nonetheless committed at gate
closure, because the retail units must bid their demand into the auction by
12:00 and should bid for less where they expect self-supply.

THE TEST

Within a day, regress each retail outcome on the hour's hydro self-supply (PDBF
role 4 on the six storage units, MWh) and REE's day-ahead demand forecast, with
standard errors clustered on day. Outcomes, summed over all ten Iberdrola
purchase units (not just the two contract counterparties -- before 2023 those
two bid almost nothing, and the retail demand went through `IBCUC01` and
`IGESC01`):

* bid      -- offered demand volume, at any price
* bought   -- cleared demand volume
* intraday -- net intraday purchases (buy minus sell), where a surplus from a
              post-auction nomination would have to be resold

Anticipation at gate closure predicts `bid` and `bought` near -1. A purely
post-auction nomination predicts both near 0 and the surplus showing up in
`intraday`.

WHAT IT CANNOT SEPARATE

A falling `bought` with an unchanged `bid` means the cut comes through the price
of the demand bids or through the market price itself. Hydro self-supply is
highest in the evening, when the price is too, so a price-elastic demand bid
clears less then with no anticipation at all. The forecast controls for the
level of demand, not for its price.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from unit_ownership import spells  # noqa: E402

HYDRO = ["DUER", "EBRA", "JUCA", "MUEL", "SIL", "TAJO"]
MONTHS = ["201903", "201910", "202103", "202203", "202303", "202403", "202410", "202503"]
OUTCOMES = ["bid", "bought", "intraday", "other_bil", "total"]


def iberdrola_purchase_units() -> list[str]:
    """Purchase units Iberdrola owns on some date since 2018 (lib/unit_ownership.py,
    2026-10-05). The same ten units as the latest listing gives, each Iberdrola's
    whole throughout."""
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "role"])
    sp = spells()
    ib = set(sp[(sp.group == "IBERDROLA") & (sp.end > pd.Timestamp("2018-01-01"))].unit)
    return sorted(u[u.unit.isin(ib) & u.role.str.startswith("purchase", na=False)].unit)


def demand_forecast() -> pd.DataFrame:
    fc = pd.read_parquet(DATA / "ree/ree_demand_forecast_5min.parquet",
                         columns=["utc_timestamp", "demand_forecast_mw"])
    t = pd.to_datetime(fc.utc_timestamp, utc=True).dt.tz_convert("Europe/Madrid")
    fc["date"] = t.dt.tz_localize(None).dt.normalize()
    fc["hour"] = t.dt.hour + 1
    return fc.groupby(["date", "hour"]).demand_forecast_mw.mean().rename("fcst").reset_index()


def month_panel(ym: str, retail: list[str]) -> pd.DataFrame:
    keys = ["date", "hour"]
    p = pq.read_table(DATA / f"omie/pdbf/parquet/pdbf_{ym}.parquet",
                      filters=[("role_code", "==", "4"),
                               ("unit", "in", HYDRO + retail)]).to_pandas()
    p["hour"] = ((p.period - 1) * p.resolution_min // 60 + 1).astype(int)
    p["mwh"] = p.schedule_mw * p.resolution_min / 60
    hydro = p[p.unit.isin(HYDRO) & (p.mwh > 0)].groupby(keys).mwh.sum().rename("hydro_bil")
    # Net bilateral inflow into the retail set: buy legs (negative) minus sell
    # legs (positive) over the retail units. Netting matters. Until 2022 IGESC01,
    # itself one of the purchase units, bought in the auction and passed the
    # energy on to the other retail units by bilateral contract
    # (iberdrola_contract_trace.py). Counting only buy legs counted that energy
    # twice -- as IGESC01's auction purchase and as the receiving unit's receipt.
    recv = (-p[p.unit.isin(retail)].groupby(keys).mwh.sum()).rename("recv_all")

    cols = ["date", "hour", "resolution_min", "unit", "side", "status", "power_mw"]
    b = pq.read_table(DATA / f"omie/bids/parquet/bids_{ym}.parquet", columns=cols,
                      filters=[("unit", "in", retail), ("side", "==", "C")]).to_pandas()
    b["mwh"] = b.power_mw * b.resolution_min / 60
    bid = b[b.status == "O"].groupby(keys).mwh.sum().rename("bid")
    bought = b[b.status == "C"].groupby(keys).mwh.sum().rename("bought")

    i = pq.read_table(DATA / f"omie/intraday/parquet/intraday_{ym}.parquet", columns=cols,
                      filters=[("unit", "in", retail), ("status", "==", "C")]).to_pandas()
    sign = i.side.astype(str).map({"C": 1.0, "V": -1.0}).astype(float)
    i["mwh"] = i.power_mw * i.resolution_min / 60 * sign
    intraday = i.groupby(keys).mwh.sum().rename("intraday")

    d = pd.concat([hydro, recv, bid, bought, intraday], axis=1).fillna(0.0).reset_index()
    d["date"] = pd.to_datetime(d.date)
    # The hydro contracts' buy legs sit on the retail units and equal the hydro
    # sell legs exactly (§3.8), so the net inflow from every OTHER contract is
    # the rest.
    d["other_bil"] = d.recv_all - d.hydro_bil
    d["total"] = d.bought + d.intraday + d.recv_all
    return d[d.hour <= 24]


def within_day_ols(g: pd.DataFrame, y: str) -> tuple[float, float]:
    cols = [y, "hydro_bil", "fcst"]
    w = g[cols] - g.groupby("date")[cols].transform("mean")
    X = np.column_stack([w.hydro_bil, w.fcst])
    yy = w[y].to_numpy()
    inv = np.linalg.inv(X.T @ X)
    beta = inv @ X.T @ yy
    e = yy - X @ beta
    groups = g.reset_index(drop=True).groupby("date").indices.values()
    meat = sum(np.outer(X[ix].T @ e[ix], X[ix].T @ e[ix]) for ix in groups)
    return beta[0], float(np.sqrt((inv @ meat @ inv)[0, 0]))


def main() -> int:
    retail = iberdrola_purchase_units()
    fc = demand_forecast()
    print(f"{len(retail)} Iberdrola purchase units: {', '.join(retail)}\n")
    print("Within-day coefficient on hydro self-supply (MWh per MWh), day-clustered se, "
          "controlling for REE's demand forecast")
    print(f"{'month':7s}" + "".join(f"{c:>18s}" for c in OUTCOMES)
          + f"{'hydro_bil':>11s}{'bought':>9s}{'other_bil':>11s}{'gap':>7s}")
    for ym in MONTHS:
        g = month_panel(ym, retail).merge(fc, on=["date", "hour"], how="inner")
        cells = []
        for y in OUTCOMES:
            b, se = within_day_ols(g, y)
            cells.append(f"{b:+.2f} ({se:.2f})".rjust(18))
        # gap: hydro receipts not matched by a hydro-leg sale -- should be 0
        gap = (g.recv_all - g.other_bil - g.hydro_bil).abs().max()
        print(f"{ym:7s}" + "".join(cells) + f"{g.hydro_bil.mean():11.0f}{g.bought.mean():9.0f}"
              f"{g.other_bil.mean():11.0f}{gap:7.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
