#!/usr/bin/env python3
"""Feasibility probe: do storage-hydro units vary their offers across the day?

    .venv/bin/python scripts/analysis/hydro_within_day_probe.py
    .venv/bin/python scripts/analysis/hydro_within_day_probe.py 202404 202504

Reproduces every number in `notes/rq-midday-hydro.md` §3 and threat 8.

WHY THIS EXISTS

The midday-hydro design differences the water value out: a storage plant's
opportunity cost of water is a daily shadow price, so a unit x day fixed effect
removes it and the competitive benchmark is an offer curve that is FLAT across
the day's hours. That is only a design if the offers actually vary within a day,
so this measures how often they do, where, and whether the variation lines up
with the firm's residual-demand slope at all.

THE SAMPLE

Storage hydro that SELLS, from `unit_agents.parquet`: every `hydro_ugh` unit,
the Portuguese cascades (`hydro`, PT, >= 200 MW, which are named after rivers --
see CLAUDE.md), and La Muela's turbine leg (MUEL). Supply roles only, which
drops the `HCGC01` purchase unit that `tech` labels hydro, and the bombagem
units, which buy. Owner groups come from `owner_groups.parquet`.

THE MEASURE

Offer price at 25% and 50% of the unit's own capacity, via
`capacity_quantile_offer.quantile_prices` (capacity from `cab`, fixed across
periods). A unit-day is FLAT when p50 is identical, to 0.01 EUR/MWh, in every
period it is defined. p50 is censored when a unit offers under half its capacity
-- 35-50% of unit-periods here -- and that censoring is reported, not hidden.

THE SLOPE CHECK IS NOT A TEST

It regresses the within-unit-day p50 deviation on the within-day deviation of
log |RD'_f| from `firm_residual_demand_full_owner.parquet`. No instrument, no
(q - theta) term, no clustering. It exists to say whether the sign is wrong,
nothing more.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from capacity_quantile_offer import SUPPLY_ROLES, quantile_prices  # noqa: E402

DATA = ROOT / "data"
AGENTS = DATA / "omie/registry/unit_agents.parquet"
GROUPS = DATA / "omie/registry/owner_groups.parquet"
PRICES = DATA / "omie/prices/omie_day_ahead_prices.parquet"
FIRM_SLOPE = ROOT / "outputs/tables/firm_residual_demand_full_owner.parquet"
OUT = ROOT / "outputs/tables/hydro_within_day_probe.parquet"

MONTHS = ["201901", "201907", "202104", "202204", "202404", "202407", "202504", "202604"]
PROFILE_HOURS = [4, 9, 13, 16, 21]


def storage_hydro() -> pd.DataFrame:
    u = pd.read_parquet(AGENTS)
    g = pd.read_parquet(GROUPS, columns=["agent_owner", "group"])
    u = u.merge(g, on="agent_owner", how="left")
    keep = (u.tech.eq("hydro_ugh")
            | (u.tech.eq("hydro") & u.country.eq("PT") & (u.max_power_mw >= 200))
            | u.unit.eq("MUEL"))
    u = u[keep & u.role.isin(SUPPLY_ROLES) & (u.max_power_mw >= 50)]
    return u[["unit", "max_power_mw", "group", "tech"]].rename(columns={"max_power_mw": "cap"})


def build(months: list[str], cap: pd.DataFrame) -> pd.DataFrame:
    prices = pd.read_parquet(PRICES, columns=["date", "period", "price_es"])
    prices["date"] = pd.to_datetime(prices["date"])
    rows = []
    for m in months:
        t = pd.read_parquet(DATA / f"omie/bids/parquet/bids_{m}.parquet")
        t = t[t.unit.isin(cap.unit) & (t.side == "V")]
        offered = t[t.status == "O"]
        q = quantile_prices(offered, cap)
        cleared = (t[t.status == "C"].groupby(["date", "period", "unit"]).power_mw.sum()
                   .rename("cleared").reset_index())
        q = q.merge(cleared, on=["date", "period", "unit"], how="left").fillna({"cleared": 0})
        hours = offered.drop_duplicates(["date", "period"])[["date", "period", "hour"]]
        q = q.merge(hours, on=["date", "period"]).merge(cap[["unit", "group"]], on="unit")
        q["date"] = pd.to_datetime(q["date"])
        q = q.merge(prices, on=["date", "period"], how="left")
        q["month"] = m
        rows.append(q)
    d = pd.concat(rows, ignore_index=True)

    g = d.groupby(["unit", "date"])
    d["flat"] = (g.p50.transform("max") - g.p50.transform("min")) < 0.01
    d["p50_dev"] = d.p50 - g.p50.transform("mean")
    d["off_share"] = d.offered / d.cap
    d["off_dev"] = d.off_share - g.off_share.transform("mean")
    d["p50_censored"] = d.p50.isna()
    d["hh"] = d.hour.clip(upper=24)
    d["late"] = d.month >= "2024"
    return d


def report(d: pd.DataFrame, cap: pd.DataFrame) -> None:
    print(f"storage-hydro sellers: {len(cap)} units, {cap.cap.sum():,.0f} MW")
    print(cap.groupby("group", dropna=False).cap.sum().sort_values(ascending=False)
          .round(0).to_string(), "\n")

    # §3.1 -- flat share and dispersion, on unit-days with >= 20 defined periods
    for col in ("p25", "p50"):
        ud = d.dropna(subset=[col]).groupby(["month", "unit", "date"])[col]
        stat = ud.agg(["std", "min", "max", "count"])
        stat = stat[stat["count"] >= 20]
        flat = (stat["max"] - stat["min"]) < 0.01
        between = ud.mean().groupby(["month", "unit"]).std().groupby("month").median()
        print(f"§3.1 {col}: flat unit-days and dispersion")
        print(pd.DataFrame({"flat_share": flat.groupby("month").mean().round(3),
                            "median_within_day_sd": stat["std"].groupby("month").median().round(2),
                            "median_between_day_sd": between.round(2),
                            "unit_days": stat.groupby("month").size()}).to_string(), "\n")

    # §3.2 -- flat share by owner group, 2019-2022 against 2024-2026 months
    ud = d.drop_duplicates(["unit", "date"])
    print("§3.2 flat share by group (late = 2024-2026 months)")
    print(ud.groupby(["group", "late"]).flat.mean().unstack().round(2).to_string(), "\n")

    # §3.3 and §3.4 -- hour profiles
    nonflat = d[~d.flat & d.p50.notna()]
    for m in sorted(d.month.unique()):
        s, n = d[d.month == m], nonflat[nonflat.month == m]
        prof = pd.DataFrame({
            "nonflat_p50_dev": n.groupby("hh").p50_dev.mean(),
            "offered_over_cap": s.groupby("hh").off_share.median(),
            "offered_dev": s.groupby("hh").off_dev.mean(),
            "p50_censored": s.groupby("hh").p50_censored.mean(),
            "p_star": s.groupby("hh").price_es.median(),
        })
        print(f"§3.3/3.4 {m}: hour profile")
        print(prof.reindex(PROFILE_HOURS).round(3).T.to_string(), "\n")


def slope_check(d: pd.DataFrame) -> None:
    """§3.5 -- within-unit-day p50 deviation on within-day log|RD'_f| deviation."""
    f = pd.read_parquet(FIRM_SLOPE, columns=["date", "period", "firm", "slope_i_h5"])
    f["date"] = pd.to_datetime(f["date"])
    m = d.merge(f, left_on=["date", "period", "group"],
                right_on=["date", "period", "firm"], how="inner")
    m = m[m.slope_i_h5 > 0].dropna(subset=["p50"])
    m["lslope"] = np.log(m.slope_i_h5)
    for c in ("p50", "lslope"):
        m[c + "_w"] = m[c] - m.groupby(["unit", "date"])[c].transform("mean")
    print(f"§3.5 slope check ({len(m):,} of {len(d):,} unit-periods join the firm panel)")
    for late, s in m.groupby("late"):
        b = np.polyfit(s.lslope_w, s.p50_w, 1)[0]
        r = s[["lslope_w", "p50_w"]].corr().iloc[0, 1]
        print(f"  {'2024-2026' if late else '2019-2022'}: slope {b:.2f}, corr {r:.3f}, n {len(s):,}")
    print()


def complex_conditions(cap: pd.DataFrame, months=("201907", "202404", "202604")) -> None:
    """Threat 8 -- does any unit declare a minimum-income condition or an SCO?"""
    cols = ["min_income_fixed_eur", "min_income_var_eur_mwh", "sco_fixed_eur"]
    print("threat 8: share of unit-days declaring a complex condition")
    for m in months:
        c = pd.read_parquet(DATA / f"omie/cab/parquet/cab_{m}.parquet")
        c = c[c.unit.isin(cap.unit)]
        shares = {x: round(float((c[x].fillna(0) > 0).mean()), 3) for x in cols if x in c}
        print(f"  {m}: {len(c)} unit-days {shares}")


def main() -> int:
    months = sys.argv[1:] or MONTHS
    cap = storage_hydro()
    d = build(months, cap)
    report(d, cap)
    slope_check(d)
    complex_conditions(cap)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT, index=False)
    print(f"\nwrote {OUT.relative_to(ROOT)}  ({len(d):,} unit-periods)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
