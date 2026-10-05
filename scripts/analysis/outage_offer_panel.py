#!/usr/bin/env python3
"""Offer price levels of every dispatchable unit by hour, with its firm's X and reactor-outage dose.

    .venv/bin/python scripts/build/build_reactor_outages.py      # input: the dose
    .venv/bin/python scripts/analysis/firm_x.py                  # input: X of the five firms
    .venv/bin/python scripts/analysis/firm_incentive_rebuild.py  # input: X of every other firm
    .venv/bin/python scripts/analysis/outage_offer_panel.py [--months 202401 ...]

Framework spec §9.2: offer = cost + beta x X for every firm, with period effects
absorbing the merit order, X instrumented by the firm's own reactor outages
(`notes/rq-reactor-outages.md`). Outages last days or weeks, so they move the day's
LEVEL of a firm's X, not its shape within the day: the outcome must be an offer
level, not leg D's shape against the unit-day's own median price.

UNITS: leg D's (`leg_d_panel.leg_d_units`): storage hydro, pumped-storage turbines,
combined cycle and coal, supply roles, sell offers. Each unit-day counts for its
largest owner in force that day (`group`); `firm5` is that group if it is one of
the five, else FRINGE (kept at 50 MW or more).

OUTCOMES per unit-period, then averaged to the local hour:
  o25, o50   offer price (EUR/MWh) at 25% and 50% of the unit's offered volume, steps
             sorted by price; step prices capped at PRICE_CAP so that withdrawal blocks
             at the harmonised maximum do not dominate a mean
  p50cap     offer price at 50% of capacity (NaN when less is offered)
  off_share  offered MW over capacity (`cab` max power that day)
  c_bid      thermal units: implied marginal cost on prices known when offers close
             (`implied_marginal_cost_daily.marginal_cost_capped_bid_eur_mwh`,
             plant-specific efficiency only); NaN otherwise

FIRM TERMS per period: X for the five from `firm_x.parquet`, for every other group
from `firm_incentive_net.parquet` (net_exp_mw / slope_exp_h5, rivals' slope at least
5 MW per EUR/MWh); dose_unpl and dose_plan, the group's share of unplanned and planned
reactor outages in GW (`reactor_outage_dose.parquet`, by UTC hour; 0 for a group with
no reactor). Clean periods only (no market split, clearing identity holds).

Writes outputs/tables/outage_offer_panel.parquet, one row per unit x date x hour.
"""
from __future__ import annotations

import sys
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from leg_d_panel import FIRMS, FRINGE_MIN_MW, KEY, leg_d_units, unit_day_capacity  # noqa: E402
from unit_ownership import majority_group, spells  # noqa: E402

DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
BIDS = DATA / "omie/bids/parquet"
OUT = TABLES / "outage_offer_panel.parquet"
PRICE_CAP = 1000.0       # EUR/MWh
MIN_SLOPE = 5.0


def month_offers(f: Path, units: list[str], cap: pd.DataFrame) -> pd.DataFrame:
    """unit, date, period: off_mw, o25, o50, p50cap from the month's sell offers."""
    b = pq.read_table(f, columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"],
                      filters=[("unit", "in", units), ("side", "==", "V"), ("status", "==", "O")]).to_pandas()
    b = b[b.power_mw > 0].copy()
    if b.empty:
        return pd.DataFrame()
    b["unit"] = b.unit.astype(str)
    b["date"] = pd.to_datetime(b.date)
    b = b.sort_values(["unit", "date", "period", "price_eur_mwh"], kind="stable", ignore_index=True)
    codes, keys = pd.factorize(pd.MultiIndex.from_frame(b[["unit", "date", "period"]]), sort=False)
    size = np.bincount(codes)
    start = np.concatenate([[0], np.cumsum(size)[:-1]])
    cum = b.groupby(codes, sort=False).power_mw.cumsum().to_numpy()
    price = np.minimum(b.price_eur_mwh.to_numpy(), PRICE_CAP)
    out = pd.DataFrame({"unit": keys.get_level_values(0), "date": keys.get_level_values(1),
                        "period": keys.get_level_values(2), "off_mw": cum[start + size - 1]})
    capv = out.merge(cap, on=["unit", "date"], how="left").cap_mw.to_numpy()

    def at(target: np.ndarray) -> np.ndarray:
        below = np.bincount(codes, weights=(cum < target[codes]).astype(float), minlength=len(size)).astype(np.int64)
        reached = below < size
        idx = np.where(reached, start + np.minimum(below, size - 1), 0)
        return np.where(reached, price[idx], np.nan)

    out["o25"] = at(0.25 * out.off_mw.to_numpy())
    out["o50"] = at(0.50 * out.off_mw.to_numpy())
    out["p50cap"] = at(np.where(np.isfinite(capv), 0.5 * capv, np.inf))
    out["cap_mw"] = capv
    return out


def periods(months: list[str]) -> pd.DataFrame:
    """date, period: local hour and the UTC hour of the period's start."""
    s = pd.read_parquet(ROOT / "outputs/tables/solar_instrument.parquet",
                        columns=["date", "period", "resolution_min", "utc_timestamp"])
    s["date"] = pd.to_datetime(s.date)
    s = s[s.date.dt.strftime("%Y%m").isin(months)].copy()
    s["hour"] = (s.period - 1) // (60 // s.resolution_min)
    s["utc"] = pd.to_datetime(s.utc_timestamp, utc=True).dt.floor("h")
    return s[KEY + ["hour", "utc"]]


