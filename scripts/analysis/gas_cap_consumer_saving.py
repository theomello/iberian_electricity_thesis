#!/usr/bin/env python3
"""The consumer's saving from the cap's pass-through: re-clear the day-ahead curve with the 54 modelled gas
units' offers moved up by rho x S_day (notes/rq-crisis-quantity.md, section D, fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_consumer_saving.py [--months 202206 ...] [--units panel|ccgt_coal|thermal]

Effective curve and re-clear as in `step_curves.py`. Hours: 2022-06-15 -> 2023-02-25 with a subsidy, 24-period
days, valid hours (unsplit, clearing identity holds, re-clear within 0.5 of the published price).
`--units`: `panel` (default) the modelled gas units of the offer panel; `ccgt_coal` adds every unit OMIE's listing
labels gas CCGT or coal; `thermal` adds cogeneration too (eligibility unchecked). Outputs get the suffix `_<units>`.
Writes outputs/tables/gas_cap_consumer_saving.csv (by rho) and gas_cap_consumer_saving_hourly.parquet (rho 0.73).
"""
from __future__ import annotations

import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from gas_cap_quantity_b1 import PANEL  # noqa: E402
from residual_demand import IDENTITY_TOL, cleared_by_period  # noqa: E402
from step_curves import BIDS, DATA, EPS, KEY, VALID_ERR, effective, hid, reclear  # noqa: E402

T = ROOT / "outputs" / "tables"
MONTHS = ["202206", "202207", "202208", "202209", "202210", "202211", "202212", "202301", "202302"]
CAP0, CAP1 = pd.Timestamp("2022-06-15"), pd.Timestamp("2023-02-25")
RHOS = [0.51, 0.54, 0.55, 0.73, 0.75, 1.00, 1.03]
MARGIN = 0.011


def subsidy_and_units() -> tuple[pd.Series, set]:
    h = pd.read_parquet(PANEL, columns=["unit", "date", "iberia", "cost", "subsidy"])
    ib = h[h.iberia & h.cost.notna()]
    s = ib[ib.subsidy > 0].groupby("date").subsidy.max()
    return s[(s.index >= CAP0) & (s.index <= CAP1)], set(ib.unit.astype(str).unique())


def wider(units: set, which: str) -> set:
    if which == "panel":
        return units
    u = pd.read_parquet(ROOT / "data/omie/registry/unit_agents.parquet", columns=["unit", "tech_omie", "tech_omie_early"])
    t = u.tech_omie.fillna(u.tech_omie_early)
    keep = ["gas CCGT", "coal"] + (["cogeneration"] if which == "thermal" else [])
    return units | set(u.unit[t.isin(keep)].astype(str))


