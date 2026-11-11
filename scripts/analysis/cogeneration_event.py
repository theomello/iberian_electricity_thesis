#!/usr/bin/env python3
"""E1: gas cogeneration's load factor against renewable thermal around the gas cap's two dates.

    .venv/bin/python scripts/analysis/cogeneration_event.py

Design: docs/specs/2026-11-10-cogeneration-design.md §4 (E1) and §5 (gates G1, G3, G4). Two windows:
  cap     2022-04-01 -> 2022-07-31, break 2022-06-15 (gas cap starts; cogeneration in the regulated scheme excluded)
  opt-in  2022-07-01 -> 2022-12-31, break 2022-10-01 (it may waive the regulated payment and enter, RDL 17/2022)
Two data sets:
  ree    REE programming units by day (outputs/tables/cogeneration_ree/), fuel from REE's registers: gas against
         biomass and waste; other fossil against the same comparison group. The main one: plants, fuel known.
  omie   OMIE offer units (outputs/tables/cogeneration_panel/), OMIE's label: non-renewable against renewable thermal.
         Daily from 2019, so it carries the placebo breaks of gate G1.

Estimator: load factor on unit and date fixed effects and treated x after, on a balanced unit x day grid (a unit with
output before the break; a day with no schedule is zero). Balanced, so the coefficient is the difference between the
groups' mean (after - before) change, and the unit-clustered standard error is that of the units' changes. Reported
weighted by capacity (the effect on output) and unweighted (the average plant).

Gates: G1 placebo breaks, same window shape, on the 15th of each month 2019-04 -> 2022-01, each below one third of the
real break; G3 the comparison group's own change below one fifth of the treated group's; G4 dropping each of the five
largest units and each of the three largest agents.

Writes outputs/tables/cogeneration_event_{estimates,weekly,placebo,dropping}.csv.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
OUT = ROOT / "outputs" / "tables"
WINDOWS = {"cap": ("2022-04-01", "2022-06-15", "2022-07-31"),
           "cap, short": ("2022-05-15", "2022-06-15", "2022-07-15"),
           "opt-in": ("2022-07-01", "2022-10-01", "2022-12-31")}


def ree() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load factor, days x units, and the units' group, capacity and agent."""
    u = pd.read_parquet(OUT / "cogeneration_ree" / "ree_units.parquet")
    u = u[u.fuel.notna()].copy()
    u["cap"] = u.max_power_mw.where(u.max_power_mw > 0, u.peak_mw)
    u = u[u.cap > 0].set_index("unit")
    d = pd.concat(pd.read_parquet(f, columns=["date", "unit", "p48_mwh"])
                  for f in sorted((OUT / "cogeneration_ree" / "days").glob("ree_202[23]*.parquet")))
    d = d[d.unit.isin(u.index) & (d.date >= "2022-04-01") & (d.date <= "2023-03-31")]
    w = d.pivot_table(index="date", columns="unit", values="p48_mwh", aggfunc="sum").fillna(0.0)
    lf = (w / 24 / u.cap.reindex(w.columns)).clip(0, 1)
    lf.index = pd.to_datetime(lf.index)
    return lf, u.rename(columns={"fuel": "group"})[["group", "cap", "agent"]]


def omie() -> tuple[pd.DataFrame, pd.DataFrame]:
    r = pd.read_parquet(ROOT / "data" / "omie" / "registry" / "cogeneration_units.parquet")
    p = pd.concat(pd.read_parquet(f, columns=["date", "unit", "energy_mwh", "max_power_mw"])
                  for f in sorted((OUT / "cogeneration_panel").glob("panel_*.parquet")))
    cap = p[p.max_power_mw > 0].groupby("unit").max_power_mw.median()
    w = p.pivot_table(index="date", columns="unit", values="energy_mwh", aggfunc="sum").fillna(0.0)
    w = w[[c for c in w.columns if c in cap.index]]
    lf = (w / 24 / cap.reindex(w.columns)).clip(0, 1)
    lf.index = pd.to_datetime(lf.index)
    u = r.set_index("unit").reindex(lf.columns)[["label", "agent_owner"]].rename(
        columns={"label": "group", "agent_owner": "agent"})
    u["cap"] = cap
    return lf, u


def did(lf: pd.DataFrame, u: pd.DataFrame, treated: str, control: str, start: str, brk: str, end: str,
        drop: list[str] | None = None) -> dict:
    """Difference in the groups' mean change in load factor across the break."""
    pre, post = lf.loc[start:pd.Timestamp(brk) - pd.Timedelta(days=1)], lf.loc[brk:end]
    keep = pre.columns[(pre > 0).any()]
    if drop:
        keep = keep.difference(drop)
    ch = (post[keep].mean() - pre[keep].mean()).rename("ch").to_frame().join(u)
    out = {}
    for wname in ("weighted", "unweighted"):
        est = {}
        for g in (treated, control):
            x = ch[ch.group == g]
            w = (x.cap if wname == "weighted" else pd.Series(1.0, x.index)) / (x.cap.sum() if wname == "weighted" else len(x))
            m = float((w * x.ch).sum())
            est[g] = (m, float((w ** 2 * (x.ch - m) ** 2).sum() * len(x) / max(len(x) - 1, 1)), len(x), x.cap.sum())
        b = est[treated][0] - est[control][0]
        out[wname] = {"beta": b, "se": np.sqrt(est[treated][1] + est[control][1]), "treated_change": est[treated][0],
                      "control_change": est[control][0], "g3_ratio": abs(est[control][0] / est[treated][0]),
                      "treated_units": est[treated][2], "control_units": est[control][2],
                      "treated_mw": est[treated][3], "control_mw": est[control][3],
                      "treated_pre_lf": float(np.average(pre[ch.index[ch.group == treated]].mean(),
                                                         weights=ch.cap[ch.group == treated] if wname == "weighted" else None))}
    return out


