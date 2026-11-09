#!/usr/bin/env python3
"""Unit x hour panel of the direct consumers' day-ahead buy bids, 2018-01 -> the bid frontier.

    .venv/bin/python scripts/build/build_direct_consumer_panel.py [--months 202401 ...] [--force]

Units: every unit in data/omie/registry/direct_consumers.parquet (all kinds; filter on `kind` downstream).
For each unit and delivery period, from curva_pbc_uof buy rows (side C):

    q_cleared            MW accepted (status C)
    q_offered            MW offered at any price (status O)
    q_p                  offered MW at a bid price >= p*, the unit's zonal clearing price: demand at the price
    q_m50, q_m10,        offered MW at bid >= p* - 50, - 10, + 10, + 50: the curve around the price
    q_p10, q_p50
    bid_wavg             MW-weighted mean bid price of the offered rows

then averaged over the periods of each hour (15-minute era: four quarters), so quantities stay MW. p* is price_es for
Spanish units and price_pt for Portuguese ones (unit_registry country; ES when unknown).

Offer limits: bids were bounded to [0, 180.30] EUR/MWh until 2021-07-06 and to [-500, 3000] after
(CLAUDE.md); a bid at the top of the range means "buy at any price" in both eras, so compare price-sensitive shares
within an era.

Writes outputs/tables/direct_consumer_panel/panel_YYYYMM.parquet (gitignored), one per month, skipped if present.
"""
from __future__ import annotations

import argparse
import glob
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables" / "direct_consumer_panel"
OFFSETS = {"q_m50": -50.0, "q_m10": -10.0, "q_p": 0.0, "q_p10": 10.0, "q_p50": 50.0}


def prices() -> pd.DataFrame:
    p = pd.read_parquet(ROOT / "data/omie/prices/omie_day_ahead_prices.parquet",
                        columns=["date", "period", "price_es", "price_pt", "utc_timestamp"])
    p["date"] = pd.to_datetime(p.date).dt.date.astype(str)
    return p


def month(f: str, units: pd.Series, P: pd.DataFrame) -> pd.DataFrame | None:
    b = pd.read_parquet(f, columns=["date", "period", "hour", "resolution_min", "unit", "side", "power_mw",
                                    "price_eur_mwh", "status"], filters=[("side", "==", "C")])
    b = b[b.unit.isin(units.index)]
    if not len(b):
        return None
    b["date"] = b.date.astype(str)
    if not b.date.isin(set(P.date)).any():
        return None  # bids past the price frontier
    b["unit"] = b.unit.astype(str)
    b["status"] = b.status.astype(str)
    b = b.merge(P, on=["date", "period"], how="inner")
    pt = b.unit.map(units).eq("PT").to_numpy()
    b["p"] = np.where(pt, b.price_pt, b.price_es)
    o = b[b.status == "O"].copy()
    c = b[b.status == "C"]
    key = ["date", "period", "unit"]
    for col, off in OFFSETS.items():
        o[col] = o.power_mw.where(o.price_eur_mwh >= o.p + off, 0.0)
    o["pq"] = o.power_mw * o.price_eur_mwh
    g = o.groupby(key, observed=True).agg(q_offered=("power_mw", "sum"), pq=("pq", "sum"),
                                          **{k: (k, "sum") for k in OFFSETS})
    g["bid_wavg"] = g.pq / g.q_offered.where(g.q_offered > 0)
    g = g.drop(columns="pq")
    g["q_cleared"] = c.groupby(key, observed=True).power_mw.sum()
    g["q_cleared"] = g.q_cleared.fillna(0.0)
    per = b.groupby(key, observed=True).agg(hour=("hour", "first"), p=("p", "first"), utc=("utc_timestamp", "first"),
                                            resolution_min=("resolution_min", "first"))
    g = g.join(per).reset_index()
    h = g.groupby(["date", "hour", "unit"], observed=True).agg(
        utc=("utc", "min"), resolution_min=("resolution_min", "first"), p=("p", "mean"),
        q_cleared=("q_cleared", "mean"), q_offered=("q_offered", "mean"), bid_wavg=("bid_wavg", "mean"),
        **{k: (k, "mean") for k in OFFSETS}).reset_index()
    return h


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()
    reg = pd.read_parquet(ROOT / "data/omie/registry/direct_consumers.parquet")
    ur = pd.read_parquet(ROOT / "data/omie/registry/unit_registry.parquet", columns=["unit", "country"])
    country = reg.unit.map(ur.set_index("unit").country).fillna("ES")
    units = pd.Series(country.to_numpy(), index=reg.unit)
    P = prices()
    OUT.mkdir(parents=True, exist_ok=True)
    files = sorted(glob.glob(str(ROOT / "data/omie/bids/parquet/bids_*.parquet")))
    if a.months:
        files = [f for f in files if Path(f).stem[-6:] in a.months]
    tot = 0
    for f in files:
        ym = Path(f).stem[-6:]
        out = OUT / f"panel_{ym}.parquet"
        if out.exists() and not a.force:
            continue
        h = month(f, units, P)
        if h is None:
            print(f"{ym}: no direct-consumer bids")
            continue
        h.to_parquet(out, index=False)
        tot += len(h)
        print(f"{ym}: {len(h):,} unit-hours, {h.unit.nunique()} units, "
              f"cleared {h.q_cleared.sum() / 1e3:,.0f} GWh", flush=True)
    print(f"done: {tot:,} unit-hours written to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
