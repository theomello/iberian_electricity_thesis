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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
