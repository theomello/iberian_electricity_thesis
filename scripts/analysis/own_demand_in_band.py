#!/usr/bin/env python3
"""How much of a firm's OWN demand bidding sits in the band that sets its slope?

    .venv/bin/python scripts/analysis/own_demand_in_band.py

Step 3b of `notes/rq-midday-hydro.md`.

THE CONCERN

`residual_demand_firm.py` measures the slope of the residual demand firm i
faces as

    slope_i = (all offered MW within +/-h of p*  -  i's own SELL MW in it) / 2h

and maps units to firms over SUPPLY roles only, so a firm's purchase units are
never recognised as its own. But a firm that also buys faces the residual of
everyone ELSE's supply and demand: its own demand bids near p* are a choice, not
a constraint, and belong outside its residual demand just as its sell offers do.
Leaving them in overstates |RD'_i|, which understates the firm's price impact,
`ability`, and the design's X = net / |RD'_i|.

This measures the size of that overstatement. Own units are every unit the
firm owns ON THAT DAY, all roles, each owner's volume times its share
(`lib/unit_ownership.py`, by date and by share since 2026-10-05; EDP COMERCIAL,
EDP's Portuguese retailer, is part of EDP since the GROUP_MERGES of 2026-09-30).
The band is h = 5 EUR/MWh around the Spanish price, as in the firm panel, on the
periods that panel keeps.

    slope_net = slope_i - own_buy_in_band / 2h

Describes the AS-BUILT net position. The exposed position (regulated
pass-through suppliers excluded, framework spec §2.4) is computed in firm_x.py.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from unit_ownership import attach_owners, spells  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
FIRM_PANEL = ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet"
OUT = ROOT / "outputs/tables/own_demand_in_band.parquet"
H = 5.0
FIRMS = ("EDP", "IBERDROLA", "ENDESA", "NATURGY", "REPSOL")


def unit_map() -> pd.DataFrame:
    """Ownership spells of every unit one of the firms owns at some date."""
    sp = spells()
    return sp[sp.unit.isin(set(sp.loc[sp.group.isin(FIRMS), "unit"]))]


def month_band(ym: str, sp: pd.DataFrame, px: pd.DataFrame) -> pd.DataFrame:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"],
                      filters=[("status", "==", "O"), ("unit", "in", sorted(set(sp.unit)))]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    b["unit"] = b.unit.astype(str)
    b = b.merge(px, on=["date", "period"], how="inner")
    b = b[(b.price_eur_mwh - b.p_star).abs() <= H]
    b = attach_owners(b, sp).rename(columns={"group": "firm"})   # power_mw x share
    b = b[b.firm.isin(FIRMS)]
    b["side"] = b.side.astype(str)
    t = b.pivot_table(index=["date", "period", "firm"], columns="side", values="power_mw",
                      aggfunc="sum", observed=True).reindex(columns=["V", "C"]).fillna(0.0)
    return t.rename(columns={"V": "own_sell_band", "C": "own_buy_band"}).reset_index()


def main() -> int:
    sp = unit_map()
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es"]).rename(columns={"price_es": "p_star"})
    px["date"] = pd.to_datetime(px.date)
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    band = pd.concat([month_band(m, sp, px) for m in months], ignore_index=True)

    f = pq.read_table(FIRM_PANEL, columns=["date", "period", "firm", "slope_i_h5"],
                      filters=[("firm", "in", list(FIRMS))]).to_pandas()
    f["date"] = pd.to_datetime(f.date)
    d = f.merge(band, on=["date", "period", "firm"], how="left").fillna(
        {"own_sell_band": 0.0, "own_buy_band": 0.0})
    d["market_band"] = d.slope_i_h5 * 2 * H + d.own_sell_band
    d["buy_share_of_band"] = np.where(d.market_band > 0, d.own_buy_band / d.market_band, np.nan)
    d["slope_net"] = d.slope_i_h5 - d.own_buy_band / (2 * H)
    d["ratio"] = np.where(d.slope_i_h5 > 0, d.slope_net / d.slope_i_h5, np.nan)
    d["year"] = d.date.dt.year
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)

    print("OWN DEMAND BIDS within +/-5 EUR/MWh of p*, firm-periods of the firm panel\n")
    print("share of firm-periods with any own demand in the band")
    print(d.assign(any=d.own_buy_band > 0).groupby(["firm", "year"])["any"].mean()
          .unstack().round(2).to_string())
    print("\nmean own demand in band as a share of the whole band")
    print(d.groupby(["firm", "year"]).buy_share_of_band.mean().unstack().round(3).to_string())
    print("\nmedian slope_net / slope_i  (1 = no overstatement)")
    print(d.groupby(["firm", "year"]).ratio.median().unstack().round(3).to_string())
    print("\n10th percentile of slope_net / slope_i")
    print(d.groupby(["firm", "year"]).ratio.quantile(0.10).unstack().round(3).to_string())
    print(f"\nnegative slope_net (own demand exceeds everyone else's band): "
          f"{(d.slope_net < 0).mean():.4f} of firm-periods")

    edp = d[d.firm == "EDP"].copy()
    hour = pq.read_table(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "utc_timestamp"]).to_pandas()
    hour["date"] = pd.to_datetime(hour.date)
    hour["hour"] = (pd.to_datetime(hour.utc_timestamp, utc=True).dt.tz_convert("Europe/Madrid")
                    .dt.hour + 1)
    edp = edp.merge(hour[["date", "period", "hour"]], on=["date", "period"], how="left")
    edp["era"] = pd.cut(edp.year, [2017, 2020, 2023, 2026], labels=["2018-2020", "2021-2023", "2024-2026"])
    print("\nEDP by era and hour: mean own-demand share of the band")
    print(edp.groupby(["era", "hour"], observed=True).buy_share_of_band.mean().unstack()
          .reindex(columns=[3, 6, 9, 12, 14, 16, 19, 21, 23]).round(3).to_string())
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(d):,} firm-periods)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
