#!/usr/bin/env python3
"""The hydro cost: each storage unit's price-taking water value, frozen as one daily file.

    .venv/bin/python scripts/build/build_water_value_forward.py     # input: λ* and its parts
    .venv/bin/python scripts/build/build_hydro_cost.py

The counterpart for storage hydro of `build_implied_marginal_cost.py` for gas and coal: a
cost on information known when day-ahead offers close, for every unit and day, to be read
by every design that needs one (leg B, the at-cost instrument, the counterfactual price).

THE COST, WITH AN EXAMPLE. A reservoir expecting to run its turbines a fifth of next
month's hours does best in the dearest fifth, so a price-taker offers its water at the
price only a fifth of those hours exceed: the 80th percentile of the prices expected from
OMIP forwards (settled on D−2) and last year's hourly shape. The running share is the
unit's own capacity factor for that calendar month in the other years, moved by how full
its reservoirs are against the time of year. `build_water_value_forward.py` has the
construction; this file only selects and flags.

  cost_eur_mwh             λ*30s: 30 days ahead, storage-adjusted. The main cost. EDP's
                           own offers reveal a water value within 6% of it on its four
                           large cascades (`rq-water-value-forward.md` §3).
  cost_90_eur_mwh          λ*90s: 90 days ahead. The check; large reservoirs plan further
                           ahead, and it sits 5–9% higher for Iberdrola and Naturgy.
  cost_nostorage_eur_mwh   λ*30, the running share without the reservoir's fill.

STATUS. A benchmark, not a measurement: what a price-taker with unbiased forwards and its
usual release would offer. A LOWER BOUND in the same sense as the gas and coal cost (which
leaves out start-ups): it leaves out option value beyond the month and the reservoir's
bounds. Option value from uncertain water within the month is under 1% (§5.4), and storage
moves it by €0–4.

FLAGS, where it says little about a unit's offers:
  pumped        pure and mixed pumped storage: the value is an arbitrage value, read apart
  zero_share    share of the unit's offered hydro MW priced at or below €1 that month
                (step caches, 2019-01 → 2025-09; NaN outside). Above 0.5 the unit offers
                its water at zero (Endesa's Guadalquivir), and the cost does not describe
                its offers.
  spell         numbers the unit's spells of `cab` max power: a new spell when the monthly
                maximum moves by more than SPELL_BREAK from the previous month's, as when
                EDP moved ~1,000 MW from ACAVADO to ALIMA in March 2024. Compare a unit's
                cost across spells with care.
  storage       the fill series used: miteco (basin), snirh (own reservoirs), or none.

Known at D − 2 (forwards and fill), so usable for offers on D. 2019-01-01 → 2026-05-31.

WRITES outputs/tables/hydro_cost_daily.parquet (unit, date, group, cls, zone,
cost_eur_mwh, cost_90_eur_mwh, cost_nostorage_eur_mwh, cf_s, storage, fill_anom, fwd,
pumped, zero_share, spell).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
CACHE = ROOT / "outputs/cache/step"
IN = TABLES / "water_value_forward.parquet"
OUT = TABLES / "hydro_cost_daily.parquet"
ZERO = 1.0           # €/MWh
SPELL_BREAK = 0.25   # a 25% move in the monthly maximum of `cab` max power


def zero_share() -> pd.DataFrame:
    """unit, ym, zero_share: offered hydro MW at or below ZERO over all offered hydro MW."""
    parts = []
    for f in sorted(CACHE.glob("hydro_2*.parquet")):
        h = pd.read_parquet(f, columns=["unit", "date", "price", "mw", "withdrawn"])
        h = h[~h.withdrawn & (h.mw > 0)]
        h["ym"] = pd.to_datetime(h.date).dt.to_period("M")
        h["z"] = h.mw.where(h.price <= ZERO, 0.0)
        parts.append(h.groupby(["unit", "ym"])[["z", "mw"]].sum())
    s = pd.concat(parts).groupby(level=[0, 1]).sum()
    return (s.z / s.mw).rename("zero_share").reset_index()


def spells(units: list[str]) -> pd.DataFrame:
    """unit, ym, spell, cap: a new spell when the month's maximum `cab` max power moves by
    more than SPELL_BREAK."""
    cap = []
    for f in sorted((DATA / "omie/cab/parquet").glob("cab_*.parquet")):
        c = pd.read_parquet(f, columns=["date", "unit", "max_power_mw"], filters=[("unit", "in", units)])
        if not c.empty:
            cap.append(c.groupby(["unit", pd.to_datetime(c.date).dt.to_period("M").rename("ym")]).max_power_mw.max())
    k = pd.concat(cap).groupby(level=[0, 1]).max().rename("cap").reset_index().sort_values(["unit", "ym"])
    prev = k.groupby("unit").cap.shift()
    brk = (prev > 0) & ((k.cap / prev - 1).abs() > SPELL_BREAK)
    k["spell"] = brk.groupby(k.unit).cumsum().astype(int)
    return k


def main() -> int:
    w = pd.read_parquet(IN)
    w["date"] = pd.to_datetime(w.date)
    d = w.rename(columns={"lam30s": "cost_eur_mwh", "lam90s": "cost_90_eur_mwh", "lam30": "cost_nostorage_eur_mwh"})
    d["pumped"] = d.cls == "pumped"
    d["ym"] = d.date.dt.to_period("M")
    d = d.merge(zero_share(), on=["unit", "ym"], how="left")
    sp = spells(d.unit.unique().tolist())
    d = d.merge(sp[["unit", "ym", "spell"]], on=["unit", "ym"], how="left")
    d["spell"] = d.groupby("unit").spell.ffill().fillna(0).astype(int)
    cols = ["unit", "date", "group", "cls", "zone", "cost_eur_mwh", "cost_90_eur_mwh", "cost_nostorage_eur_mwh",
            "cf_s", "storage", "fill_anom", "fwd", "pumped", "zero_share", "spell"]
    d = d[cols].sort_values(["unit", "date"], ignore_index=True)
    assert not d.duplicated(["unit", "date"]).any()
    d.to_parquet(OUT, index=False)

    st = d[~d.pumped]
    print(f"wrote {OUT.relative_to(ROOT)}: {len(d):,} unit-days, {d.unit.nunique()} units "
          f"({st.unit.nunique()} storage, {d[d.pumped].unit.nunique()} pumped), {d.date.min():%Y-%m-%d} → "
          f"{d.date.max():%Y-%m-%d}; cost defined on {d.cost_eur_mwh.notna().mean():.3f}")
    print(f"storage source, unit-days: {d.storage.value_counts().to_dict()}")
    zs = st.groupby("unit").zero_share.median()
    print(f"storage units offering most hydro at ≤ €{ZERO:g} (median month): {sorted(zs[zs > 0.5].index)}")
    br = sp[sp.spell > sp.groupby("unit").spell.shift().fillna(0)]
    print("spell breaks (cab max power, monthly maximum):")
    print(br.merge(sp.assign(ym=sp.ym + 1)[["unit", "ym", "cap"]].rename(columns={"cap": "cap_before"}),
                   on=["unit", "ym"], how="left")[["unit", "ym", "cap_before", "cap", "spell"]].to_string(index=False))
    print("\nmedian cost by year, storage units (€/MWh):")
    print(st.groupby(st.date.dt.year)[["fwd", "cost_eur_mwh", "cost_90_eur_mwh", "cost_nostorage_eur_mwh"]]
          .median().round(1).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
