#!/usr/bin/env python3
"""Step 0 descriptive tables for the cogeneration design: output by group, how units offer, how often they switch.

    .venv/bin/python scripts/analysis/cogeneration_describe.py

Design: docs/specs/2026-11-10-cogeneration-design.md. Counts, sums and shares only; nothing is estimated.
Reads data/omie/registry/cogeneration_units.parquet and outputs/tables/cogeneration_panel/. Groups:
  gas_entered         matched to an REE gas plant, unit new after the cap
  gas_not_entered     matched to an REE gas plant, earlier unit
  nonren_new          non-renewable label, fuel unknown, unit new after the cap
  nonren_unknown      non-renewable label, fuel unknown, earlier unit
  other_fossil, renewable (label or biomass/waste fuel); portfolio units are reported as `portfolio`.
Writes outputs/tables/cogeneration_describe_{group_month,offers,switches}.csv and prints gates G0 and G5.
"""
from __future__ import annotations

import glob
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
REG = ROOT / "data" / "omie" / "registry" / "cogeneration_units.parquet"
DIR = ROOT / "outputs" / "tables" / "cogeneration_panel"
OUT = ROOT / "outputs" / "tables"


def group(r) -> str:
    if r.portfolio:
        return "portfolio"
    if r.label == "renew" or r.fuel == "biomass_waste":
        return "renewable"
    if r.fuel == "gas":
        return "gas_entered" if r.new_after_cap else "gas_not_entered"
    if r.fuel == "other_fossil":
        return "other_fossil"
    return "nonren_new" if r.new_after_cap else "nonren_unknown"


def main() -> int:
    reg = pd.read_parquet(REG)
    reg["group"] = [group(r) for r in reg.itertuples()]
    p = pd.concat(pd.read_parquet(f) for f in sorted(glob.glob(str(DIR / "panel_*.parquet"))))
    p = p.merge(reg[["unit", "group"]], on="unit")
    p["ym"] = p.date.str[:7]
    hours = p.groupby("date").hours.first().groupby(lambda d: d[:7]).sum()

    gm = p.groupby(["ym", "group"]).agg(mwh=("energy_mwh", "sum"), load_factor=("load_factor", "mean"),
                                        share_running=("run", lambda s: s.dropna().astype(float).mean())).reset_index()
    gm["mean_mw"] = gm.mwh / gm.ym.map(hours)
    gm["units_active"] = gm.set_index(["ym", "group"]).index.map(
        p[p.energy_mwh > 0].groupby(["ym", "group"]).unit.nunique()).fillna(0).astype(int)
    gm.drop(columns="mwh").round(3).to_csv(OUT / "cogeneration_describe_group_month.csv", index=False)
    print("mean MW by group, selected months")
    print(gm.pivot(index="ym", columns="group", values="mean_mw").round(0)
          .loc[["2021-06", "2022-03", "2022-05", "2022-06", "2022-07", "2022-09", "2022-11", "2023-02", "2023-06"]]
          .to_string())
    tot = gm.groupby("ym").mean_mw.sum()
    print(f"all groups, 2022-03: {tot['2022-03']:,.0f} MW; 2022-09: {tot['2022-09']:,.0f} MW")

    p["half"] = p.date.str[:4] + "H" + (((p.date.str[5:7].astype(int) - 1) // 6) + 1).astype(str)
    o = p[p.offered_mwh > 0].groupby(["half", "group", "unit"]).agg(z=("share_at_zero", "median"),
                                                                 price=("offer_price", "median")).reset_index()
    o["reservation"] = o.z < 0.5
    of = o.groupby(["half", "group"]).agg(units=("unit", "size"), share_reservation=("reservation", "mean")).reset_index()
    med = o[o.reservation].groupby(["half", "group"]).price.median().rename("median_price")
    of = of.merge(med, on=["half", "group"], how="left")
    of.round(3).to_csv(OUT / "cogeneration_describe_offers.csv", index=False)
    print("\nshare of units offering most of their MW above 1 EUR/MWh (a stated reservation price)")
    print(of.pivot(index="half", columns="group", values="share_reservation").round(2).to_string())

    y = p[(p.date.str[:4] == "2022") & (p.group != "portfolio") & (p.group != "renewable") & p.run.notna()]
    y = y.sort_values(["unit", "date"])
    y["run"] = y.run.astype(bool)
    y["chg"] = y.groupby("unit").run.transform(lambda s: s != s.shift()).astype(int)
    y.loc[y.groupby("unit").head(1).index, "chg"] = 0
    sw = y.groupby(["unit", "group"]).agg(switches=("chg", "sum"), days=("run", "size"),
                                          share_running=("run", "mean")).reset_index()
    sw.to_csv(OUT / "cogeneration_describe_switches.csv", index=False)
    y["spell"] = y.groupby("unit").chg.cumsum()
    sp = y.groupby(["unit", "spell"]).size()
    print(f"\nnon-renewable, non-portfolio units with a load factor in 2022: {len(sw)}")
    print(f"gate G5: units with >= 10 run/stop switches in 2022: {(sw.switches >= 10).sum()} (needs 100)")
    print(f"  of which matched to gas: {((sw.switches >= 10) & sw.group.str.startswith('gas')).sum()}")
    print(f"run or stop spells lasting under two days: {(sp < 2).mean():.1%} of {len(sp):,} spells")

    a = reg[(reg.label == "nonren") & reg.mw_202201.notna()]
    print(f"gate G0: fuel known for {a[a.fuel.notna()].mw_202201.sum() / a.mw_202201.sum():.1%} of non-renewable "
          f"capacity offering in January 2022 (needs 60%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
