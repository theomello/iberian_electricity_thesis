#!/usr/bin/env python3
"""T2 of the nuclear-cuts design: the cuts a price-taking reactor would make.

    .venv/bin/python scripts/analysis/nuclear_cuts_benchmark.py

Design: docs/specs/2026-10-19-nuclear-cuts-design.md §4 T2. Reads T1's reactor-days
(`nuclear_cuts_daily.parquet`, from nuclear_cuts_describe.py). No estimation.

THE RULE. A price-taker runs a reactor in full when the price it expects for the day
is at least its cost, and goes down to its minimum load when the price is below it.
It cannot move faster than its ramp limit:
    target_t = 1 if p_exp_t >= c_t else m
    r_t      = clip(target_t, r_{t-1} - down, r_{t-1} + up)          (share of capacity)
    cut_t    = (1 - r_t) x capacity
p_exp is OMIP's price for the day as of D-2 (T1). c is each provisional bound in turn:
c_lo (fees and taxes, fuel worth 0), c_acct (fuel at book value), c_hi (fuel worth the
end-of-cycle price). The rule is myopic: it looks at one day, not the coming week.

LIMITS, from each reactor's own record (2018-2026, days with no declared outage):
  m          minimum load: the 2nd percentile of hourly schedule / capacity on its
             partial-cut hours (check: the 5th percentile)
  down, up   ramp: the 95th percentile of its day-to-day moves in daily mean schedule,
             among moves above 3% of capacity
Each run of consecutive available days starts at full output. Whole-day stops are left
out on both sides (T1: they are mostly on days the outage register misses).

COMPARISON, by year and bound: actual and simulated cut, their overlap
sum(min(actual, sim)), the EXCESS sum(max(0, actual - sim)) (cut a price-taker would not
make: what market power, technical limits or a higher fuel value must explain) and the
MISSING sum(max(0, sim - actual)) (cut a price-taker would make and the reactor did not).

CHECK, hourly and unconstrained: cut every hour whose realised price is below c, down to
m, no ramp limit. Realised prices are moved by the cuts themselves, so this is an upper
bound on how much price-taking flexibility could explain, not a forecast.

OUTPUTS: outputs/tables/nuclear_cuts_benchmark_daily.parquet, nuclear_cuts_benchmark.csv
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
TABLES = ROOT / "outputs/tables"
OUT_DAILY = TABLES / "nuclear_cuts_benchmark_daily.parquet"
OUT = TABLES / "nuclear_cuts_benchmark.csv"
BOUNDS = ["c_lo", "c_acct", "c_hi"]
MOVE = 0.03          # a day-to-day move counts above this share of capacity
FREE = {"economic"}


def limits(d: pd.DataFrame, h: pd.DataFrame, q_min: float) -> pd.DataFrame:
    """unit -> m, down, up from the reactor's own record."""
    part = d[d.form == "partial"][["unit", "date"]]
    hp = h.merge(part, on=["unit", "date"])
    hp = hp[hp.sched_mw > 0]
    m = (hp.sched_mw / hp.cap_mw).groupby(hp.unit).quantile(q_min).rename("m")
    s = d[d.form.isin(["partial", "none"])].sort_values(["unit", "date"]).copy()
    s["r"] = s.sched_mw / s.cap_mw
    s["dr"] = s.groupby("unit").r.diff().where(s.groupby("unit").date.diff().dt.days.eq(1))
    mv = s[s.dr.abs() > MOVE]
    down = mv[mv.dr < 0].dr.abs().groupby(mv.unit).quantile(0.95).rename("down")
    up = mv[mv.dr > 0].dr.groupby(mv.unit).quantile(0.95).rename("up")
    return pd.concat([m, down, up], axis=1)


def simulate(d: pd.DataFrame, lim: pd.DataFrame, bound: str, ramp: bool = True) -> np.ndarray:
    """Simulated cut (MW, daily mean) for each row of d, in d's order."""
    out = np.zeros(len(d))
    for u, g in d.groupby("unit", sort=False):
        m, dn, upl = lim.loc[u, ["m", "down", "up"]]
        if not ramp:
            dn = upl = 1.0
        idx = g.index.to_numpy()
        new_run = g.date.diff().dt.days.ne(1).to_numpy()
        r = 1.0
        for k, (i, nr) in enumerate(zip(idx, new_run)):
            if nr:
                r = 1.0
            p, c = d.at[i, "p_exp"], d.at[i, bound]
            target = 1.0 if (np.isnan(p) or np.isnan(c) or p >= c) else m
            r = float(np.clip(target, r - dn, r + upl))
            out[d.index.get_loc(i)] = (1 - r) * d.at[i, "cap_mw"]
    return out


def compare(d: pd.DataFrame, sim: str, by: list[str]) -> pd.DataFrame:
    a, s = d.cut_mw, d[sim]
    t = d.assign(actual=a, sim=s, overlap=np.minimum(a, s), excess=(a - s).clip(lower=0),
                 missing=(s - a).clip(lower=0))
    g = t.groupby(by)[["actual", "sim", "overlap", "excess", "missing"]].sum() * 24 / 1e6   # TWh
    g["explained"] = g.overlap / g.actual
    return g.round(3)


