#!/usr/bin/env python3
"""Unit-day panel of cogeneration offer units: scheduled energy, load factor and day-ahead offers.

    .venv/bin/python scripts/build/build_cogeneration_panel.py [--force]

Design: docs/specs/2026-11-10-cogeneration-design.md (step 0). Units: data/omie/registry/cogeneration_units.parquet.
Writes outputs/tables/cogeneration_panel/panel_YYYYMM.parquet, 2019-01 -> 2023-12, one row per unit and day on
which the unit has a schedule, an offer or an offer header:

- energy_mwh: PDBF schedule, all role codes summed (schedule_mw x resolution_min / 60); bilateral_mwh: role code 4.
- max_power_mw: that day's sell-side `cab` maximum power; the registry's median when the day has no header.
- load_factor = energy_mwh / (max_power_mw x hours in the day); null when the capacity is null or zero.
  run = load_factor > 0.10.
- offered_mwh, cleared_mwh: day-ahead sell offers (status O) and their accepted part (status C).
- offer_price: MW-weighted mean price of the offered sell rows; share_at_zero: offered MW priced <= 1 EUR/MWh.
- price_es: the day's mean Spanish day-ahead price; hours: 23, 24 or 25.

Resumable: a month already on disk is skipped unless --force.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
REG = ROOT / "data" / "omie" / "registry" / "cogeneration_units.parquet"
OUT = ROOT / "outputs" / "tables" / "cogeneration_panel"
RUN_ABOVE = 0.10


def prices() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data" / "omie" / "prices" / "omie_day_ahead_prices.parquet",
                        columns=["date", "price_es", "resolution_min"])
    p["date"] = p.date.astype(str)
    g = p.groupby("date").agg(price_es=("price_es", "mean"), hours=("resolution_min", lambda r: r.sum() / 60))
    return g.reset_index()


def month(ym: str, reg: pd.DataFrame, P: pd.DataFrame) -> pd.DataFrame:
    units = set(reg.unit)
    d = pd.read_parquet(ROOT / "data" / "omie" / "pdbf" / "parquet" / f"pdbf_{ym}.parquet",
                        columns=["date", "unit", "schedule_mw", "resolution_min", "role_code"])
    d = d[d.unit.isin(units)]
    d["mwh"] = d.schedule_mw * d.resolution_min / 60
    d["bil"] = d.mwh.where(d.role_code == "4", 0.0)
    d["date"] = d.date.astype(str)
    sched = d.groupby(["unit", "date"]).agg(energy_mwh=("mwh", "sum"), bilateral_mwh=("bil", "sum"))

    c = pd.read_parquet(ROOT / "data" / "omie" / "cab" / "parquet" / f"cab_{ym}.parquet",
                        columns=["date", "unit", "side", "max_power_mw"])
    c = c[c.unit.isin(units) & (c.side == "V")]
    c["date"] = c.date.astype(str)
    cap = c.groupby(["unit", "date"]).max_power_mw.max().rename("cab_mw")

    b = pd.read_parquet(ROOT / "data" / "omie" / "bids" / "parquet" / f"bids_{ym}.parquet",
                        columns=["date", "unit", "side", "power_mw", "price_eur_mwh", "status", "resolution_min"])
    b = b[b.unit.astype(str).isin(units) & (b.side == "V")]
    b = b.assign(unit=b.unit.astype(str), date=b.date.astype(str), status=b.status.astype(str),
                 mwh=b.power_mw.astype("float64") * b.resolution_min / 60)
    o = b[b.status == "O"].assign(pm=lambda x: x.mwh * x.price_eur_mwh, z=lambda x: x.mwh.where(x.price_eur_mwh <= 1, 0.0))
    og = o.groupby(["unit", "date"]).agg(offered_mwh=("mwh", "sum"), pm=("pm", "sum"), z=("z", "sum"))
    og["offer_price"] = og.pm / og.offered_mwh.where(og.offered_mwh > 0)
    og["share_at_zero"] = og.z / og.offered_mwh.where(og.offered_mwh > 0)
    cl = b[b.status == "C"].groupby(["unit", "date"]).mwh.sum().rename("cleared_mwh")

    out = pd.concat([sched, cap, og[["offered_mwh", "offer_price", "share_at_zero"]], cl], axis=1).reset_index()
    out = out.merge(P, on="date", how="left").merge(reg[["unit", "max_power_mw"]].rename(
        columns={"max_power_mw": "reg_mw"}), on="unit", how="left")
    out["max_power_mw"] = out.cab_mw.fillna(out.reg_mw)
    for col in ["energy_mwh", "bilateral_mwh", "offered_mwh", "cleared_mwh"]:
        out[col] = out[col].fillna(0.0)
    cap_ok = out.max_power_mw.where(out.max_power_mw > 0)
    out["load_factor"] = out.energy_mwh / (cap_ok * out.hours)
    out["run"] = (out.load_factor > RUN_ABOVE).where(out.load_factor.notna())
    return out.drop(columns=["cab_mw", "reg_mw"]).sort_values(["unit", "date"])


def main() -> int:
    force = "--force" in sys.argv
    reg = pd.read_parquet(REG)
    P = prices()
    OUT.mkdir(parents=True, exist_ok=True)
    for per in pd.period_range("2019-01", "2023-12", freq="M"):
        ym = per.strftime("%Y%m")
        f = OUT / f"panel_{ym}.parquet"
        if f.exists() and not force:
            continue
        m = month(ym, reg, P)
        m.to_parquet(f, index=False)
        print(f"{ym}: {len(m):,} unit-days, {m.unit.nunique()} units, {m.energy_mwh.sum() / m.hours.groupby(m.date).first().sum():,.0f} MW mean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
