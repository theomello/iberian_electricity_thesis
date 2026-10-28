#!/usr/bin/env python3
"""Gas plants' offers in Iberia and Italy, unit by hour, 2021-06-15 -> 2023-06-30: the outcome
panel of the gas-cap design (docs/specs/2026-10-28-gas-cap-conduct-design.md, step 0).

    .venv/bin/python scripts/analysis/gas_cap_offer_panel.py

Writes outputs/tables/gas_cap_offer_panel.parquet, one row per unit and hour:

* `p25`, `p50`, `p75`, `p100`: the price at which the unit has offered 25/50/75/100% of its
  capacity K, steps sorted by price and accumulated (as `capacity_quantile_offer.py`).
  NaN when it offers less than that share in the hour: a withholding unit is censored, so
  coverage is reported, never dropped silently.
* `p_band`: the MW-weighted price of its steps within +-BAND of the hour's clearing price
  (its zone's in Italy, its country's in Iberia), and `mw_band`. Kept as a comparison only:
  a band around the clearing price conditions on an outcome the cap itself moved (ab99b50).
* `offered_mw`, `offered_share` = offered_mw / K.
* `p_mid` (2026-10-28): the price at the midpoint between the unit's minimum stable load and K,
  i.e. at K * (1 + ml) / 2, with ml JRC's `min_load` (a share of capacity; the plant's mean over
  its generators in Iberia, the unit's own in Italy, 0.33 where JRC has none). Iberian plants
  offer their minimum-load block low and protect it with the minimum-income condition, so
  shares of K below ml read that block, not the price of running more; Italian plants price
  their first MW near cost. `ml` is carried.
* `run10`, `run20`, `run50` (2026-10-28): MW offered at or below cost + 10/20/50 EUR/MWh,
  divided by K -- the willingness to run, comparable across the two countries because
  withholding by a high price (Iberia's habit) and by not offering (Italy's) count the same.
* `cost` (EUR/MWh, prices final at 12:00 on D-1): Iberia `marginal_cost_subsidised_bid_eur_mwh`,
  i.e. own cost minus the decree's subsidy; Italy `marginal_cost_bid_eur_mwh` (no subsidy).
  `subsidy` (Iberia, bid-time; 0 in Italy) and `cost_gross` (before the subsidy).
* `country` (ES, PT, IT), `zone` (Italy), `firm` (Iberia: majority owner that day,
  `lib/unit_ownership.py`; Italy: the operator that submitted the unit's offers, bilateral
  rows excluded), `price` (the clearing price used for the band).

K is the same rule in both countries: the 99th percentile of the unit's hourly offered MW
over the year before the cap (2021-06-15 -> 2022-06-14). It is predetermined, and it does not
depend on registers that differ between countries (`cab` max power exists for Iberia only).

Offers kept: Iberia OMIE `curva_pbc_uof` status `O`, sell side (physical bilateral contracts
are not in it); Italy GME status ACC/REJ/PREJ, side OFF, operator not "Bilateralista"
(bilateral positions, the counterpart of what OMIE leaves out). Units: gas units with a
plant-specific efficiency (`eff_is_generic` False), 100 MW or more in Italy.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.compute as pc
import pyarrow.dataset as ds

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
OUT = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from unit_ownership import majority_group  # noqa: E402

START, END = pd.Timestamp("2021-06-15"), pd.Timestamp("2023-06-30")
PRE_END = pd.Timestamp("2022-06-14")
BAND = 10.0          # EUR/MWh around the clearing price, for p_band
QS = (0.25, 0.50, 0.75, 1.00)


def iberia_steps(fuel: str = "gas") -> tuple[pd.DataFrame, pd.DataFrame]:
    c = pd.read_parquet(DATA / "jrc_ppdb" / "implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "fuel", "eff_is_generic", "subsidy_bid_eur_mwh",
                                 "marginal_cost_bid_eur_mwh", "marginal_cost_subsidised_bid_eur_mwh"])
    c = c[(c.fuel == fuel) & ~c.eff_is_generic & c.date.between(START, END)]
    units = sorted(c.unit.unique())
    parts = []
    for ym in pd.period_range(START, END, freq="M"):
        t = ds.dataset(DATA / "omie" / "bids" / "parquet" / f"bids_{ym.strftime('%Y%m')}.parquet").to_table(
            filter=(pc.field("status") == "O") & (pc.field("side") == "V") & pc.field("unit").isin(units),
            columns=["date", "period", "unit", "power_mw", "price_eur_mwh"]).to_pandas()
        t["unit"] = t.unit.astype(str)
        parts.append(t)
    s = pd.concat(parts, ignore_index=True)
    s["date"] = pd.to_datetime(s.date)
    s = s[s.date.between(START, END) & (s.power_mw > 0)]
    reg = pd.read_parquet(DATA / "omie" / "registry" / "unit_registry.parquet").set_index("unit").country
    s["country"] = s.unit.map(reg).astype(str)
    pr = pd.read_parquet(DATA / "omie" / "prices" / "omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt"])
    pr["date"] = pd.to_datetime(pr.date)
    s = s.merge(pr, on=["date", "period"], how="left")
    s["price"] = np.where(s.country == "PT", s.price_pt, s.price_es)
    s = s.drop(columns=["price_es", "price_pt"]).rename(columns={"power_mw": "mw", "price_eur_mwh": "p"})
    s["zone"] = s.country
    cost = c.rename(columns={"marginal_cost_subsidised_bid_eur_mwh": "cost",
                             "marginal_cost_bid_eur_mwh": "cost_gross",
                             "subsidy_bid_eur_mwh": "subsidy"})[["unit", "date", "cost", "cost_gross", "subsidy"]]
    return s, cost


def italy_steps() -> tuple[pd.DataFrame, pd.DataFrame]:
    c = pd.read_parquet(DATA / "jrc_ppdb" / "italy_implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "eff_is_generic", "capacity_g", "marginal_cost_bid_eur_mwh"])
    c = c[~c.eff_is_generic & (c.capacity_g >= 100) & c.date.between(START, END)]
    units = sorted(c.unit.unique())
    d = ds.dataset(DATA / "gme" / "offers" / "parquet")
    t = d.to_table(filter=(pc.field("side") == "OFF") & pc.field("status").isin(["ACC", "REJ", "PREJ"])
                   & pc.field("unit").isin(units) & (pc.field("operator") != "Bilateralista"),
                   columns=["date", "period", "unit", "operator", "zone", "quantity_mwh",
                            "price_eur_mwh"]).to_pandas()
    for col in ("unit", "operator", "zone"):
        t[col] = t[col].astype(str)
    t = t[t.quantity_mwh > 0].rename(columns={"quantity_mwh": "mw", "price_eur_mwh": "p"})
    # Zonal clearing price: every accepted sell offer in a zone-hour is paid the zone's price.
    z = d.to_table(filter=(pc.field("side") == "OFF") & (pc.field("status") == "ACC"),
                   columns=["date", "period", "zone", "awarded_price_eur_mwh"]).to_pandas()
    z["zone"] = z.zone.astype(str)
    z = z.groupby(["date", "period", "zone"], observed=True).awarded_price_eur_mwh.median().rename("price").reset_index()
    t = t.merge(z, on=["date", "period", "zone"], how="left")
    t["country"] = "IT"
    cost = c.rename(columns={"marginal_cost_bid_eur_mwh": "cost_gross"})[["unit", "date", "cost_gross"]]
    cost["cost"], cost["subsidy"] = cost.cost_gross, 0.0
    return t, cost


ML_DEFAULT = 0.33


def min_loads() -> pd.Series:
    m = pd.read_parquet(DATA / "jrc_ppdb" / "jrc_cab_match.parquet", columns=["unit", "jrc_eic_p"])
    es = pd.concat([pd.read_parquet(DATA / "jrc_ppdb" / f"jrc_{c}_units.parquet", columns=["eic_p", "min_load"])
                    for c in ("spain", "portugal")])
    ib = m.merge(es.groupby("eic_p").min_load.mean().rename("ml"), left_on="jrc_eic_p", right_index=True,
                 how="left").drop_duplicates("unit").set_index("unit").ml
    it = pd.read_parquet(DATA / "jrc_ppdb" / "jrc_italy_units.parquet", columns=["name_g", "min_load"])
    it = it.dropna(subset=["name_g"]).groupby("name_g").min_load.mean()
    return pd.concat([ib, it])


def unit_hour(s: pd.DataFrame, cost: pd.DataFrame) -> pd.DataFrame:
    keys = ["unit", "date", "period"]
    s = s.merge(cost[["unit", "date", "cost"]], on=["unit", "date"], how="left")
    s = s.sort_values(keys + ["p"], kind="stable")
    g = s.groupby(keys, sort=False)
    s["cum"] = g.mw.cumsum()
    h = g.agg(offered_mw=("mw", "sum"), price=("price", "first"), country=("country", "first"),
              zone=("zone", "first")).reset_index()
    pre = h[h.date <= PRE_END]
    K = pre.groupby("unit").offered_mw.quantile(0.99).rename("K")
    h = h.merge(K, on="unit", how="inner")
    s = s.merge(K, on="unit", how="inner")
    for q in QS:
        hit = s[s.cum >= q * s.K - 1e-6].groupby(keys, sort=False).p.first().rename(f"p{int(q * 100)}")
        h = h.merge(hit, on=keys, how="left")
    ml = min_loads()
    s["ml"] = s.unit.map(ml).fillna(ML_DEFAULT).clip(0.0, 0.9)
    hit = s[s.cum >= (1 + s.ml) / 2 * s.K - 1e-6].groupby(keys, sort=False).p.first().rename("p_mid")
    h = h.merge(hit, on=keys, how="left")
    h["ml"] = h.unit.map(ml).fillna(ML_DEFAULT).clip(0.0, 0.9)
    band = s[(s.p - s.price).abs() <= BAND].assign(pm=lambda x: x.p * x.mw)
    b = band.groupby(keys).agg(pm=("pm", "sum"), mw_band=("mw", "sum"))
    b["p_band"] = b.pm / b.mw_band
    h = h.merge(b[["p_band", "mw_band"]], on=keys, how="left")
    h["mw_band"] = h.mw_band.fillna(0.0)
    for x in (10, 20, 50):
        r = s[s.p <= s.cost + x].groupby(keys).mw.sum().rename(f"run{x}")
        h = h.merge(r, on=keys, how="left")
        h[f"run{x}"] = h[f"run{x}"].fillna(0.0).where(h.merge(cost[["unit", "date", "cost"]],
                                                               on=["unit", "date"], how="left").cost.notna().to_numpy()) / h.K
    h["offered_share"] = h.offered_mw / h.K
    return h


def main() -> int:
    ib, ib_cost = iberia_steps()
    it, it_cost = italy_steps()
    op = (it.groupby("unit").operator.agg(lambda x: x.mode().iloc[0]))
    h = pd.concat([unit_hour(ib, ib_cost).merge(ib_cost, on=["unit", "date"], how="left"),
                   unit_hour(it.drop(columns="operator"), it_cost).merge(it_cost, on=["unit", "date"], how="left")],
                  ignore_index=True)
    h["firm"] = None
    ibm = h.country.isin(["ES", "PT"])
    h.loc[ibm, "firm"] = majority_group(h.loc[ibm, ["unit", "date"]], exposed=False).to_numpy()
    h.loc[~ibm, "firm"] = h.loc[~ibm, "unit"].map(op)
    h["iberia"] = ibm
    h["cap"] = ibm & (h.subsidy > 0)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT, index=False)
    print(f"wrote {OUT}: {len(h):,} unit-hours")
    h["half"] = np.where(h.date <= PRE_END, "pre", np.where(h.date <= "2023-02-25", "binding", "after"))
    cov = h.groupby(["iberia", "half"]).agg(
        units=("unit", "nunique"), unit_hours=("unit", "size"),
        **{f"{c}_cov": (c, lambda x: x.notna().mean()) for c in ["p25", "p50", "p75", "p100", "p_band"]},
        share=("offered_share", "median"), cost_cov=("cost", lambda x: x.notna().mean()))
    print("\ncoverage (share of unit-hours where each measure is defined)\n", cov.round(3).to_string())
    h["ym"] = h.date.dt.to_period("M")
    mk = h.assign(m50=h.p50 - h.cost, m100=h.p100 - h.cost, mband=h.p_band - h.cost)
    tab = mk.groupby(["ym", "iberia"])[["m50", "m100", "mband", "subsidy"]].median().unstack("iberia").round(1)
    print("\nmonthly median markup (offer - cost after subsidy), Italy False / Iberia True\n", tab.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
