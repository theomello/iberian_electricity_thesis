#!/usr/bin/env python3
"""Who sells to Iberdrola's retail units on bilateral contracts?

    .venv/bin/python scripts/analysis/iberdrola_contract_trace.py

`notes/rq-midday-hydro.md` §3.8. Iberdrola's storage hydro self-supplies its
retail units, and within a day its OTHER bilateral contracts flex against that
self-supply (`iberdrola_self_supply.py`). Those other receipts also fell from
about 9-10 GWh per hour in 2019-22 to 1-4 in 2023-25. This traces them.

METHOD

PDBF role-4 rows carry a contract id in `unit_id` (CLAUDE.md, PDBF section), and
a contract's sell and buy legs balance to zero in every period. For every
contract-period with a buy leg on an Iberdrola retail unit, each SELL leg on the
same contract id is credited with

    seller MWh x (Iberdrola retail buy MWh / all buy MWh on that contract-period)

so a contract shared with other buyers is not all attributed to Iberdrola.
Sellers are labelled by the owner groups in force that day, each with its share
(`lib/unit_ownership.py`, 2026-10-05; a co-owned reactor's sale is split), and by
technology (OMIE's listing, projected label, then the `cab` name), and the
storage-hydro units already traced (HYDRO) are shown as their own row.

Three sample months a year (Feb, Jun, Oct), as in `firm_net_position.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from iberdrola_self_supply import HYDRO, iberdrola_purchase_units  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402

DATA = ROOT / "data"
MONTHS = ("02", "06", "10")


def labels() -> pd.DataFrame:
    u = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet",
                        columns=["unit", "descr", "tech", "tech_omie", "tech_omie_early"])
    u["techl"] = u.tech_omie.fillna(u.tech_omie_early).fillna(u.tech).fillna("unknown")
    return u.set_index("unit")[["descr", "techl"]]


def month_trace(ym: str, retail: list[str], lab: pd.DataFrame, sp: pd.DataFrame) -> pd.DataFrame:
    f = DATA / f"omie/pdbf/parquet/pdbf_{ym}.parquet"
    if not f.exists():
        return pd.DataFrame()
    p = pq.read_table(f, columns=["date", "period", "resolution_min", "unit", "unit_id",
                                  "schedule_mw"],
                      filters=[("role_code", "==", "4")]).to_pandas()
    p["mwh"] = p.schedule_mw * p.resolution_min / 60
    key = ["date", "period", "unit_id"]
    buys = p[p.mwh < 0]
    ib = buys[buys.unit.isin(retail)].groupby(key).mwh.sum().rename("ib_buy")
    if ib.empty:
        return pd.DataFrame()
    allb = buys.groupby(key).mwh.sum().rename("all_buy")
    share = (ib / allb).rename("share").reset_index()
    sells = p[p.mwh > 0].merge(share, on=key, how="inner")
    sells["to_ib"] = sells.mwh * sells.share
    # The seller's owners in force that day, each with its share of the energy
    # (lib/unit_ownership.py, 2026-10-05): a co-owned reactor's sale is split.
    sells["date"] = pd.to_datetime(sells.date)
    sells["unit"] = sells.unit.astype(str)
    sells = attach_owners(sells.drop(columns="share"), sp, value_cols=("to_ib",))
    sells["owner"] = sells.group.fillna("UNMAPPED")
    out = sells.groupby(["unit", "owner"]).agg(twh=("to_ib", "sum"),
                                               contracts=("unit_id", "nunique")).reset_index()
    out["twh"] /= 1e6
    out = out.join(lab, on="unit")
    out["year"] = int(ym[:4])
    return out


def main() -> int:
    retail = iberdrola_purchase_units()
    lab = labels()
    sp = spells()
    parts = [month_trace(f"{y}{m}", retail, lab, sp) for y in range(2018, 2027) for m in MONTHS]
    d = pd.concat([x for x in parts if not x.empty], ignore_index=True)
    d["source"] = d.owner + " / " + d.techl
    d.loc[d.unit.isin(HYDRO), "source"] = "IBERDROLA / storage hydro (traced, §3.8)"

    tot = d.groupby("year").twh.sum()
    print("Energy received by Iberdrola's retail units on bilateral contracts, TWh over "
          "Feb + Jun + Oct")
    print(tot.round(2).to_frame("all").T.to_string(), "\n")

    top = d.groupby("source").twh.sum().sort_values(ascending=False)
    keep = top.index[:12]
    t = d.assign(src=d.source.where(d.source.isin(keep), "other")).pivot_table(
        index="src", columns="year", values="twh", aggfunc="sum").fillna(0.0)
    t = t.loc[list(keep) + (["other"] if "other" in t.index else [])]
    print("BY SELLER owner / technology, TWh")
    print(t.round(2).to_string(), "\n")

    print("SELLER OWNER GROUPS: share of receipts by year")
    g = d.pivot_table(index="owner", columns="year", values="twh", aggfunc="sum").fillna(0.0)
    g = (g / g.sum()).round(3)
    print(g.loc[g.max(axis=1) > 0.01].sort_values(g.columns[0], ascending=False).to_string(), "\n")

    print("LARGEST SELLING UNITS, 2018-2022 vs 2023-2026, TWh")
    d["era"] = d.year.map(lambda y: "2018-22" if y <= 2022 else "2023-26")
    u = d.pivot_table(index=["unit", "descr", "owner", "techl"], columns="era", values="twh",
                      aggfunc="sum").fillna(0.0)
    u["drop"] = u.get("2018-22", 0) - u.get("2023-26", 0)
    print(u.sort_values("drop", ascending=False).head(12).round(2).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
