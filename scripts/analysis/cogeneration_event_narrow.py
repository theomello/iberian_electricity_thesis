#!/usr/bin/env python3
"""E1 in a narrow window: 14 days either side of each date, against placebos of the same width.

    .venv/bin/python scripts/analysis/cogeneration_event_narrow.py

The four-month E1 (cogeneration_event.py) fails its placebo gate because the gap between gas and renewable thermal
drifts over months. Here the window is 14 days before and 14 days from the break, so drift has less room. Same
estimator (`did`). Placebos on OMIE's label (daily from 2019): the same 28-day window on every date with the real
break's weekday whose window ends before 2022-03-29 (RDL 6/2022). `holiday` marks a placebo whose window touches
24 December - 6 January, Holy Week (Palm Sunday - Easter Monday) or August; the real windows touch none.
The gate is unchanged: each placebo below one third of the real break. Run with the user's go-ahead, 2026-11-11.

Writes outputs/tables/cogeneration_event_narrow_{estimates,placebo}.csv.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from cogeneration_event import did, omie, ree

OUT = Path(__file__).resolve().parent.parent.parent / "outputs" / "tables"
BREAKS = {"cap": "2022-06-15", "opt-in": "2022-10-01", "opt-in, first working day": "2022-10-03"}
HALF = pd.Timedelta(days=14)
EASTER = ["2019-04-21", "2020-04-12", "2021-04-04", "2022-04-17"]


def holiday(s: pd.Timestamp, e: pd.Timestamp) -> bool:
    days = pd.date_range(s, e)
    if ((days.month == 8) | ((days.month == 12) & (days.day >= 24)) | ((days.month == 1) & (days.day <= 6))).any():
        return True
    return any(((days >= pd.Timestamp(x) - pd.Timedelta(days=7)) & (days <= pd.Timestamp(x) + pd.Timedelta(days=1))).any()
               for x in EASTER)


def ree_2021() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load factor of REE's cogeneration units for every day of 2021 (fetched 2026-11-11 for the placebos)."""
    u = pd.read_parquet(OUT / "cogeneration_ree" / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    d = pd.concat(pd.read_parquet(f, columns=["date", "unit", "p48_mwh"])
                  for f in sorted((OUT / "cogeneration_ree" / "days").glob("ree_2021*.parquet")))
    w = d[d.unit.isin(u.index)].pivot_table(index="date", columns="unit", values="p48_mwh", aggfunc="sum").fillna(0.0)
    lf = (w / 24 / u.cap.reindex(w.columns)).clip(0, 1)
    lf.index = pd.to_datetime(lf.index)
    assert len(lf) == 365, f"2021 has {len(lf)} days on disk"
    return lf, u.rename(columns={"fuel": "group"})[["group", "cap", "agent"]]


def plant_placebos(est: pd.DataFrame) -> pd.DataFrame:
    """The 28-day window on every date of 2021 with the real break's weekday, on REE's plants."""
    lf, u = ree_2021()
    rows = []
    for name, b in BREAKS.items():
        b = pd.Timestamp(b)
        for t in ("gas", "other_fossil"):
            for wname in ("weighted", "unweighted"):
                real = est[(est.data == "ree") & (est.treated == t) & (est.window == name) & (est.weights == wname)].beta.iloc[0]
                for pb in pd.date_range("2021-01-15", "2021-12-18"):
                    s, e = pb - HALF, pb + HALF - pd.Timedelta(days=1)
                    if pb.dayofweek != b.dayofweek:
                        continue
                    v = did(lf, u, t, "biomass_waste", s, pb, e)[wname]
                    rows.append({"window": name, "treated": t, "weights": wname, "placebo_break": pb.date(),
                                 "beta": v["beta"], "se": v["se"], "over_real": abs(v["beta"] / real),
                                 "holiday": holiday(s, e), "real": real})
    p = pd.DataFrame(rows)
    p.round(4).to_csv(OUT / "cogeneration_event_narrow_placebo_plants.csv", index=False)
    print("\nplacebos on REE's plants, 2021, same weekday as the real break")
    for (name, t, wname), g in p.groupby(["window", "treated", "weights"]):
        print(f"  {name:25s} {t:12s} {wname:10s}: real {g.real.iloc[0]:+.3f}; {len(g)} placebos, sd {g.beta.std():.3f}, "
              f"range {g.beta.min():+.3f} to {g.beta.max():+.3f}, largest {g.over_real.max():.2f} of real, "
              f"above one third: {(g.over_real > 1 / 3).sum()}, as large as real: {(g.over_real >= 1).sum()}")
    g = p[(p.window == "cap") & (p.treated == "gas") & (p.weights == "weighted")]
    print("\ncap, gas, weighted: every placebo\n" + g[["placebo_break", "beta", "se", "over_real", "holiday"]].round(3).to_string(index=False))
    return p


def main() -> int:
    sets = {"ree": (ree(), [("gas", "biomass_waste"), ("other_fossil", "biomass_waste")]),
            "omie": (omie(), [("nonren", "renew")])}
    est, plac = [], []
    for src, ((lf, u), pairs) in sets.items():
        for t, c in pairs:
            for name, b in BREAKS.items():
                b = pd.Timestamp(b)
                for wname, v in did(lf, u, t, c, b - HALF, b, b + HALF - pd.Timedelta(days=1)).items():
                    est.append({"data": src, "treated": t, "window": name, "weights": wname, **v})
    lf, u = sets["omie"][0]
    for name, b in BREAKS.items():
        b = pd.Timestamp(b)
        real = did(lf, u, "nonren", "renew", b - HALF, b, b + HALF - pd.Timedelta(days=1))["weighted"]["beta"]
        for pb in pd.date_range("2019-01-15", "2022-03-14"):
            s, e = pb - HALF, pb + HALF - pd.Timedelta(days=1)
            if pb.dayofweek != b.dayofweek or s < lf.index.min() or e >= pd.Timestamp("2022-03-29"):
                continue
            v = did(lf, u, "nonren", "renew", s, pb, e)["weighted"]
            plac.append({"window": name, "placebo_break": pb.date(), "beta": v["beta"], "se": v["se"],
                         "over_real": abs(v["beta"] / real), "holiday": holiday(s, e), "real": real})
    est, plac = pd.DataFrame(est), pd.DataFrame(plac)
    est.round(4).to_csv(OUT / "cogeneration_event_narrow_estimates.csv", index=False)
    plac.round(4).to_csv(OUT / "cogeneration_event_narrow_placebo.csv", index=False)
    pd.set_option("display.width", 250)
    cols = ["data", "treated", "window", "weights", "beta", "se", "treated_change", "control_change", "g3_ratio",
            "treated_units", "control_units", "treated_pre_lf"]
    print("E1, 14 days either side (load factor, 0-1)\n" + est[cols].round(3).to_string(index=False))
    print("\nplacebos on OMIE's label, same weekday as the real break")
    for (name, hol), g in list(plac.groupby(["window", "holiday"])) + [((n, "all"), g) for n, g in plac.groupby("window")]:
        print(f"  {name:25s} holiday window {str(hol):5s}: real {g.real.iloc[0]:+.3f}; {len(g)} placebos, sd {g.beta.std():.3f}, "
              f"largest {g.over_real.max():.2f} of real, median {g.over_real.median():.2f}, "
              f"above one third: {(g.over_real > 1 / 3).sum()}, as large as real: {(g.over_real >= 1).sum()}")
    big = plac[(plac.window == "cap") & (plac.over_real > 1 / 3)]
    print("\ncap: placebos above one third\n" + big.round(3).to_string(index=False))
    if len(list((OUT / "cogeneration_ree" / "days").glob("ree_2021*.parquet"))) >= 365:
        plant_placebos(est)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
