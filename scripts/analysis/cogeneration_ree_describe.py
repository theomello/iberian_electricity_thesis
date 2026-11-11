#!/usr/bin/env python3
"""Cogeneration by plant and day from REE's programming units: counts and sums, no estimate.

    .venv/bin/python scripts/analysis/cogeneration_ree_describe.py

Reads outputs/tables/cogeneration_ree/ (build/build_cogeneration_ree_panel.py) and, for the comparison, the OMIE
cogeneration panel. Daily coverage is 2022-04-01 -> 2023-03-31; outside it only the 15th of each month. Writes
outputs/tables/cogeneration_ree_{daily,monthly,events,entrants,switches}.csv and prints them.

  daily     average MW of the final schedule (P48) by fuel and day, and the units running
  monthly   the same by month, beside OMIE's non-renewable thermal units (PDBF), for coverage
  events    the 14 days before and after 15 June 2022 (gas cap starts; cogeneration in the regulated payment scheme
            excluded) and 1 October 2022 (it may opt in, RDL 17/2022)
  entrants  gas units first seen in each month of the daily window, and their MW
  switches  per gas unit: days seen, days running (above 10% of its largest day), run/stop switches
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
REE = ROOT / "outputs" / "tables" / "cogeneration_ree"
OUT = ROOT / "outputs" / "tables"
DAILY0, DAILY1 = "2022-04-01", "2023-03-31"
EVENTS = {"gas cap starts": "2022-06-15", "opt-in allowed": "2022-10-01"}
RUN = 0.10


def load() -> tuple[pd.DataFrame, pd.DataFrame]:
    d = pd.concat(pd.read_parquet(f) for f in sorted((REE / "days").glob("ree_*.parquet")))
    u = pd.read_parquet(REE / "ree_units.parquet")
    d = d.merge(u[["unit", "fuel", "in_register", "tech", "peak_mw"]], on="unit", how="left")
    d["group"] = d.fuel.fillna("not cogeneration").where(d.in_register.fillna(False), "not in register")
    d["mw"] = d.p48_mwh / 24
    return d, u


def omie_monthly() -> pd.Series:
    reg = pd.read_parquet(ROOT / "data" / "omie" / "registry" / "cogeneration_units.parquet")[["unit", "label"]]
    p = pd.concat(pd.read_parquet(f, columns=["date", "unit", "energy_mwh"])
                  for f in sorted((OUT / "cogeneration_panel").glob("panel_202[123]*.parquet")))
    p = p.merge(reg, on="unit")
    p = p[p.label == "nonren"]
    day = p.groupby("date").energy_mwh.sum() / 24
    return day.groupby(pd.to_datetime(day.index).to_period("M")).mean().rename("omie_nonren_mw")


def main() -> int:
    d, u = load()
    cog = d[d.group.isin(["gas", "other_fossil", "biomass_waste"])]

    daily = cog.pivot_table(index="date", columns="group", values="mw", aggfunc="sum").round(0)
    daily["gas_units_running"] = cog[(cog.group == "gas") & (cog.mw > RUN * cog.peak_mw)].groupby("date").unit.nunique()
    daily.to_csv(OUT / "cogeneration_ree_daily.csv")

    m = daily.groupby(pd.to_datetime(daily.index).to_period("M")).mean().round(0)
    m["days"] = daily.groupby(pd.to_datetime(daily.index).to_period("M")).size()
    m = m.join(omie_monthly().round(0))
    m["ree_fossil_over_omie"] = ((m.gas + m.other_fossil) / m.omie_nonren_mw).round(2)
    m.to_csv(OUT / "cogeneration_ree_monthly.csv")
    print("average MW by month (P48), REE programming units with a cogeneration fuel\n" + m.to_string())

    rows = []
    idx = pd.to_datetime(daily.index)
    for name, day in EVENTS.items():
        t = pd.Timestamp(day)
        for lab, sel in (("14 days before", (idx >= t - pd.Timedelta(days=14)) & (idx < t)),
                         ("14 days after", (idx >= t) & (idx < t + pd.Timedelta(days=14)))):
            rows.append({"event": name, "date": day, "window": lab, **daily[sel].mean().round(0).to_dict()})
    ev = pd.DataFrame(rows)
    ev.to_csv(OUT / "cogeneration_ree_events.csv", index=False)
    print("\naround the two dates\n" + ev.to_string(index=False))

    win = d[(d.date >= DAILY0) & (d.date <= DAILY1) & (d.p48_mwh > 0)]
    before = set(d[(d.date < DAILY0) & (d.p48_mwh > 0)].unit)
    first = win.groupby("unit").date.min()
    g = u[u.fuel == "gas"].set_index("unit")
    new = first[first.index.isin(g.index) & ~first.index.isin(before) & (first > DAILY0)]
    ent = pd.DataFrame({"first": new, "mw": g.max_power_mw.reindex(new.index), "peak_mw": g.peak_mw.reindex(new.index)})
    e = ent.groupby(pd.to_datetime(ent["first"]).dt.to_period("M")).agg(units=("mw", "size"), register_mw=("mw", "sum"),
                                                                       peak_mw=("peak_mw", "sum")).round(0)
    e.to_csv(OUT / "cogeneration_ree_entrants.csv")
    print("\ngas units first seen in the daily window (not on any sampled day from 2021-01)\n" + e.to_string())
    ent.sort_values("first").to_csv(OUT / "cogeneration_ree_entrant_units.csv")

    # A unit with no schedule may have no row that day: fill every day between its first and last as stopped.
    w = d[(d.date >= DAILY0) & (d.date <= DAILY1) & (d.group == "gas")]
    grid = w.pivot_table(index="date", columns="unit", values="mw", aggfunc="sum")
    grid = grid.where(grid.notna() | ~(grid.ffill().notna() & grid.bfill().notna()), 0.0)
    w = grid.stack().rename("mw").reset_index().merge(u[["unit", "peak_mw"]], on="unit").sort_values(["unit", "date"])
    w["run"] = w.mw > RUN * w.peak_mw
    sw = w.groupby("unit").agg(days=("date", "size"), run_days=("run", "sum"),
                               switches=("run", lambda s: int((s != s.shift()).iloc[1:].sum())),
                               peak_mw=("peak_mw", "first"))
    sw.to_csv(OUT / "cogeneration_ree_switches.csv")
    print(f"\ngas units in the daily window: {len(sw)}; with at least 10 run/stop switches: {(sw.switches >= 10).sum()} "
          f"({sw[sw.switches >= 10].peak_mw.sum():,.0f} MW); never stopped: {(sw.run_days == sw.days).sum()}; "
          f"median switches {sw.switches.median():.0f}")

    tot = d[(d.date >= DAILY0) & (d.date <= DAILY1)].groupby("group").agg(units=("unit", "nunique"), twh=("p48_mwh", "sum"))
    tot["twh"] = (tot.twh / 1e6).round(2)
    print("\nall programming units in the daily window, final schedule\n" + tot.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
