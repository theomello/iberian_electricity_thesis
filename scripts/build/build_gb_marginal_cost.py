#!/usr/bin/env python3
"""Implied marginal cost of British gas plants, per unit per day: the second comparison's cost.

    .venv/bin/python scripts/build/build_gb_marginal_cost.py [--verify]

Writes data/jrc_ppdb/gb_implied_marginal_cost_daily.parquet, one row per British gas unit
(JRC-PPDB-OPEN, with an efficiency) per calendar day from 2021-05-20. Spain's rule, in pounds:

    cost = gas / eff + 0.2020 * (UKA + CPS) / eff

with the gas price the ONS System Average Price (`fetch_ons_gas_sap.py`), UKA the UK ETS
allowance future (`fetch_uka_carbon_price.py`, from its first trading day) and CPS the Carbon
Price Support, GBP 18/tCO2 over the whole window. Same emission factor as Spain and Italy. The
`_eur` columns divide by the ECB's GBP-per-EUR rate (`ecb_gbp_eur_daily.parquet`).

`unit` is JRC's `name_g`, National Grid's BM unit name (`PEMB-11`); `elexon_unit` the id Elexon's
offers carry (`T_PEMB-11`). `eff_is_generic` flags JRC's class averages, as for Spain and Italy.

`_bid` columns keep the D-2 rule of the Iberian and Italian costs, although balancing offers can
be changed until an hour before delivery: conservative, and the same information set in all three
countries.

Exists for the gas-cap design (`docs/specs/2026-10-28-gas-cap-conduct-design.md`, step 2d).
"""
from __future__ import annotations

import argparse
import glob
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA  # noqa: E402
from build_implied_marginal_cost import (  # noqa: E402
    GAS_EMISSION_FACTOR_TCO2_PER_MWH_TH, known_at_bidding, last_traded)

OUT = DATA / "jrc_ppdb" / "gb_implied_marginal_cost_daily.parquet"
CPS_GBP_TCO2 = 18.0


def build() -> pd.DataFrame:
    uk = pd.read_parquet(DATA / "jrc_ppdb" / "jrc_uk_units.parquet")
    units = uk[(uk.type_g == "Fossil Gas") & uk.eff.notna() & uk.name_g.notna()].copy()
    units = units.sort_values("eff", ascending=False).drop_duplicates("name_g").rename(columns={"name_g": "unit"})
    units["eff_is_generic"] = units.best_source.eq("Class_derived")
    reg = pd.read_parquet(sorted(glob.glob(str(DATA / "elexon" / "bmunits_*.parquet")))[-1])
    units = units.merge(reg[["nationalGridBmUnit", "elexonBmUnit", "fuelType", "leadPartyName"]]
                        .rename(columns={"nationalGridBmUnit": "unit", "elexonBmUnit": "elexon_unit",
                                         "fuelType": "elexon_fuel", "leadPartyName": "lead_party"}),
                        on="unit", how="left")
    units = units[["unit", "elexon_unit", "elexon_fuel", "lead_party", "name_p", "capacity_g", "eff",
                   "best_source", "eff_is_generic", "year_commissioned", "year_decommissioned"]]

    sap = pd.read_parquet(DATA / "ons" / "gas_sap_daily.parquet")
    gas = sap.rename(columns={"gas_day": "date", "sap_gbp_mwh": "gas_gbp_mwh"})[["date", "gas_gbp_mwh"]]
    gas["date"] = pd.to_datetime(gas.date)
    co2 = pd.read_parquet(DATA / "investing" / "uka_carbon_price_daily.parquet")[["date", "close"]]
    co2 = co2.rename(columns={"close": "uka_gbp_tco2"}).assign(date=lambda x: pd.to_datetime(x.date))
    fx = pd.read_parquet(DATA / "ecb" / "ecb_gbp_eur_daily.parquet")
    gas = gas[gas.date >= co2.date.min()]
    prices = last_traded(gas, co2, fx)
    for q, c in ((gas, "gas_gbp_mwh"), (co2, "uka_gbp_tco2"), (fx, "gbp_per_eur")):
        prices = known_at_bidding(prices, q, [c])

    p = units.merge(prices, how="cross")
    ef = GAS_EMISSION_FACTOR_TCO2_PER_MWH_TH
    for sfx in ("", "_bid"):
        p[f"marginal_cost{sfx}_gbp_mwh"] = (p[f"gas_gbp_mwh{sfx}"] + ef * (p[f"uka_gbp_tco2{sfx}"] + CPS_GBP_TCO2)) / p.eff
        p[f"marginal_cost{sfx}_eur_mwh"] = p[f"marginal_cost{sfx}_gbp_mwh"] / p[f"gbp_per_eur{sfx}"]
    return p.sort_values(["unit", "date"]).reset_index(drop=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    p = build()
    p.to_parquet(OUT, index=False)
    spec = p[~p.eff_is_generic]
    print(f"wrote {OUT}: {len(p):,} unit-days, {p.unit.nunique()} units ({spec.unit.nunique()} plant-specific, "
          f"{spec.elexon_unit.notna().groupby(spec.unit).first().sum()} with an Elexon id), "
          f"{p.date.min():%Y-%m-%d} -> {p.date.max():%Y-%m-%d}")
    for y, g in spec.groupby(spec.date.dt.year):
        print(f"  {y}: median cost {g.marginal_cost_bid_gbp_mwh.median():6.1f} GBP/MWh, "
              f"{g.marginal_cost_bid_eur_mwh.median():6.1f} EUR/MWh")
    if a.verify:
        assert not p.duplicated(["unit", "date"]).any(), "(unit, date) is not a key"
        assert p.marginal_cost_gbp_mwh.notna().all(), "null delivery-day cost"
        # Above Spain's ceiling: small peaking turbines (17-53 MW, Drax's, Fiddler's Ferry's,
        # Ratcliffe's, Coolkeeragh's) carry efficiencies of 0.25-0.29, up to GBP 868/MWh in August 2022.
        assert spec.marginal_cost_gbp_mwh.between(5, 1000).all(), "plant-specific cost out of range"
        print("  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
