#!/usr/bin/env python3
"""Re-clearable day-ahead curves by hour, each thermal owner's own curve, and gas and coal offer steps.

    .venv/bin/python scripts/analysis/step_curves.py [--months 201906 ...]

Input to `step_estimator.py` and `step_estimator_hydro.py` (framework spec §9.7 step 6;
step-offer design `docs/specs/2026-10-01-step-offer-design.md` §3). Hourly day-ahead
market, 2019-01 (REE's D-1 forecasts start) → 2025-09 (the last hourly month).

THE EFFECTIVE CURVE. Clearing OMIE's offered curves (status O) does not reproduce the
published price: in June 2019 it comes out 13 €/MWh too low. Two reasons, both
checked on the files:
  - units withdrawn by their minimum-income condition stay in the offered curve (on
    average 9 GW of sell offers below the price are not accepted, 93% of it from units
    accepted in no hour of the day, all of which declare the condition);
  - the flow with France under market coupling (unit MIEU) appears only as accepted
    rows, at -500 / -300 €/MWh (imports) or high bid prices (exports).
So the curve used here takes, for each side, the ACCEPTED rows (status C) on the
accepted side of the price and the OFFERED rows (status O) at and beyond it:
    sell: C rows priced below p*, O rows priced at or above p*
    buy:  C rows priced above p*, O rows priced at or below p*
Re-cleared over 2019–2023, it reproduces p* exactly in 61–97% of hours a month and
within 0.5 €/MWh in 80–99.6% (the run's log). An hour
is `valid` when it is unsplit, the clearing identity holds and the re-clear is within
VALID_ERR of p*. Units withdrawn on a day keep their offers above the price; a draw at
a higher price treats them as available.

OWNERSHIP. Rows are split across the owners in force that day by share
(`lib/unit_ownership.attach_owners`); a group's OWN curve is its exposed rows
(regulated pass-through suppliers count as rivals, framework spec §2.4). Groups: every
group that is the largest owner of a gas or coal unit with a plant-specific efficiency
on some day, or of a storage or pumped-storage hydro unit of leg D (added 2026-10-06).

WRITES outputs/cache/step/ (gitignored), one set per month:
  hours_YYYYMM   hid, date, period, utc, p_star, p_clear, valid, d_tot (MW of buy
                 offers), F_wind, F_solar, F_demand (REE's D-1 forecasts, MW)
  market_YYYYMM  hid, price, a: all MW offered at or below the price, both sides
                 (cumulative over the hour's unique prices)
  own_YYYYMM     hid, group, price, v_sell, v_buy: each group's own MW at each price
  units_YYYYMM   hid, unit, group, fuel, price, mw, mw_below, cap_mw, cost, cleared_mw,
                 withdrawn: every sell step of the gas and coal units
  hydro_YYYYMM   hid, date, unit, group, cls, price, mw, mw_below, cap_mw, cleared_mw,
                 withdrawn: every sell step of storage hydro and pumped-storage turbines
hid = days since 2018-01-01 × 24 + period − 1. Days without 24 periods (DST) are left out.
"""
from __future__ import annotations

import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from leg_d_panel import leg_d_units  # noqa: E402
from regional_wind_offer_test import forecasts  # noqa: E402
from residual_demand import IDENTITY_TOL, cleared_by_period  # noqa: E402
from unit_ownership import attach_owners, majority_group, spells  # noqa: E402

DATA = ROOT / "data"
BIDS = DATA / "omie/bids/parquet"
CACHE = ROOT / "outputs/cache/step"
FIRST, LAST = "201901", "202509"     # the day-ahead market is hourly until 2025-09-30
EPOCH = pd.Timestamp("2018-01-01")
EPS = 0.005            # €/MWh: OMIE prices have two decimals
VALID_ERR = 0.5        # €/MWh
KEY = ["date", "period"]


def hid(date: pd.Series, period: pd.Series) -> np.ndarray:
    return ((pd.to_datetime(date) - EPOCH).dt.days.to_numpy() * 24 + period.to_numpy() - 1).astype(np.int64)


def thermal_costs() -> pd.DataFrame:
    """unit, date, fuel, cost: gas and coal units with a plant-specific efficiency, cost on
    prices known when offers close, the gas cap applied (`_capped_bid`)."""
    c = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "fuel", "eff_is_generic", "marginal_cost_capped_bid_eur_mwh"])
    c = c[~c.eff_is_generic & c.marginal_cost_capped_bid_eur_mwh.notna()]
    c["date"] = pd.to_datetime(c.date)
    c["unit"] = c.unit.astype(str)
    return c.rename(columns={"marginal_cost_capped_bid_eur_mwh": "cost"})[["unit", "date", "fuel", "cost"]]