def month(ym: str, S: pd.Series, units: set, px: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    for c in ("unit", "side", "status"):
        b[c] = b[c].astype(str)
    days = b.groupby("date").period.max()
    b = b[b.date.isin(days[days == 24].index) & b.date.isin(S.index)]
    idg = cleared_by_period(b)[KEY + ["identity_gap"]]
    b = b.merge(px, on=KEY, how="inner")
    b["hid"] = hid(b.date, b.period)
    b["price_eur_mwh"] = b.price_eur_mwh.astype("float64")
    e = effective(b)
    rc, _ = reclear(e)
    hrs = (b[KEY + ["hid", "p_star", "split"]].drop_duplicates("hid").merge(idg, on=KEY, how="left")
           .merge(rc, on="hid", how="left"))
    hrs["valid"] = ((~hrs.split) & (hrs.identity_gap <= IDENTITY_TOL) & ((hrs.p_clear - hrs.p_star).abs() <= VALID_ERR))
    hrs["S"] = hrs.date.map(S)
    c_buy = b[(b.status == "C") & (b.side == "C")].groupby("hid").power_mw.sum().rename("buy_mw")
    c_sell = b[(b.status == "C") & (b.side == "V") & b.unit.isin(units)].groupby("hid").power_mw.sum().rename("gas_mw")
    hrs = hrs.merge(c_buy, on="hid", how="left").merge(c_sell, on="hid", how="left").fillna({"buy_mw": 0.0, "gas_mw": 0.0})
    mine = e.side.eq("V") & e.unit.isin(units)
    # sell rows of the modelled units at the margin of the actual price
    marg = e[mine & ((e.price_eur_mwh - e.p_star).abs() <= MARGIN) & (e.status == "C")].groupby("hid").size()
    hrs["at_margin"] = hrs.hid.map(marg).fillna(0).astype(int) > 0
    out = {"hid": hrs.hid.to_numpy()}
    Sd = e.date.map(S).to_numpy()
    for r in RHOS:
        e2 = e.copy()
        e2.loc[mine, "price_eur_mwh"] = e.loc[mine, "price_eur_mwh"] + r * Sd[mine.to_numpy()]
        rc1, _ = reclear(e2)
        out[f"p0_{r:.2f}"] = hrs.hid.map(rc1.set_index("hid").p_clear).to_numpy()
    p0 = pd.DataFrame(out)
    return hrs, p0


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*")
    ap.add_argument("--units", choices=["panel", "ccgt_coal", "thermal"], default="panel")
    a = ap.parse_args()
    sfx = "" if a.units == "panel" else f"_{a.units}"
    months = [m for m in MONTHS if not a.months or m in a.months]
    S, units = subsidy_and_units()
    units = wider(units, a.units)
    print(f"{len(units)} units ({a.units}); subsidy on {len(S)} days (mean S {S.mean():.1f})")
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["date", "period", "price_es", "price_pt", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    px = px[px.resolution_min == 60]
    px = px.assign(split=px.price_es != px.price_pt).rename(columns={"price_es": "p_star"})[KEY + ["p_star", "split"]]
    hs = []
    for ym in months:
        t0 = time.time()
        hrs, p0 = month(ym, S, units, px)
        hs.append(hrs.merge(p0, on="hid"))
        v = hrs[hrs.valid]
        print(f"  {ym}: {len(hrs)} hours, valid {hrs.valid.mean():.3f}, unit at margin {hrs.at_margin.mean():.3f} "
              f"({time.time() - t0:.0f} s)", flush=True)
    H = pd.concat(hs, ignore_index=True)
    V = H[H.valid]
    bill = float((V.S * V.gas_mw).sum() / 1e6)
    print(f"\nvalid hours {len(V):,} of {len(H):,} ({len(V) / len(H):.1%}); subsidy bill B on these units, valid hours: EUR {bill:,.0f} m "
          f"(all hours EUR {float((H.S * H.gas_mw).sum() / 1e6):,.0f} m); unit at the margin in {V.at_margin.mean():.1%} of valid hours")
    rows = []
    for r in RHOS:
        d = V[f"p0_{r:.2f}"] - V.p_clear
        g = float((d * V.buy_mw).sum() / 1e6)
        rows.append({"rho": r, "gross_eur_m": g, "bill_eur_m": bill, "net_eur_m": g - bill,
                     "hours_price_moves": float((d.abs() > 0.011).mean()), "mean_drop": float(d.mean()),
                     "p95_drop": float(d.quantile(0.95)), "max_drop": float(d.max())})
        print(f"  rho {r:.2f}: gross EUR {g:,.0f} m, net of the bill EUR {g - bill:,.0f} m; price moves in {rows[-1]['hours_price_moves']:.1%} "
              f"of hours, mean {d.mean():.2f}, p95 {d.quantile(0.95):.2f}, max {d.max():.1f} EUR/MWh")
    pd.DataFrame(rows).to_csv(T / f"gas_cap_consumer_saving{sfx}.csv", index=False)
    H[["hid", "date", "period", "valid", "S", "p_clear", "buy_mw", "gas_mw", "at_margin", "p0_0.73"]].to_parquet(
        T / f"gas_cap_consumer_saving_hourly{sfx}.parquet", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
