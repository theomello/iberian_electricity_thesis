#!/usr/bin/env python3
"""Date the break in storage-hydro owners' flat bidding.

    .venv/bin/python scripts/analysis/hydro_within_day_probe.py --all   # input
    .venv/bin/python scripts/analysis/hydro_flat_break.py
    .venv/bin/python scripts/analysis/hydro_flat_break.py --group REPSOL

WHY

`hydro_within_day_probe.py` found Iberdrola's storage-hydro units offering one
price in every hour of the day on ~0.8-0.9 of unit-days through 2023 and under
half from 2024. `notes/rq-midday-hydro.md` §3.2 says a dated break is worth far
more than a trend: a date can be set against policy and market-design events, a
drift cannot. This finds the date and asks whether it is sharp.

FOUR MEASURES OF A FLAT DAY, BECAUSE TWO ARE CENSORED

* `same_prices` -- the unit used the same SET of step prices in every period of
  the day, whatever the quantities. Read straight from the raw bids, so it does
  not depend on how much capacity was offered. The primary one.
  Steps under MIN_STEP_MW are ignored: Iberdrola adds a 0.1 MW step at
  0 EUR/MWh in some hours and not others (EBRA, 2023-03-15, around a 183 MW
  block at 498 EUR/MWh), and counting it put a spurious "break" on 2023-01-03.
* `same_curve` -- the identical curve, every price AND quantity step, in every
  period. Too strict to be the primary: offered quantities move a few percent
  from hour to hour (probe §3.4), which breaks identity while the prices hold.
  Only ~0.17 of Iberdrola's unit-days qualify even before any break.
* `flat_p50`, `flat_p25` -- the probe's measure: the price at 50% (25%) of
  capacity is identical in every period where it is defined. Undefined when a
  unit offers under that share of its capacity, which is common, so a unit-day
  is scored only if the price is defined in at least half its periods -- and
  the share of days that CAN be scored is reported, since a change in it would
  move these two measures without any change in bidding.

THE BREAK

Least-squares single mean shift on the DAILY share of the group's unit-days
that are flat, searched over the middle 70% of the sample. The 95% interval is
Bai's (1994) asymptotic one for a mean shift in a linear process:

    tau_hat +/- 11.03 * LRV / delta^2    days

with LRV the Newey-West long-run variance of the residuals, since the daily
series is strongly persistent. It is an approximation and is labelled as one;
the monthly table around the date is the check that the step is real.

A BALANCED PANEL, OR COMPOSITION MOVES THE SHARE

Units that enter or leave mid-window change the share without any unit changing
how it bids. Iberdrola's Tamega cascade in Portugal was commissioned inside the
window. So the break is estimated on units present across the whole archive,
and each unit's own break date is reported beside the group's.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from hydro_within_day_probe import BIDS, OUT_FULL, storage_hydro  # noqa: E402

TRIM = 0.15
MIN_STEP_MW = 1.0   # token steps below this carry no economic content
BAI_Q975 = 11.03   # 97.5% quantile of argmax of two-sided Brownian motion with drift

# Dated events a break could be set against. Sources: candidate-natural-
# experiments.md (RDL 17/2021, RDL 10/2022), CLAUDE.md (platform migration,
# 15-minute MTU).
EVENTS = {
    date(2021, 9, 16): "RDL 17/2021 clawback on non-emitting >10 MW begins",
    date(2022, 6, 15): "RDL 10/2022 gas cap begins",
    date(2024, 1, 1): "clawback and gas cap both end (in force to 2023-12-31)",
    date(2025, 3, 19): "SDAC offer typology (SCO) + 15-min intraday",
    date(2025, 4, 28): "Iberian blackout",
    date(2025, 10, 1): "15-minute day-ahead MTU",
}


def same_curve_days(units: list[str]) -> pd.DataFrame:
    """Per unit-day: did the unit submit one identical offer curve all day?"""
    out = []
    for f in sorted(BIDS.glob("bids_*.parquet")):
        t = pq.read_table(f, columns=["date", "period", "unit", "side", "status",
                                      "power_mw", "price_eur_mwh"],
                          filters=[("unit", "in", units), ("side", "==", "V"),
                                   ("status", "==", "O")]).to_pandas()
        t = t[t.power_mw >= MIN_STEP_MW]
        if t.empty:
            continue
        t = t.sort_values(["unit", "date", "period", "price_eur_mwh", "power_mw"])
        price = t.price_eur_mwh.round(2).astype(str)
        t["step"] = price + "@" + t.power_mw.round(1).astype(str)
        t["price"] = price
        per = t.groupby(["unit", "date", "period"])
        curve = per.step.agg("|".join)
        prices = per.price.agg(lambda x: "|".join(sorted(set(x))))
        per_day = pd.DataFrame({
            "n_periods": curve.groupby(["unit", "date"]).size(),
            "n_curves": curve.groupby(["unit", "date"]).nunique(),
            "n_price_sets": prices.groupby(["unit", "date"]).nunique(),
        })
        out.append(per_day.reset_index())
    d = pd.concat(out, ignore_index=True)
    d["date"] = pd.to_datetime(d["date"])
    d["same_curve"] = (d.n_curves == 1).astype(float)
    d["same_prices"] = (d.n_price_sets == 1).astype(float)
    return d


def probe_flat_days(units: list[str]) -> pd.DataFrame:
    p = pd.read_parquet(OUT_FULL, columns=["unit", "date", "period", "p25", "p50"])
    p = p[p.unit.isin(units)]
    g = p.groupby(["unit", "date"])
    agg = g.agg(n=("period", "size"), n25=("p25", "count"), n50=("p50", "count"),
                lo25=("p25", "min"), hi25=("p25", "max"),
                lo50=("p50", "min"), hi50=("p50", "max")).reset_index()
    for q in ("25", "50"):
        ok = agg[f"n{q}"] >= agg.n / 2
        agg[f"flat_p{q}"] = np.where(ok, (agg[f"hi{q}"] - agg[f"lo{q}"] < 0.01).astype(float),
                                     np.nan)
        agg[f"scored_p{q}"] = ok.astype(float)
    return agg[["unit", "date", "flat_p25", "flat_p50", "scored_p25", "scored_p50"]]


def newey_west(e: np.ndarray, lags: int) -> float:
    e = e - e.mean()
    v = e @ e / len(e)
    for k in range(1, lags + 1):
        v += 2 * (1 - k / (lags + 1)) * (e[k:] @ e[:-k]) / len(e)
    return v


def break_date(s: pd.Series) -> dict:
    """Single mean-shift break by least squares, with Bai's interval."""
    s = s.dropna()
    y = s.to_numpy()
    n = len(y)
    lo, hi = int(n * TRIM), int(n * (1 - TRIM))
    c = np.concatenate([[0.0], np.cumsum(y)])
    c2 = np.concatenate([[0.0], np.cumsum(y * y)])
    k = np.arange(lo, hi)
    ssr = (c2[k] - c[k] ** 2 / k) + ((c2[n] - c2[k]) - (c[n] - c[k]) ** 2 / (n - k))
    kb = int(k[np.argmin(ssr)])
    m1, m2 = y[:kb].mean(), y[kb:].mean()
    resid = np.concatenate([y[:kb] - m1, y[kb:] - m2])
    lrv = newey_west(resid, lags=int(4 * (n / 100) ** (2 / 9)))
    delta = m2 - m1
    idx = s.index
    tss = (y - y.mean()) @ (y - y.mean())
    if delta == 0 or tss == 0:
        return {"break": None, "before": m1, "after": m2, "delta": 0.0,
                "ci_lo": None, "ci_hi": None, "n_days": n, "ssr_gain": 0.0}
    half = BAI_Q975 * lrv / delta ** 2
    lo_i, hi_i = max(0, int(kb - np.ceil(half))), min(n - 1, int(kb + np.ceil(half)))
    return {"break": idx[kb].date(), "before": m1, "after": m2, "delta": delta,
            "ci_lo": idx[lo_i].date(), "ci_hi": idx[hi_i].date(), "n_days": n,
            "ssr_gain": 1 - ssr.min() / tss}