def hydro_units() -> pd.DataFrame:
    """unit, cls: storage hydro and pumped-storage turbines of leg D (`leg_d_units`: every
    such unit one of the five owns, and any other of 50 MW or more)."""
    u = leg_d_units()
    return u[u.cls.isin(["hydro", "pumped"])][["unit", "cls"]].reset_index(drop=True)


def owner_groups(sp: pd.DataFrame, tc: pd.DataFrame, hu: pd.DataFrame) -> list[str]:
    ud = pd.concat([tc[["unit", "date"]].drop_duplicates(),
                    pd.DataFrame({"unit": hu.unit.repeat(4).to_numpy(),
                                  "date": np.tile(pd.to_datetime(["2019-06-01", "2021-06-01", "2023-06-01",
                                                                  "2025-06-01"]), len(hu))})])
    g = majority_group(ud, sp)
    return sorted(g.dropna().unique())


def sell_steps(b: pd.DataFrame, units: set, ym: str, sp: pd.DataFrame) -> pd.DataFrame:
    """Every offered sell step of `units`: hid, date, unit, group (largest owner that day),
    price, mw, mw_below, cap_mw (`cab`), cleared_mw (the hour), withdrawn (offered below
    the price in some hour of the day, accepted in none)."""
    t = b[(b.status == "O") & (b.side == "V") & b.unit.isin(units) & (b.power_mw > 0)]
    t = t.groupby(["hid", "date", "unit", "price_eur_mwh"]).power_mw.sum().reset_index()
    t = t.sort_values(["hid", "unit", "price_eur_mwh"], kind="stable")
    t["mw_below"] = t.groupby(["hid", "unit"]).power_mw.cumsum() - t.power_mw
    ud = t[["unit", "date"]].drop_duplicates()
    ud["group"] = majority_group(ud, sp).to_numpy()
    t = t.merge(ud, on=["unit", "date"], how="left")
    cab = pq.read_table(DATA / f"omie/cab/parquet/cab_{ym}.parquet", columns=["date", "unit", "max_power_mw"]).to_pandas()
    cab["date"] = pd.to_datetime(cab.date)
    cab["unit"] = cab.unit.astype(str)
    cab = cab.groupby(["unit", "date"]).max_power_mw.max().rename("cap_mw").reset_index()
    t = t.merge(cab, on=["unit", "date"], how="left")
    cl = b[(b.status == "C") & (b.side == "V") & b.unit.isin(units)]
    t = t.merge(cl.groupby(["hid", "unit"]).power_mw.sum().rename("cleared_mw").reset_index(),
                on=["hid", "unit"], how="left")
    t["cleared_mw"] = t.cleared_mw.fillna(0.0)
    itm = b[(b.status == "O") & (b.side == "V") & (b.price_eur_mwh < b.p_star - EPS) & b.unit.isin(units)]
    itm_d = set(zip(itm.unit, itm.date))
    clr_d = set(zip(cl.unit, cl.date))
    t["withdrawn"] = [(u, d) in itm_d and (u, d) not in clr_d for u, d in zip(t.unit, t.date)]
    return t.rename(columns={"price_eur_mwh": "price", "power_mw": "mw"})


def effective(b: pd.DataFrame) -> pd.DataFrame:
    """Rows of the effective curve (module docstring); b carries p_star."""
    p, q = b.p_star, b.price_eur_mwh
    sell, buy = b.side == "V", b.side == "C"
    o = b.status == "O"
    keep_o = o & ((sell & (q >= p - EPS)) | (buy & (q <= p + EPS)))
    keep_c = ~o & ((sell & (q < p - EPS)) | (buy & (q > p + EPS)))
    return b[keep_o | keep_c]


def reclear(e: pd.DataFrame) -> pd.DataFrame:
    """hid, p_clear, d_tot and the market table (hid, price, a) from effective rows."""
    v = e.groupby(["hid", "price_eur_mwh"]).power_mw.sum().reset_index().sort_values(["hid", "price_eur_mwh"])
    v["a"] = v.groupby("hid").power_mw.cumsum()
    d_tot = e[e.side == "C"].groupby("hid").power_mw.sum().rename("d_tot")
    v = v.merge(d_tot, on="hid", how="left")
    v["d_tot"] = v.d_tot.fillna(0.0)
    hit = v[v.a - v.d_tot >= 0].groupby("hid").price_eur_mwh.first().rename("p_clear")
    market = v.rename(columns={"price_eur_mwh": "price"})[["hid", "price", "a"]]
    return pd.concat([hit, d_tot], axis=1).reset_index(), market


