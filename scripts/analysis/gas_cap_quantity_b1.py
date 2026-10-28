#!/usr/bin/env python3
"""Step B1 of the crisis quantity design: how large is the effect Branch B must detect, and can it?
(docs/specs/2026-10-28-crisis-quantity-design.md §7, fixed before running)

    .venv/bin/python scripts/analysis/gas_cap_quantity_b1.py [--reps 199]

1. The two ends. For each Iberian gas unit, its offer steps over the last eight weeks before the cap
   (2022-04-20 -> 2022-06-14), in predicted in-money hours, as markups m = p - gross cost, pooled by
   hour of day (all hours of the unit if a cell has fewer than 5 days). F(x) = the unit's mean share
   of K offered at markup <= x. After 2022-06-15, with the day's bid-time subsidy S:
       full pass-through (offers at net cost + m):  run20 = F(20),      run20_gross = F(20 + S)
       none (offers at gross cost + m):              run20 = F(20 - S),  run20_gross = F(20)
   The gap full - none is averaged as Branch B will average the outcome: weekly unit means over the
   main sample, then the mean over units, then over weeks with a subsidy.
2. Minimum detectable effect. Estimator B (Xu 2017, `gas_cap_ife.gsc`) on weekly unit means of the
   outcome, main sample, weeks before 2022-06-15 only, treating Iberia as capped from a placebo date
   (2022-01-01, 2022-03-01). r by Xu's cross-validation on the weeks before the placebo. The mean gap
   from the placebo to 2022-06-14, firm block bootstrap within country; MDE = 2.8 x its standard
   error (5% two-sided, 80% power).
Stop rule, per outcome: stop if the MDE at either placebo exceeds half the full-none gap.

Main sample: predicted in-money unit-hours (same zone-hour price the day before minus cost after the
subsidy > EUR 50), Italian essential units out. Units with at most 30% of weeks missing over
2021-10-01 -> 2023-06-30 (50% if fewer than 25 Iberian units pass; stop below 25).

Writes outputs/tables/gas_cap_quantity_b1_ends.csv (weekly ends) and gas_cap_quantity_b1_mde.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import gsc, xu_cv  # noqa: E402
from gas_cap_offer_panel import iberia_steps  # noqa: E402

PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
T = ROOT / "outputs" / "tables"
WIN0, END = pd.Timestamp("2021-10-01"), pd.Timestamp("2023-06-30")
CAP0 = pd.Timestamp("2022-06-15")
REF0 = CAP0 - pd.Timedelta(weeks=8)
PLACEBOS = [pd.Timestamp("2022-01-01"), pd.Timestamp("2022-03-01")]
MARGIN, RUN, MIN_DAYS, MIN_UNITS = 50.0, 20.0, 5, 25


def panel(margin: float | None = MARGIN) -> pd.DataFrame:
    """Main sample; `margin=None` keeps every hour (no in-money condition)."""
    h = pd.read_parquet(PANEL, columns=["unit", "date", "period", "iberia", "zone", "firm", "cost", "cost_gross",
                                        "subsidy", "price", "run20", "run20_gross", "essential"])
    p = h.groupby(["zone", "date", "period"], as_index=False).price.first()
    p["date"] = p.date + pd.Timedelta(days=1)
    h = h.merge(p.rename(columns={"price": "price_lag"}), on=["zone", "date", "period"], how="left")
    h["firm"] = h.firm.fillna(h.unit)
    inm = (h.price_lag - h.cost) > margin if margin is not None else True
    h = h[~h.essential & h.cost.notna() & inm & h.date.between(WIN0, END)]
    h["w"] = h.date.dt.to_period("W").dt.start_time
    return h


def matrix(h: pd.DataFrame, y: str) -> tuple[pd.DataFrame, float]:
    W = h.groupby(["unit", "w"])[y].mean().unstack()
    weeks = pd.date_range(WIN0.to_period("W").start_time, END, freq="W-MON")
    W = W.reindex(columns=weeks)
    ib = h.drop_duplicates("unit").set_index("unit").iberia
    for thr in (0.30, 0.50):
        keep = W.isna().mean(axis=1) <= thr
        if ib.reindex(W.index[keep]).sum() >= MIN_UNITS:
            return W[keep], thr
    return W.iloc[0:0], float("nan")


def ends(h: pd.DataFrame) -> pd.DataFrame:
    s, cost = iberia_steps()
    ib = h[h.iberia]
    # K per unit, as the panel defines it: 99th percentile of hourly offered MW before the cap.
    off = s.groupby(["unit", "date", "period"]).mw.sum()
    pre = off[off.index.get_level_values("date") <= CAP0 - pd.Timedelta(days=1)]
    K = pre.groupby("unit").quantile(0.99).rename("K")
    ref_keys = ib[ib.date.between(REF0, CAP0 - pd.Timedelta(days=1))][["unit", "date", "period"]]
    r = s.merge(ref_keys, on=["unit", "date", "period"]).merge(cost[["unit", "date", "cost_gross"]],
                                                              on=["unit", "date"])
    r = r.merge(K, on="unit")
    r["m"] = r.p - r.cost_gross
    r["hod"] = r.period.clip(upper=24)
    days_cell = r.groupby(["unit", "hod"]).date.nunique().rename("days")
    r = r.merge(days_cell, on=["unit", "hod"])
    hours_cell = r.groupby(["unit", "hod"])[["date", "period"]].apply(lambda x: len(x.drop_duplicates())).rename("nh")
    hours_unit = r.groupby("unit")[["date", "period"]].apply(lambda x: len(x.drop_duplicates())).rename("nhu")
    r = r.merge(hours_cell, on=["unit", "hod"]).merge(hours_unit, on="unit")
    post = ib[ib.date >= CAP0][["unit", "date", "period", "w", "subsidy"]].copy()
    post["hod"] = post.period.clip(upper=24)
    out = []
    for (u, hod), g in post.groupby(["unit", "hod"]):
        c = r[(r.unit == u) & (r.hod == hod)]
        if c.empty or c.days.iat[0] < MIN_DAYS:
            c = r[r.unit == u]
            if c.empty:
                continue
            n = c.nhu.iat[0]
        else:
            n = c.nh.iat[0]
        o = np.argsort(c.m.to_numpy())
        m = c.m.to_numpy()[o]
        cw = np.cumsum((c.mw / c.K).to_numpy()[o]) / n
        F = lambda x: np.where(np.searchsorted(m, x, side="right") > 0,
                               cw[np.maximum(np.searchsorted(m, x, side="right") - 1, 0)], 0.0)
        S = g.subsidy.to_numpy()
        out.append(g.assign(full_run20=F(np.full_like(S, RUN)), none_run20=F(RUN - S),
                            full_run20_gross=F(RUN + S), none_run20_gross=F(np.full_like(S, RUN))))
    e = pd.concat(out)
    wk = e.groupby(["unit", "w"])[["full_run20", "none_run20", "full_run20_gross", "none_run20_gross", "subsidy"]].mean()
    return wk.groupby("w").mean()


def placebo_mde(W: pd.DataFrame, ib: np.ndarray, firm: np.ndarray, reps: int, rng) -> list[dict]:
    cols = W.columns
    keep = cols < CAP0
    M = W.loc[:, keep].to_numpy()
    c = cols[keep]
    rows = []
    for p in PLACEBOS:
        pre = c < p
        post = ~pre
        r = int(np.argmin(xu_cv(M, ib, pre)))
        est = float(np.nanmean(gsc(M, ib, pre, r)[post]))
        fi = pd.Series(firm)
        groups = {k: fi[ib == k].unique() for k in (True, False)}
        draws = []
        for _ in range(reps):
            idx = np.concatenate([np.flatnonzero((fi.to_numpy() == f_) & (ib == k))
                                  for k in (True, False)
                                  for f_ in rng.choice(groups[k], size=len(groups[k]), replace=True)])
            draws.append(np.nanmean(gsc(M[idx], ib[idx], pre, r)[post]))
        se = float(np.nanstd(draws, ddof=1))
        rows.append({"placebo": p.date(), "r": r, "gap": est, "se": se, "mde": 2.8 * se,
                     "iberian_firms": len(groups[True]), "italian_firms": len(groups[False])})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261028)
    h = panel()
    e = ends(h)
    zero = e[e.subsidy == 0]
    assert np.allclose(zero.full_run20, zero.none_run20) and np.allclose(zero.full_run20_gross, zero.none_run20_gross), \
        "the two ends must coincide where there is no subsidy"
    print(f"check: ends coincide on all {len(zero)} post-cap weeks without a subsidy")
    bind = e[e.subsidy > 0]
    gap = {"run20": float((bind.full_run20 - bind.none_run20).mean()),
           "run20_gross": float((bind.full_run20_gross - bind.none_run20_gross).mean())}
    e.to_csv(T / "gas_cap_quantity_b1_ends.csv")
    print(f"ends over {len(bind)} weeks with a subsidy (mean S {bind.subsidy.mean():.1f}):")
    print(bind[["full_run20", "none_run20", "full_run20_gross", "none_run20_gross"]].mean().round(3).to_string())
    print("full - none gap:", {k: round(v, 3) for k, v in gap.items()})
    rows = []
    for y in ("run20", "run20_gross"):
        W, thr = matrix(h, y)
        if W.empty:
            print(f"{y}: fewer than {MIN_UNITS} Iberian units pass at 50% missing weeks -> STOP")
            continue
        meta = h.drop_duplicates("unit").set_index("unit")
        ib = meta.iberia.reindex(W.index).to_numpy()
        firm = meta.firm.reindex(W.index).to_numpy()
        print(f"\n{y}: {ib.sum()} Iberian, {(~ib).sum()} Italian units (missing-week limit {thr:.0%})")
        for row in placebo_mde(W, ib, firm, a.reps, rng):
            row.update(outcome=y, threshold=0.5 * gap[y], unit_limit=thr,
                       iberian_units=int(ib.sum()), italian_units=int((~ib).sum()))
            row["fails"] = row["mde"] > row["threshold"]
            rows.append(row)
            print(f"  placebo {row['placebo']}: r {row['r']}, gap {row['gap']:+.3f} (se {row['se']:.3f}), "
                  f"MDE {row['mde']:.3f} vs half the gap {row['threshold']:.3f}{'  <-- FAILS' if row['fails'] else ''}")
    out = pd.DataFrame(rows)
    out.to_csv(T / "gas_cap_quantity_b1_mde.csv", index=False)
    for y in ("run20", "run20_gross"):
        f = out[out.outcome == y]
        verdict = "no units" if f.empty else ("STOP" if f.fails.any() else "PASS")
        print(f"B1 rule, {y}: {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