def fmt(b: dict) -> str:
    if b["break"] is None:
        return f"no variation ({b['before']:.2f} throughout, {b['n_days']:,} days)"
    return (f"{b['break']}  [{b['ci_lo']} .. {b['ci_hi']}]  "
            f"{b['before']:.2f} -> {b['after']:.2f}  "
            f"(R2 of the step {b['ssr_gain']:.2f}, {b['n_days']:,} days)")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--group", default="IBERDROLA")
    args = ap.parse_args()

    cap = storage_hydro()
    units = sorted(cap[cap.group == args.group].unit)
    sc = same_curve_days(units)
    fl = probe_flat_days(units)
    d = sc.merge(fl, on=["unit", "date"], how="outer")

    span = d.groupby("unit").date.agg(["min", "max", "count"])
    first, last = d.date.min(), d.date.max()
    full = span[(span["min"] <= first + pd.Timedelta(days=31))
                & (span["max"] >= last - pd.Timedelta(days=31))].index.tolist()
    print(f"{args.group}: {len(units)} storage-hydro units, {first.date()} .. {last.date()}")
    print(span.assign(balanced=span.index.isin(full)).to_string(), "\n")

    bal = d[d.unit.isin(full)]
    print(f"GROUP BREAK, balanced panel ({len(full)} units), daily share of flat unit-days")
    for col in ("same_prices", "flat_p50", "flat_p25", "same_curve"):
        s = bal.groupby("date")[col].mean()
        print(f"  {col:11s} {fmt(break_date(s))}")
    s_all = d.groupby("date").same_prices.mean()
    print(f"  {'same_prices':11s} {fmt(break_date(s_all))}   <- all units, unbalanced\n")

    for col in ("same_prices", "flat_p50"):
        print(f"PER-UNIT BREAK, {col}")
        for u in units:
            s = d[d.unit == u].set_index("date")[col].sort_index()
            if s.count() < 365:
                print(f"  {u:7s} too short ({s.count()} days)")
                continue
            print(f"  {u:7s} {fmt(break_date(s))}")
        print()

    # Centre everything below on the flat_p50 break: it is the robust one. The
    # same_prices step mostly disappears once token steps are dropped.
    b = break_date(bal.groupby("date").flat_p50.mean())
    bd = pd.Timestamp(b["break"])
    m = bal.assign(month=bal.date.dt.to_period("M"))
    win = m[(m.date >= bd - pd.DateOffset(months=8)) & (m.date < bd + pd.DateOffset(months=8))]
    print(f"MONTHLY flat_p50 share around its break, {bd.date()} (balanced panel)")
    tab = win.groupby(["month", "unit"]).flat_p50.mean().unstack()
    tab["all"] = win.groupby("month").flat_p50.mean()
    tab["same_prices"] = win.groupby("month").same_prices.mean()
    tab["scored_p50"] = win.groupby("month").scored_p50.mean()
    print(tab.round(2).to_string())

    print("\nWEEKLY share, 6 weeks either side")
    w = bal[(bal.date >= bd - pd.Timedelta(weeks=6)) & (bal.date < bd + pd.Timedelta(weeks=6))]
    print(w.groupby(pd.Grouper(key="date", freq="W-SUN"))[["flat_p50", "same_prices"]]
          .mean().round(2).to_string())

    # What changed: the hour-of-day shape of the p50 offer, a year either side.
    # All unit-days, flat ones included, so this is the average offer profile
    # and not the selected non-flat days the probe reports.
    p = pd.read_parquet(OUT_FULL, columns=["unit", "date", "hh", "p50", "price_es"])
    p = p[p.unit.isin(full) & p.p50.notna()]
    p["dev"] = p.p50 - p.groupby(["unit", "date"]).p50.transform("mean")
    yr = pd.DateOffset(years=1)
    before = p[(p.date >= bd - yr) & (p.date < bd)]
    after = p[(p.date >= bd) & (p.date < bd + yr)]
    prof = pd.DataFrame({
        "dev_before": before.groupby("hh").dev.mean(),
        "dev_after": after.groupby("hh").dev.mean(),
        "p*_before": before.groupby("hh").price_es.median(),
        "p*_after": after.groupby("hh").price_es.median(),
    })
    print("\nHOUR PROFILE of the p50 offer, deviation from the unit-day mean, "
          "EUR/MWh -- a year either side of the break")
    print(prof.reindex([2, 5, 8, 11, 13, 15, 18, 20, 21, 22]).round(1).T.to_string())

    print("\nEVENTS, days from the estimated break")
    for ev, label in EVENTS.items():
        print(f"  {ev}  {(ev - b['break']).days:+5d}  {label}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
