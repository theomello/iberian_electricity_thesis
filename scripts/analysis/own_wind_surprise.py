#!/usr/bin/env python3
"""Each firm's own wind surprise: its farms' output minus its own day-ahead wind schedule.

    .venv/bin/python scripts/analysis/own_wind_surprise.py

Framework spec §9.7 step 5, the rescue named in `notes/rq-intraday-surprise.md` §5.
REE's forecast error failed as an intraday instrument because firms know part of it
when they bid: they schedule their wind on their own forecasts. The surprise that
moves a firm's intraday position is the error against ITS OWN schedule:

    S_gt = W_hat_gt − sched_gt                                   (MW)

sched_gt  the firm's day-ahead wind schedule: OMIE's operating schedule (`pdbf`, every
          role summed, so bilateral contracts count: Iberdrola sells 93% of its wind
          bilaterally, March 2022) of the units OMIE labels wind, exposed and
          share-weighted by the owners in force that day (lib/unit_ownership)
W_hat_gt  the firm's realised wind: its located farms' capacity factor,
              cf_gt = Σ_r K_gr · cf_rt / Σ_r K_gr
          (K_gr located wind by region, cf_rt measured output over capacity, as in
          `regional_wind_offer_test.py`), scaled to the scheduled fleet month by month:
              W_hat_gt = k_gm · cf_gt,   k_gm = Σ_t sched_gt / Σ_t cf_gt   (group-month)
          so S has mean zero in each group-month, and the capacity built during the
          window and the farms not located drop out of the level.

What S holds besides news: the part of the firm's farms' output its located farms do
not represent (46% of wind is not located), and any reason other than a forecast for
which the firm scheduled less or more wind than it expected to produce. The second is
a choice made with the day-ahead offers; the day-ahead placebo tests it.

Groups: the firms of `intraday_surprise_test.FIRMS_Z` with located wind. Hourly,
2019-01-01 → 2024-06-13 (MIBEL's intraday sessions). Writes
outputs/tables/own_wind_surprise.parquet: group, utc, date, period, sched_mw, cf, k,
W_hat_mw, S_mw; and prints how the schedule tracks the located farms.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from intraday_surprise_test import FIRMS_Z  # noqa: E402
from regional_wind_offer_test import forecasts, own_capacity, regional_cf  # noqa: E402
from unit_ownership import attach_owners, spells  # noqa: E402

DATA = ROOT / "data"
OUT = ROOT / "outputs/tables/own_wind_surprise.parquet"
START, END = "2019-01-01", "2024-06-13"


def wind_units() -> list[str]:
    ua = pd.read_parquet(DATA / "omie/registry/unit_agents.parquet", columns=["unit", "tech_omie", "tech_omie_early"])
    lab = ua.tech_omie.fillna(ua.tech_omie_early)
    return sorted(ua.loc[lab == "wind", "unit"].astype(str))


def schedules(units: list[str], sp: pd.DataFrame) -> pd.DataFrame:
    months = [str(p).replace("-", "") for p in pd.period_range(START[:7], END[:7], freq="M")]
    parts = []
    for ym in months:
        p = pq.read_table(DATA / f"omie/pdbf/parquet/pdbf_{ym}.parquet",
                          columns=["date", "period", "resolution_min", "unit", "schedule_mw"],
                          filters=[("unit", "in", units)]).to_pandas()
        p["date"] = pd.to_datetime(p.date)
        p = p[(p.date >= START) & (p.date <= END) & (p.resolution_min == 60)]
        p["unit"] = p.unit.astype(str)
        p = p.groupby(["date", "period", "unit"], as_index=False).schedule_mw.sum()
        m = attach_owners(p, sp, value_cols=("schedule_mw",))
        m = m[m.group.isin(FIRMS_Z) & ~m.pt]
        parts.append(m.groupby(["date", "period", "group"], as_index=False).schedule_mw.sum())
    s = pd.concat(parts, ignore_index=True).rename(columns={"schedule_mw": "sched_mw"})
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet",
                         columns=["date", "period", "utc_timestamp", "resolution_min"])
    px["date"] = pd.to_datetime(px.date)
    px = px[px.resolution_min == 60].assign(utc=lambda x: x.utc_timestamp.dt.floor("h"))
    return s.merge(px[["date", "period", "utc"]], on=["date", "period"])


def main() -> int:
    sp = spells()
    s = schedules(wind_units(), sp)
    cf = regional_cf(forecasts())
    k = own_capacity(FIRMS_Z)
    w = k.merge(cf[["utc", "nuts_id", "cf_real"]], on="nuts_id")
    w["kc"] = w.K_gw * w.cf_real
    c = w.groupby(["group", "utc"]).agg(kc=("kc", "sum"), K=("K_gw", "sum")).reset_index()
    c["cf"] = c.kc / c.K
    c["utc"] = pd.to_datetime(c.utc, utc=True)
    s["utc"] = pd.to_datetime(s.utc, utc=True)
    d = s.merge(c[["group", "utc", "cf"]], on=["group", "utc"], how="inner").dropna(subset=["cf"])
    d["ym"] = d.date.dt.strftime("%Y%m")
    tot = d.groupby(["group", "ym"]).agg(sm=("sched_mw", "sum"), cm=("cf", "sum"))
    d = d.merge((tot.sm / tot.cm).rename("k").reset_index(), on=["group", "ym"])
    d["W_hat_mw"] = d.k * d.cf
    d["S_mw"] = d.W_hat_mw - d.sched_mw
    d = d.drop(columns="ym")
    d.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)} ({len(d):,} group-hours)")
    print("\nhow each firm's day-ahead wind schedule tracks its located farms' capacity factor:")
    g = d.groupby("group").apply(lambda x: pd.Series({
        "hours": len(x), "sched_mean_mw": x.sched_mw.mean(), "corr_sched_cf": x.sched_mw.corr(x.cf),
        "S_sd_mw": x.S_mw.std(), "S_sd_over_sched": x.S_mw.std() / x.sched_mw.mean()}), include_groups=False)
    print(g.round(3).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
