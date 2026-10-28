#!/usr/bin/env python3
"""The gas cap's pass-through read on the cost plants declare themselves (descriptive, no estimation).

    .venv/bin/python scripts/analysis/gas_cap_declared_cost.py

Idea from the 2026-10-28 repo sweep (`notes/rq-gas-cap-declared-cost.md`). Every Iberian combined
cycle declares, each day, the variable term of its minimum-income condition in `cab`
(`min_income_var_eur_mwh`, EUR/MWh, published to 2025-03-18). Before the cap it sits at a steady
multiple of the plant's implied fuel-and-carbon cost; the question is how much of the decree's
subsidy (RDL 10/2022, from delivery day 2022-06-15) it lost.

Units: the Iberian gas units of `gas_cap_offer_panel.parquet` (plant-specific efficiency),
Turbogas (`RTG*`) out (it declares round numbers unrelated to cost). Unit-days with a declared
term in (0, 999) only (999 means "never run"). Two subsidy timings, both from
`implied_marginal_cost_daily.parquet`: `bid` (prices final at 12:00 on D-1, as offers were
made) and `delivery` (the decree's own, day D).

Reading for each unit-day: r_ref = the unit's mean declared/gross ratio over 2022-03-15 ->
2022-06-14. Had the plant kept that ratio and passed a share rho of the subsidy S:
v = r_ref * (gross - rho * S), so rho = (gross - v / r_ref) / S, read where S >= 20.

Writes outputs/tables/gas_cap_declared_cost_{daily,event,monthly,firm}.csv:
  daily    median declared term, gross cost, subsidy, and the term at rho = 0 and rho = 1,
           around the start (June 2022) and the end (2023-01-15 -> 2023-03-15)
  event    J(D) = median over units of the change in mean log(declared/gross) from the 7 days
           before D to the 7 days from D; the actual date 2022-06-15 against every placebo date
           2021-09-08 -> 2022-06-07 (windows wholly before the cap)
  monthly  median declared/gross, declared/net and rho by month, both timings
  firm     median rho June -> October 2022 by firm and by country, bid timing
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
T = ROOT / "outputs" / "tables"
START, END = pd.Timestamp("2021-06-01"), pd.Timestamp("2023-06-30")
CAP = pd.Timestamp("2022-06-15")
REF = (pd.Timestamp("2022-03-15"), pd.Timestamp("2022-06-14"))
MIN_S = 20.0


def panel() -> pd.DataFrame:
    p = pd.read_parquet(T / "gas_cap_offer_panel.parquet", columns=["unit", "iberia", "country", "firm", "date"])
    p = p[p.iberia & ~p.unit.str.startswith("RTG")]
    p["date"] = pd.to_datetime(p.date)
    units = p.drop_duplicates(["unit", "date"])[["unit", "date", "country", "firm"]]
    c = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "marginal_cost_bid_eur_mwh", "subsidy_bid_eur_mwh",
                                 "marginal_cost_eur_mwh", "subsidy_eur_mwh"])
    c["date"] = pd.to_datetime(c.date)
    c = c.rename(columns={"marginal_cost_bid_eur_mwh": "gross_bid", "subsidy_bid_eur_mwh": "s_bid",
                          "marginal_cost_eur_mwh": "gross_del", "subsidy_eur_mwh": "s_del"})
    months = pd.period_range(START, END, freq="M")
    cab = pd.concat([pd.read_parquet(DATA / f"omie/cab/parquet/cab_{m.strftime('%Y%m')}.parquet",
                                     columns=["unit", "date", "min_income_var_eur_mwh"]) for m in months])
    cab["date"] = pd.to_datetime(cab.date)
    cab = cab.groupby(["unit", "date"], as_index=False).min_income_var_eur_mwh.first().rename(
        columns={"min_income_var_eur_mwh": "v"})
    d = units.merge(c, on=["unit", "date"]).merge(cab, on=["unit", "date"])
    d = d[(d.v > 0) & (d.v < 999) & d.date.between(START, END)].copy()
    for t in ("bid", "del"):
        d[f"net_{t}"] = d[f"gross_{t}"] - d[f"s_{t}"]
        d[f"r_{t}"] = d.v / d[f"gross_{t}"]
        ref = d[d.date.between(*REF)].groupby("unit")[f"r_{t}"].mean().rename(f"rref_{t}")
        d = d.merge(ref, on="unit", how="left")
        d[f"rho_{t}"] = np.where(d[f"s_{t}"] >= MIN_S,
                                 (d[f"gross_{t}"] - d.v / d[f"rref_{t}"]) / d[f"s_{t}"], np.nan)
    return d


def daily(d: pd.DataFrame) -> pd.DataFrame:
    w = d[d.date.between("2022-06-01", "2022-06-30") | d.date.between("2023-01-15", "2023-03-15")]
    w = w.assign(v_rho0=w.rref_bid * w.gross_bid, v_rho1=w.rref_bid * w.net_bid)
    return w.groupby("date").agg(units=("unit", "nunique"), declared=("v", "median"),
                                 gross_bid=("gross_bid", "median"), subsidy_bid=("s_bid", "median"),
                                 subsidy_delivery=("s_del", "median"), net_bid=("net_bid", "median"),
                                 declared_if_rho0=("v_rho0", "median"),
                                 declared_if_rho1=("v_rho1", "median")).round(1)


def jump(d: pd.DataFrame, day: pd.Timestamp) -> float:
    x = d[d.date.between(day - pd.Timedelta(days=7), day + pd.Timedelta(days=6))]
    x = x.assign(lr=np.log(x.v / x.gross_bid), post=x.date >= day)
    m = x.groupby(["unit", "post"]).lr.mean().unstack()
    return float((m[True] - m[False]).dropna().median())


def event(d: pd.DataFrame) -> pd.DataFrame:
    rows = [{"date": CAP, "kind": "actual", "J": jump(d, CAP)}]
    for day in pd.date_range("2021-09-08", CAP - pd.Timedelta(days=8)):
        rows.append({"date": day, "kind": "placebo", "J": jump(d, day)})
    e = pd.DataFrame(rows)
    first = d[d.date.between(CAP, CAP + pd.Timedelta(days=6))]
    e["J_if_full_passthrough"] = float(np.log(first.net_bid / first.gross_bid).median())
    return e


def monthly(d: pd.DataFrame) -> pd.DataFrame:
    d = d.assign(ym=d.date.dt.strftime("%Y-%m"), r_net_bid=d.v / d.net_bid)
    return d.groupby("ym").agg(units=("unit", "nunique"), declared_over_gross=("r_bid", "median"),
                               declared_over_net=("r_net_bid", "median"), subsidy_bid=("s_bid", "median"),
                               rho_bid=("rho_bid", "median"), rho_delivery=("rho_del", "median")).round(3)


def by_firm(d: pd.DataFrame) -> pd.DataFrame:
    w = d[d.date.between("2022-06-15", "2022-10-31") & d.rho_bid.notna()]
    f = w.groupby("firm").agg(units=("unit", "nunique"), unit_days=("rho_bid", "size"), rho_bid=("rho_bid", "median"),
                              rho_delivery=("rho_del", "median"))
    c = w.groupby("country").agg(units=("unit", "nunique"), unit_days=("rho_bid", "size"), rho_bid=("rho_bid", "median"),
                                 rho_delivery=("rho_del", "median"))
    return pd.concat([f.assign(level="firm"), c.assign(level="country")]).round(3)


def main() -> int:
    d = panel()
    print(f"{len(d):,} unit-days, {d.unit.nunique()} units, {d.date.min().date()} -> {d.date.max().date()}")
    out = {"daily": daily(d), "event": event(d), "monthly": monthly(d), "firm": by_firm(d)}
    for k, v in out.items():
        v.to_csv(T / f"gas_cap_declared_cost_{k}.csv")
    with pd.option_context("display.width", 200):
        print(out["daily"].loc["2022-06-08":"2022-06-22"].to_string())
        print(out["daily"].loc["2023-02-15":"2023-03-06"].to_string())
        e = out["event"]
        pl = e[e.kind == "placebo"].J
        a = e[e.kind == "actual"].J.iloc[0]
        print(f"\nevent: J(2022-06-15) {a:+.3f}; full pass-through would give {e.J_if_full_passthrough.iloc[0]:+.3f}; "
              f"placebo ({len(pl)} dates) 2.5/50/97.5% {pl.quantile(.025):+.3f} / {pl.median():+.3f} / {pl.quantile(.975):+.3f}, "
              f"min {pl.min():+.3f}")
        print(out["monthly"].to_string())
        print(out["firm"].to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
