"""Where in the sequence of schedules does the within-day price response arise? (note rq-cogeneration.md)

Stages, hourly, per REE programming unit: PDBF (day-ahead base) -> PVP (after day-ahead technical constraints) -> PHFC (after the
intraday auctions and continuous market) -> P48 (after real-time constraints, balancing energy, tertiary, transfers). The response of
each step (the change in the group's output MW) to the hourly day-ahead price moved by the hourly wind forecast, date effects, hour x
month and hour x weekday effects, clustered by week (cogeneration_hourly.fit); per MW of capacity per EUR 10. Groups: gas,
other fossil, biomass and waste, and biomass and waste without five plants (RSAICA, RCUBILL, EEHU2, REEM20, RZABAL; chosen from the
earlier probe, so exploratory). Writes outputs/tables/cogeneration_hourly_stages.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cogeneration_hourly import fit, hourly_drivers  # noqa: E402
from cogeneration_price_response import OUT  # noqa: E402

FIVE = {"RSAICA", "RCUBILL", "EEHU2", "REEM20", "RZABAL"}


def read(sub):
    d = pd.concat(pd.read_parquet(f) for f in sorted((OUT / "cogeneration_ree" / sub).glob("h_*.parquet")))
    d["date"] = pd.to_datetime(d.date)
    return d.set_index(["date", "hour", "unit"])


def main():
    u = pd.read_parquet(OUT / "cogeneration_ree" / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    a = read("hourly_pdbf").join(read("hourly"), how="outer").join(read("hourly_stages"), how="outer").fillna(0.0).reset_index()
    a = a[a.unit.isin(u.index)]
    a["fuel"] = a.unit.map(u.fuel)
    print("sanity: mean MW per hour, by stage (gas)")
    g = a[a.fuel == "gas"].groupby(["date", "hour"])[["pdbf_mwh", "pvp_mwh", "phfc_mwh", "p48_mwh"]].sum().mean()
    print(g.round(1).to_string())
    dv = hourly_drivers()
    groups = {"gas": a.fuel == "gas", "other_fossil": a.fuel == "other_fossil", "biomass_waste": a.fuel == "biomass_waste",
              "biomass_waste w/o five": (a.fuel == "biomass_waste") & ~a.unit.isin(FIVE)}
    rows = []
    for gname, sel in groups.items():
        s = a[sel].groupby(["date", "hour"])[["pdbf_mwh", "pvp_mwh", "phfc_mwh", "p48_mwh"]].sum()
        cap = u.cap[u.index.isin(a[sel].unit.unique())].sum()
        s["step1_constraints_dayahead"] = s.pvp_mwh - s.pdbf_mwh
        s["step2_intraday_markets"] = s.phfc_mwh - s.pvp_mwh
        s["step3_realtime_balancing"] = s.p48_mwh - s.phfc_mwh
        s["total"] = s.p48_mwh - s.pdbf_mwh
        s["pdbf_level"] = s.pdbf_mwh
        M = s.reset_index().merge(dv, on=["date", "hour"], how="inner")
        wk = pd.Series(M.date.dt.to_period("W").astype(str).factorize()[0], index=M.index)
        for y in ("pdbf_level", "step1_constraints_dayahead", "step2_intraday_markets", "step3_realtime_balancing", "total"):
            r = fit(M, y, wk)
            rows.append(dict(group=gname, cap_mw=cap, stage=y, per_cap_10eur=r["coef_per_10eur"] / cap, se=r["se"] / cap, t=r["t"], F=r["F"]))
    r = pd.DataFrame(rows)
    r.round(5).to_csv(OUT / "cogeneration_hourly_stages.csv", index=False)
    pd.set_option("display.width", 200)
    print(r.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