def main() -> int:
    d = pd.read_parquet(TABLES / "nuclear_cuts_daily.parquet")
    d = d[d.form.isin(["partial", "none"])].sort_values(["unit", "date"]).reset_index(drop=True)
    h = pd.read_parquet(TABLES / "reactor_outage_hours.parquet",
                        columns=["unit", "utc", "cap_mw", "sched_mw", "cls", "lost_decl_mw", "lost_undecl_mw"])
    h["date"] = h.utc.dt.tz_convert("Europe/Madrid").dt.tz_localize(None).dt.normalize()
    h = h.merge(d[["unit", "date", "c_lo", "c_acct", "c_hi"]], on=["unit", "date"])
    h["cut_mw"] = h.lost_undecl_mw.fillna(0) + np.where(h.cls.isin(FREE), h.lost_decl_mw, 0.0)

    rows = []

    def show(title, df):
        print(f"\n{title}\n{df.to_string()}")
        rows.append(df.assign(table=title).reset_index())

    for q, lab in ((0.02, "main"), (0.05, "check")):
        lim = limits(d, h, q)
        show(f"LIMITS ({lab}: minimum load at the {int(q * 100)}th percentile), share of capacity", lim.round(3))
        if lab == "main":
            main_lim = lim
    d["era"] = np.where(d.year >= 2024, "2024-2026", "2018-2023")
    for b in BOUNDS:
        d[f"sim_{b}"] = simulate(d, main_lim, b)
        d[f"sim_{b}_noramp"] = simulate(d, main_lim, b, ramp=False)
    d["sim_c_acct_m5"] = simulate(d, limits(d, h, 0.05), "c_acct")

    print(f"\n{len(d):,} reactor-days; expected price missing on {d.p_exp.isna().sum()} (treated as no cut)")
    for b in BOUNDS:
        show(f"ACTUAL against the price-taker at {b}, TWh, by year (ramp limits, minimum load at 2nd pct)",
             compare(d, f"sim_{b}", ["year"]))
    show("2024-2026 by reactor, price-taker at c_acct", compare(d[d.year >= 2024], "sim_c_acct", ["unit"]))
    show("2024-2026 by reactor, price-taker at c_hi", compare(d[d.year >= 2024], "sim_c_hi", ["unit"]))
    show("checks, by era: no ramp limit; minimum load at the 5th percentile (c_acct)",
         pd.concat({f"{b} no ramp": compare(d, f"sim_{b}_noramp", ["era"]) for b in BOUNDS} |
                   {"c_acct, m at 5th pct": compare(d, "sim_c_acct_m5", ["era"])}))

    # day-level agreement, cuts of at least 10% of capacity
    for b in ("c_acct", "c_hi"):
        a = d.cut_mw >= 0.1 * d.cap_mw
        s = d[f"sim_{b}"] >= 0.1 * d.cap_mw
        show(f"days with a cut of at least 10% of capacity, actual x price-taker at {b}, 2024-2026",
             pd.crosstab(a[d.year >= 2024].rename("actual"), s[d.year >= 2024].rename("price-taker")))
        cc = d.groupby("era").apply(lambda g: np.corrcoef(g.cut_mw, g[f"sim_{b}"])[0, 1], include_groups=False)
        show(f"correlation of daily cut, actual with price-taker at {b}", cc.round(3).to_frame("corr"))

    # where the excess sits: expected price relative to the bound
    e = d[d.year >= 2024].copy()
    for b in ("c_acct", "c_hi"):
        e["gap"] = pd.cut(e.p_exp - e[b], [-1e9, -20, -10, -5, 0, 5, 10, 20, 1e9])
        e["excess"] = (e.cut_mw - e[f"sim_{b}"]).clip(lower=0)
        e["missing"] = (e[f"sim_{b}"] - e.cut_mw).clip(lower=0)
        show(f"2024-2026: excess and missing cut (TWh) by expected price minus {b}, EUR/MWh",
             (e.groupby("gap", observed=False)[["cut_mw", f"sim_{b}", "excess", "missing"]].sum() * 24 / 1e6).round(3))

    # hourly, unconstrained check on realised prices
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["utc_timestamp", "price_es"])
    px["utc"] = pd.to_datetime(px.utc_timestamp, utc=True).dt.floor("h")
    h = h.merge(px.groupby("utc").price_es.mean().rename("p").reset_index(), on="utc", how="left")
    h["m"] = h.unit.map(main_lim.m)
    h["year"] = h.date.dt.year
    hr = []
    for b in BOUNDS:
        s = np.where(h.p < h[b], (1 - h.m) * h.cap_mw, 0.0)
        t = h.assign(actual=h.cut_mw, sim=s, overlap=np.minimum(h.cut_mw, s),
                     excess=(h.cut_mw - s).clip(lower=0), missing=(s - h.cut_mw).clip(lower=0))
        g = t.groupby("year")[["actual", "sim", "overlap", "excess", "missing"]].sum() / 1e6
        g["explained"] = g.overlap / g.actual
        hr.append(g.round(3).assign(bound=b))
    show("CHECK, hourly on realised prices, no ramp limit, TWh", pd.concat(hr).set_index("bound", append=True).unstack("bound"))

    TABLES.mkdir(parents=True, exist_ok=True)
    d.to_parquet(OUT_DAILY, index=False)
    pd.concat(rows, ignore_index=True).to_csv(OUT, index=False)
    print(f"\nwrote {OUT_DAILY.relative_to(ROOT)}, {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
