#!/usr/bin/env python3
"""Build the implied marginal cost this repo set out to construct:
fuel_price / efficiency + emission_factor * CO2_price / efficiency, per
matched CCGT or coal unit per day.

    .venv/bin/python scripts/build/build_implied_marginal_cost.py
    .venv/bin/python scripts/build/build_implied_marginal_cost.py --verify

Writes data/jrc_ppdb/implied_marginal_cost_daily.parquet, one row per
matched unit per day: `unit` (OMIE code), `date`, `fuel` (`gas`/`coal`),
`marginal_cost_eur_mwh`, plus the inputs and `eff_is_generic` carried
through so a caller can filter to the trustworthy subset without
re-joining anything.

TWO FUELS, TWO PRICE SERIES, ONE FORMULA SHAPE

    marginal_cost = fuel_price_eur_mwh_th / efficiency
                     + emission_factor_tco2_per_mwh_th * co2_price_eur_tco2 / efficiency

`fuel_price_eur_mwh_th` is EUR per MWh of *thermal* input (fuel), which is
exactly the denominator `efficiency` converts to electrical output:
`fuel_input_mwh_th = output_mwh_e / efficiency`, so `fuel_cost / output =
fuel_price / efficiency`. Same derivation for the CO2 term, converting
emitted tCO2 to EUR via the allowance price. Both emission factors are
**standard constants, not fetched data** -- the EU ETS Monitoring and
Reporting Regulation's defaults (Commission Implementing Regulation (EU)
2018/2066, Annex VI): natural gas 56.1 tCO2/TJ = 0.2020 tCO2/MWh(th); other
bituminous coal 94.6 tCO2/TJ = 0.3406 tCO2/MWh(th). These are the
regulatory defaults a plant without its own lab-measured factor must use --
appropriate here since these are implied, not declared, costs.

**Gas** -- `fuel_price_eur_mwh_th` is MIBGAS's `mibgas_es_eur_mwh`
directly, already EUR/MWh(th).

**Coal** -- two conversions MIBGAS didn't need, both cited rather than
guessed:

  1. `fetch_coal_price.py`'s `close` is **USD/tonne**; divide by
     `fetch_ecb_fx.py`'s `usd_per_eur` to reach EUR/tonne (divide, not
     multiply -- see that fetcher's docstring on why).
  2. EUR/tonne -> EUR/MWh(th) needs a calorific value. The API2 CIF ARA
     index (the benchmark `fetch_coal_price.py` tracks) is specified at
     **6,000 kcal/kg NAR** (S&P Global's own CIF ARA 6,000 NAR Coal Price
     Assessments methodology -- traditional standard-traded-coal spec, sub-1%
     sulphur). Converted: 6,000 kcal/kg x 4.1868 kJ/kcal = 25.1208 GJ/tonne
     = **6.978 MWh(th)/tonne**.

`COAL_CALORIFIC_VALUE_MWH_PER_TONNE` and both emission factors are named
module constants with their source in the comment beside them, not
buried in the formula -- change the citation, not just the number, if a
better one turns up.

**This is a benchmark price, not necessarily these plants' actual fuel
cost.** API2 is the Rotterdam *import* benchmark; some of the matched
plants may have burned domestic Spanish coal at a different price,
particularly before Spain's mines closed. Treat the coal-side marginal
cost as a looser bound than the gas side for this reason, on top of the
"lower bound" caveat below that applies to both fuels.

WHY THIS IS A LOWER BOUND, NOT THE PLANT'S ACTUAL COST

Real CCGT variable cost also includes O&M, water, and startup
amortisation, and `efficiency` here is a static plant-level number, not the
part-load efficiency a unit actually runs at in a given hour -- CCGT
efficiency falls off away from full load, so this understates cost at low
output. It is what CLAUDE.md's `cab` section calls a bound, not a
measurement, in the same spirit as the minimum-income-condition bound: a
floor a rational unit would not offer below, not its true cost.

`eff_is_generic` FLOWS THROUGH ON PURPOSE

8 of the 38 Fossil Gas matches carry only a technology-class-average
efficiency (`Class_derived`, see `build_jrc_cab_match.py`), not a
plant-specific one. Their `marginal_cost_eur_mwh` is still computed --
dropping them here would silently narrow the panel -- but `eff_is_generic`
is kept in the output specifically so a caller can restrict to the
trustworthy 30 (31 OEM_derived minus overlaps... see the printed
breakdown) without re-deriving the flag.

SAMPLE PERIOD

Restricted to the intersection of each fuel's inputs' date coverage. Gas,
CO2, coal and FX all run to within a day of 2026-08-18; the join is on
`date` so any day an input is missing (1 null day in MIBGAS, ~1.5% of
trading days in the EUA/coal series and the ECB series -- weekends and
each source's own non-trading/non-publication days) drops that unit-day
rather than filling it. Gas and coal are NOT matched to a common calendar
before joining -- each fuel keeps whatever trading days its own price
series actually has, so a gas-unit-day and a coal-unit-day for the "same"
date are not guaranteed to rest on the same set of underlying market
closures.

STILL NOT IN THE FORMULA AT ALL

O&M, water and startup-amortisation costs; part-load efficiency (every
number here is a single static full-load figure, so cost is understated
whenever a unit runs below full output); and 9.6 GW of real CCGT capacity
JRC has an efficiency for that `build_jrc_cab_match.py` couldn't safely
match to an OMIE code (Puentes de García Rodríguez 5, Escombreras
Iberdrola 6, Escatrón 3, Castelnou and others -- a matching-layer gap, not
a missing price). None of these are closed by a better fetch.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
from omie_common import DATA  # noqa: E402

OUT = DATA / "jrc_ppdb" / "implied_marginal_cost_daily.parquet"
GAS_EMISSION_FACTOR_TCO2_PER_MWH_TH = 0.2020  # EU ETS MRR Annex VI, natural gas default
COAL_EMISSION_FACTOR_TCO2_PER_MWH_TH = 0.3406  # EU ETS MRR Annex VI, other bituminous coal
COAL_CALORIFIC_VALUE_MWH_PER_TONNE = 6.978  # API2 spec, 6,000 kcal/kg NAR (S&P Global CIF ARA methodology)


def load_inputs() -> dict[str, pd.DataFrame]:
    match = pd.read_parquet(DATA / "jrc_ppdb" / "jrc_cab_match.parquet")
    jrc_type = (pd.read_parquet(DATA / "jrc_ppdb" / "jrc_spain_units.parquet")
                [["eic_p", "type_g"]].drop_duplicates())
    match = match.merge(jrc_type, left_on="jrc_eic_p", right_on="eic_p", how="left")

    gas = pd.read_parquet(DATA / "mibgas" / "mibgas_price_index_daily.parquet")[
        ["date", "mibgas_es_eur_mwh"]]
    gas["date"] = pd.to_datetime(gas.date)

    co2 = pd.read_parquet(DATA / "investing" / "eua_carbon_price_daily.parquet")[["date", "close"]]
    co2 = co2.rename(columns={"close": "co2_eur_tco2"})

    coal = pd.read_parquet(DATA / "investing" / "coal_price_daily.parquet")[["date", "close"]]
    coal = coal.rename(columns={"close": "coal_usd_tonne"})

    fx = pd.read_parquet(DATA / "ecb" / "ecb_usd_eur_daily.parquet")

    return {"match": match, "gas": gas, "co2": co2, "coal": coal, "fx": fx}


def build_fuel_panel(units: pd.DataFrame, prices: pd.DataFrame, fuel_col: str,
                      emission_factor: float, fuel: str) -> pd.DataFrame:
    panel = units[["unit", "cab_descr", "eff", "eff_source", "eff_is_generic"]].merge(
        prices, how="cross")
    panel["fuel"] = fuel
    panel["marginal_cost_eur_mwh"] = (
        panel[fuel_col] / panel.eff
        + emission_factor * panel.co2_eur_tco2 / panel.eff
    )
    return panel


def build() -> pd.DataFrame:
    d = load_inputs()
    match = d["match"]

    gas_units = match[match.type_g == "Fossil Gas"].copy()
    coal_units = match[match.type_g == "Fossil Hard coal"].copy()

    # mibgas_es_eur_mwh has a single null day (documented in
    # fetch_mibgas_prices.py); drop it rather than propagate a NaN cost.
    gas_prices = d["gas"].dropna(subset=["mibgas_es_eur_mwh"]).merge(
        d["co2"], on="date", how="inner")
    gas_panel = build_fuel_panel(gas_units, gas_prices, "mibgas_es_eur_mwh",
                                  GAS_EMISSION_FACTOR_TCO2_PER_MWH_TH, "gas")

    # Coal: USD/tonne -> EUR/tonne (divide by usd_per_eur, see
    # fetch_ecb_fx.py) -> EUR/MWh(th) (divide by the calorific value).
    coal_prices = d["coal"].merge(d["fx"], on="date", how="inner").merge(
        d["co2"], on="date", how="inner")
    coal_prices["coal_eur_mwh_th"] = (
        coal_prices.coal_usd_tonne / coal_prices.usd_per_eur
        / COAL_CALORIFIC_VALUE_MWH_PER_TONNE
    )
    coal_panel = build_fuel_panel(coal_units, coal_prices, "coal_eur_mwh_th",
                                   COAL_EMISSION_FACTOR_TCO2_PER_MWH_TH, "coal")

    panel = pd.concat([gas_panel, coal_panel], ignore_index=True)
    panel = panel.sort_values(["fuel", "unit", "date"]).reset_index(drop=True)
    return panel


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verify", action="store_true",
                     help="re-derive coverage facts from the written parquet")
    ap.add_argument("--refresh", action="store_true",
                     help="rebuild even if the output parquet already exists")
    args = ap.parse_args()

    if OUT.exists() and not args.refresh and not args.verify:
        print(f"  {OUT} already exists; pass --refresh to rebuild")
        panel = pd.read_parquet(OUT)
    else:
        panel = build()
        OUT.parent.mkdir(parents=True, exist_ok=True)
        panel.to_parquet(OUT, index=False)
        print(f"  wrote {OUT}")

    for fuel in ["gas", "coal"]:
        fp = panel[panel.fuel == fuel]
        n_units = fp.unit.nunique()
        n_generic = fp[fp.eff_is_generic].unit.nunique()
        print(f"\n=== {fuel} ===")
        print(f"{len(fp):,} unit-days, {n_units} units "
              f"({n_units - n_generic} plant-specific eff, {n_generic} generic-eff), "
              f"{fp.date.min().date()} -> {fp.date.max().date()}")
        specific = fp[~fp.eff_is_generic]
        generic = fp[fp.eff_is_generic]
        if len(specific):
            print(f"  marginal_cost_eur_mwh, plant-specific eff (the units to trust): "
                  f"mean {specific.marginal_cost_eur_mwh.mean():.2f}, "
                  f"range {specific.marginal_cost_eur_mwh.min():.2f}-"
                  f"{specific.marginal_cost_eur_mwh.max():.2f}")
        if len(generic):
            print(f"  marginal_cost_eur_mwh, generic eff (DO NOT trust the level): "
                  f"mean {generic.marginal_cost_eur_mwh.mean():.2f}, "
                  f"range {generic.marginal_cost_eur_mwh.min():.2f}-"
                  f"{generic.marginal_cost_eur_mwh.max():.2f}")
        print(f"\n  by unit (mean marginal cost, plant-specific eff only):")
        for unit, g in specific.groupby("unit"):
            print(f"    {unit:<10}{g.cab_descr.iloc[0]:<28}eff={g.eff.iloc[0]:.3f}  "
                  f"mean_mc={g.marginal_cost_eur_mwh.mean():>6.2f} EUR/MWh")

    print("\n  (the generic-eff extremes are real arithmetic, not a bug: a small unit's low "
          "class-average efficiency divides a fuel-price spike into an implausible implied cost "
          "-- exactly why eff_is_generic exists; filter it out before using the level, not just "
          "the flag)")

    if args.verify:
        dupe = panel.duplicated(["fuel", "unit", "date"]).sum()
        assert dupe == 0, "duplicate (fuel, unit, date) rows -- not a key"
        assert panel.marginal_cost_eur_mwh.notna().all(), "no null costs should survive the inner join"
        specific = panel[~panel.eff_is_generic]
        assert 5 < specific.marginal_cost_eur_mwh.min(), "cost floor looks implausibly low for fuel + CO2"
        # Only the plant-specific-efficiency subset is checked for a plausible
        # ceiling -- the generic-efficiency subset's extremes are expected,
        # see the printed caveat above.
        assert specific.marginal_cost_eur_mwh.max() < 500, "plant-specific cost ceiling looks implausibly high"
        print("\n  --verify passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
