#!/usr/bin/env python3
"""Implied marginal cost of Italian gas plants, per unit per day: the control group's cost.

    .venv/bin/python scripts/build/build_italy_marginal_cost.py [--verify]

Writes data/jrc_ppdb/italy_implied_marginal_cost_daily.parquet, one row per Italian gas
unit (JRC-PPDB-OPEN, with an efficiency) per calendar day. Same rule as Spain's
`build_implied_marginal_cost.py`:

    cost = gas / eff + 0.2020 * EUA / eff

with the gas price at the PSV (GME's MGP-GAS, `fetch_gme_gas_prices.py`) in place of MIBGAS
and the same EUA series and emission factor. There was no subsidy in Italy.

`unit` is JRC's `name_g`, which is GME's own unit code (`UP_TAVAZZANO_5`), so it joins the
GME offers exactly. `eff_is_generic` flags JRC's class averages (`best_source` =
Class_derived), as for Spain: filter on it before using a level.

GAS PRICE PER GAS DAY. A PSV product (`MGP-YYYY-MM-DD`) trades on more than one session.
`psv_eur_mwh` is the last session's volume-weighted mean, or GME's reference price on a
session with no trade. `_bid` columns use only values final when offers close at 12:00 on
D-1 (gas days D-2 or earlier, carbon dated D-2 or earlier), as in Spain: GME's electricity
day-ahead market closes at noon on D-1 too.

Exists for the gas-cap design (`docs/specs/2026-10-28-gas-cap-conduct-design.md`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA  # noqa: E402
from build_implied_marginal_cost import (  # noqa: E402
    GAS_EMISSION_FACTOR_TCO2_PER_MWH_TH, known_at_bidding, last_traded)

OUT = DATA / "jrc_ppdb" / "italy_implied_marginal_cost_daily.parquet"


def psv_daily() -> pd.DataFrame:
    t = pd.read_parquet(DATA / "gme" / "gas" / "gme_mgp_gas_daily.parquet")
    t = t.sort_values(["gas_day", "session"])
    t["px"] = t.price_mean.fillna(t.price_ref)
    last = t.dropna(subset=["px"]).groupby("gas_day").px.last()
    return pd.DataFrame({"date": last.index, "psv_eur_mwh": last.to_numpy()})


def build() -> pd.DataFrame:
    it = pd.read_parquet(DATA / "jrc_ppdb" / "jrc_italy_units.parquet")
    units = it[(it.type_g == "Fossil Gas") & it.eff.notna() & it.name_g.notna()].copy()
    units = units.sort_values("eff", ascending=False).drop_duplicates("name_g")
    units = units.rename(columns={"name_g": "unit"})
    units["eff_is_generic"] = units.best_source.eq("Class_derived")
    units = units[["unit", "name_p", "capacity_g", "eff", "best_source", "eff_is_generic",
                   "year_commissioned", "year_decommissioned", "status_g"]]

    gas = psv_daily()
    co2 = pd.read_parquet(DATA / "investing" / "eua_carbon_price_daily.parquet")[["date", "close"]]
    co2 = co2.rename(columns={"close": "co2_eur_tco2"})
    prices = last_traded(gas, co2)
    prices = known_at_bidding(prices, gas, ["psv_eur_mwh"])
    prices = known_at_bidding(prices, co2, ["co2_eur_tco2"])

    panel = units.merge(prices, how="cross")
    ef = GAS_EMISSION_FACTOR_TCO2_PER_MWH_TH
    panel["marginal_cost_eur_mwh"] = (panel.psv_eur_mwh + ef * panel.co2_eur_tco2) / panel.eff
    panel["marginal_cost_bid_eur_mwh"] = (panel.psv_eur_mwh_bid + ef * panel.co2_eur_tco2_bid) / panel.eff
    return panel.sort_values(["unit", "date"]).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    panel = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    panel.to_parquet(OUT, index=False)
    spec = panel[~panel.eff_is_generic]
    print(f"wrote {OUT}: {len(panel):,} unit-days, {panel.unit.nunique()} units "
          f"({spec.unit.nunique()} plant-specific), {panel.date.min():%Y-%m-%d} -> {panel.date.max():%Y-%m-%d}")
    for y, g in spec.groupby(spec.date.dt.year):
        print(f"  {y}: median cost {g.marginal_cost_bid_eur_mwh.median():7.1f} EUR/MWh")
    if a.verify:
        assert not panel.duplicated(["unit", "date"]).any(), "(unit, date) is not a key"
        assert panel.marginal_cost_eur_mwh.notna().all(), "null delivery-day cost"
        # Higher ceiling than Spain's 500: PSV reached 312 EUR/MWh on 2022-08-26, and two
        # Termini Imerese units carry a plant-specific efficiency of 0.33 -- 1,008 EUR/MWh.
        assert spec.marginal_cost_eur_mwh.between(5, 1200).all(), "plant-specific cost out of range"
        print("  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