def weekly(lf: pd.DataFrame, u: pd.DataFrame, treated: str, control: str, start: str, brk: str, end: str) -> pd.DataFrame:
    x = lf.loc[start:end]
    keep = x.columns[(x.loc[:pd.Timestamp(brk) - pd.Timedelta(days=1)] > 0).any()]
    wk = ((x.index - pd.Timestamp(brk)).days // 7)
    rows = {}
    for g in (treated, control):
        c = [k for k in keep if u.group.get(k) == g]
        rows[g] = (x[c] * u.cap[c]).sum(axis=1).groupby(wk).mean() / u.cap[c].sum()
    t = pd.DataFrame(rows)
    t["gap"] = t[treated] - t[control]
    t["gap_rel"] = t.gap - t.gap.loc[-1]
    return t.round(3).rename_axis("week")


def main() -> int:
    data = {"ree": (ree(), [("gas", "biomass_waste"), ("other_fossil", "biomass_waste")]),
            "omie": (omie(), [("nonren", "renew")])}
    est, wks, drops, plac = [], [], [], []
    for src, ((lf, u), pairs) in data.items():
        for t, c in pairs:
            for win, (s, b, e) in WINDOWS.items():
                r = did(lf, u, t, c, s, b, e)
                for wname, v in r.items():
                    est.append({"data": src, "treated": t, "control": c, "window": win, "weights": wname, **v})
                if win != "cap, short":
                    wks.append(weekly(lf, u, t, c, s, b, e).reset_index().assign(data=src, treated=t, window=win))
                    base = r["weighted"]["beta"]
                    uu = u[u.group == t]
                    big = list(uu.cap.sort_values().index[-5:])
                    ag = list(uu.groupby("agent").cap.sum().sort_values().index[-3:])
                    for kind, items in (("unit", big), ("agent", ag)):
                        for it in items:
                            dr = [it] if kind == "unit" else list(uu.index[uu.agent == it])
                            v = did(lf, u, t, c, s, b, e, drop=dr)["weighted"]
                            drops.append({"data": src, "treated": t, "window": win, "dropped": f"{kind} {it}",
                                          "mw": uu.cap.reindex(dr).sum(), "beta": v["beta"], "se": v["se"], "all": base})
    lf, u = data["omie"][0]
    for win in ("cap", "opt-in"):
        s, b, e = (pd.Timestamp(x) for x in WINDOWS[win])
        real = did(lf, u, "nonren", "renew", s, b, e)["weighted"]["beta"]
        for m in pd.period_range("2019-01", "2022-01", freq="M"):
            pb = pd.Timestamp(m.year, m.month, 15)
            ps, pe = pb - (b - s), pb + (e - b)
            if ps < lf.index.min() or pe >= pd.Timestamp("2022-03-29"):
                continue
            v = did(lf, u, "nonren", "renew", ps, pb, pe)["weighted"]
            plac.append({"window": win, "placebo_break": pb.date(), "beta": v["beta"], "se": v["se"],
                         "over_real": abs(v["beta"] / real)})
    est, drops, plac = pd.DataFrame(est), pd.DataFrame(drops), pd.DataFrame(plac)
    wks = pd.concat(wks)
    est.round(4).to_csv(OUT / "cogeneration_event_estimates.csv", index=False)
    wks.to_csv(OUT / "cogeneration_event_weekly.csv", index=False)
    drops.round(4).to_csv(OUT / "cogeneration_event_dropping.csv", index=False)
    plac.round(4).to_csv(OUT / "cogeneration_event_placebo.csv", index=False)

    pd.set_option("display.width", 250)
    print("E1 estimates (load factor, 0-1)\n" + est.round(3).to_string(index=False))
    print("\nG3: comparison group's change over the treated group's, must be below 0.20: see g3_ratio above")
    print("\nG4: weighted estimate after dropping each of the five largest units and three largest agents")
    print(drops.groupby(["data", "treated", "window"]).agg(all=("all", "first"), lowest=("beta", "min"),
                                                          highest=("beta", "max")).round(3).to_string())
    print("\nG1: placebo breaks on OMIE's label, 2019-04 -> 2022-01; each must be below one third of the real break")
    print(plac.groupby("window").agg(placebos=("beta", "size"), largest=("over_real", "max"),
                                     median=("over_real", "median"), above_third=("over_real", lambda s: (s > 1 / 3).sum())
                                     ).round(2).to_string())
    print(plac[plac.over_real > 1 / 3].round(3).to_string(index=False))
    for (src, t, win), g in wks.groupby(["data", "treated", "window"]):
        print(f"\nweekly gap, {src}, {t}, {win} (week 0 starts on the break)\n" + g.drop(columns=["data", "treated", "window"]).set_index("week").T.to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