def month(ym: str, sp: pd.DataFrame, groups: list[str], tc: pd.DataFrame, hu: pd.DataFrame, px: pd.DataFrame,
          fc: pd.DataFrame) -> dict[str, pd.DataFrame]:
    b = pq.read_table(BIDS / f"bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"]).to_pandas()
    b["date"] = pd.to_datetime(b.date)
    for c in ("unit", "side", "status"):
        b[c] = b[c].astype(str)
    days = b.groupby("date").period.max()
    b = b[b.date.isin(days[days == 24].index)]
    idg = cleared_by_period(b)[KEY + ["identity_gap"]]
    b = b.merge(px, on=KEY, how="inner")
    b["hid"] = hid(b.date, b.period)

    e = effective(b)
    rc, market = reclear(e)
    hours = (b[KEY + ["hid", "p_star", "split", "utc"]].drop_duplicates("hid")
             .merge(idg, on=KEY, how="left").merge(rc, on="hid", how="left").merge(fc, on="utc", how="left"))
    hours["valid"] = ((~hours.split) & (hours.identity_gap <= IDENTITY_TOL)
                      & ((hours.p_clear - hours.p_star).abs() <= VALID_ERR)
                      & hours[["F_wind", "F_solar", "F_demand"]].notna().all(axis=1))

    # each group's own curve: exposed rows of its units, share-weighted
    own_units = set(sp.loc[sp.group.isin(groups), "unit"])
    m = attach_owners(e[e.unit.isin(own_units)], sp)
    m = m[m.group.isin(groups) & ~m.pt]
    m["v_sell"] = m.power_mw.where(m.side == "V", 0.0)
    m["v_buy"] = m.power_mw.where(m.side == "C", 0.0)
    own = (m.groupby(["hid", "group", "price_eur_mwh"])[["v_sell", "v_buy"]].sum().reset_index()
           .rename(columns={"price_eur_mwh": "price"}))

    # gas and coal sell steps (the full offered ladder) with the unit's cost and owner
    t = sell_steps(b, set(tc.unit), ym, sp).merge(tc, on=["unit", "date"], how="inner")
    units = t[["hid", "unit", "group", "fuel", "price", "mw", "mw_below", "cap_mw", "cost", "cleared_mw", "withdrawn"]]
    # storage hydro and pumped-storage turbines
    h = sell_steps(b, set(hu.unit), ym, sp).merge(hu, on="unit")
    hydro = h[["hid", "date", "unit", "group", "cls", "price", "mw", "mw_below", "cap_mw", "cleared_mw", "withdrawn"]]

    f32 = {"price": "float64", "a": "float64"}
    return {"hours": hours[["hid", "date", "period", "utc", "p_star", "p_clear", "valid", "d_tot",
                            "F_wind", "F_solar", "F_demand"]],
            "market": market.astype(f32),
            "own": own.astype({"v_sell": "float32", "v_buy": "float32"}),
            "units": units, "hydro": hydro}


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*")
    args = ap.parse_args()
    months = sorted(f.stem.split("_")[1] for f in BIDS.glob("bids_*.parquet"))
    months = [m for m in months if FIRST <= m <= LAST]
    if args.months:
        months = [m for m in months if m in args.months]
    CACHE.mkdir(parents=True, exist_ok=True)
    sp = spells()
    tc = thermal_costs()
    hu = hydro_units()
    groups = owner_groups(sp, tc, hu)
    print(f"{len(groups)} groups own a gas or coal unit with a plant-specific efficiency, or a storage or "
          f"pumped-storage hydro unit: {groups}")
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "price_es", "price_pt", "utc_timestamp", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    px = px[px.resolution_min == 60]
    px = px.assign(split=px.price_es != px.price_pt, utc=px.utc_timestamp.dt.floor("h")).rename(
        columns={"price_es": "p_star"})[KEY + ["p_star", "split", "utc"]]
    fc = forecasts()
    for c in ("F_wind", "F_solar", "F_demand"):
        fc[c] = fc[c] * 1000.0        # GW -> MW
    for ym in months:
        t0 = time.time()
        out = month(ym, sp, groups, tc, hu, px, fc)
        for k, v in out.items():
            v.to_parquet(CACHE / f"{k}_{ym}.parquet", index=False)
        h = out["hours"]
        err = (h.p_clear - h.p_star).abs()
        print(f"  {ym}: {len(h)} hours, valid {h.valid.mean():.3f}, re-clear exact {(err < 0.011).mean():.3f}, "
              f"within {VALID_ERR} {(err <= VALID_ERR).mean():.3f}; {len(out['market']):,} prices, "
              f"{len(out['units']):,} thermal and {len(out['hydro']):,} hydro unit steps ({time.time() - t0:.0f} s)",
              flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