def firm_terms(months: list[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(X by date, period, group; clean flags by date, period)."""
    x5 = pd.read_parquet(TABLES / "firm_x.parquet", columns=KEY + ["firm", "X", "clean", "zero_price"])
    x5["date"] = pd.to_datetime(x5.date)
    x5 = x5[x5.date.dt.strftime("%Y%m").isin(months)]
    clean = x5[x5.firm == FIRMS[0]][KEY + ["clean", "zero_price"]]
    xa = pd.read_parquet(TABLES / "firm_incentive_net.parquet", columns=KEY + ["firm", "net_exp_mw", "slope_exp_h5"],
                         filters=[("year", ">=", int(min(months)[:4])), ("year", "<=", int(max(months)[:4]))])
    xa["date"] = pd.to_datetime(xa.date)
    xa = xa[xa.date.dt.strftime("%Y%m").isin(months) & ~xa.firm.isin(FIRMS)]
    xa["X"] = (xa.net_exp_mw / xa.slope_exp_h5).where(xa.slope_exp_h5 >= MIN_SLOPE)
    x = pd.concat([x5[KEY + ["firm", "X"]], xa[KEY + ["firm", "X"]]], ignore_index=True)
    return x.rename(columns={"firm": "group"}), clean


def doses() -> pd.DataFrame:
    d = pd.read_parquet(TABLES / "reactor_outage_dose.parquet")
    w = d[d.cls.isin(["unplanned", "planned"])].pivot_table(index=["firm", "utc"], columns="cls", values="lost_mw",
                                                            aggfunc="sum").fillna(0.0) / 1000
    return w.rename(columns={"unplanned": "dose_unpl", "planned": "dose_plan"}).reset_index().rename(
        columns={"firm": "group"})


def costs() -> pd.DataFrame:
    c = pd.read_parquet(DATA / "jrc_ppdb/implied_marginal_cost_daily.parquet",
                        columns=["unit", "date", "marginal_cost_capped_bid_eur_mwh", "eff_is_generic"])
    c = c[~c.eff_is_generic].rename(columns={"marginal_cost_capped_bid_eur_mwh": "c_bid"})
    c["date"] = pd.to_datetime(c.date)
    return c[["unit", "date", "c_bid"]]


def build(months: list[str] | None) -> pd.DataFrame:
    files = sorted(BIDS.glob("bids_*.parquet"))
    if months:
        files = [f for f in files if f.stem.split("_")[1] in months]
    months = [f.stem.split("_")[1] for f in files]
    u = leg_d_units()
    units = sorted(u.unit)
    sp = spells()
    sp = sp[sp.unit.isin(set(units))]
    per = periods(months)
    x, clean = firm_terms(months)
    dz, cst = doses(), costs()
    parts = []
    for f, ym in zip(files, months):
        if ym not in set(per.date.dt.strftime("%Y%m")):
            continue
        cap = unit_day_capacity(units, [ym])
        o = month_offers(f, units, cap)
        if o.empty:
            continue
        o = o.merge(u, on="unit")
        o["cap_mw"] = o.cap_mw.where(o.cap_mw > 0, o.reg_mw)
        o["off_share"] = o.off_mw / o.cap_mw
        ud = o[["unit", "date"]].drop_duplicates()
        ud["group"] = majority_group(ud, sp).to_numpy()
        ud["firm5"] = np.where(ud.group.isin(FIRMS), ud.group, "FRINGE")
        o = o.merge(ud, on=["unit", "date"])
        o = o[(o.firm5 != "FRINGE") | (o.reg_mw >= FRINGE_MIN_MW)]
        o = o.merge(per, on=KEY).merge(clean, on=KEY)
        o = o[o.clean]
        o = o.merge(x, on=KEY + ["group"], how="left").merge(dz, on=["group", "utc"], how="left")
        o[["dose_unpl", "dose_plan"]] = o[["dose_unpl", "dose_plan"]].fillna(0.0)
        h = o.groupby(["unit", "group", "firm5", "cls", "date", "hour"]).agg(
            o25=("o25", "mean"), o50=("o50", "mean"), p50cap=("p50cap", "mean"), off_share=("off_share", "mean"),
            cap_mw=("cap_mw", "first"), X=("X", "mean"), dose_unpl=("dose_unpl", "mean"),
            dose_plan=("dose_plan", "mean"), zero_price=("zero_price", "max"), n_per=("period", "size")).reset_index()
        parts.append(h)
        print(f"  {ym}: {len(h):,} unit-hours", file=sys.stderr, flush=True)
    h = pd.concat(parts, ignore_index=True).merge(cst, on=["unit", "date"], how="left")
    iso = h.date.dt.isocalendar()
    h["wk"] = (iso.year * 100 + iso.week).astype("int64")
    f32 = ["o25", "o50", "p50cap", "off_share", "X", "dose_unpl", "dose_plan", "c_bid"]
    h[f32] = h[f32].astype("float32")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    h.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(h):,} unit-hours, {h.unit.nunique()} units)")
    print(h.groupby(["firm5", "cls"]).agg(n=("o50", "size"), X=("X", "mean"), dose_unpl=("dose_unpl", "mean"),
                                         dose_plan=("dose_plan", "mean")).round(3).to_string())
    return h


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*", help="YYYYMM months only (for checks)")
    build(ap.parse_args().months)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
