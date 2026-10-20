#!/usr/bin/env python3
"""The running variable of the minimum-income near-miss design: each declaring unit-day's margin.

    .venv/bin/python scripts/build/build_mic_running.py [--months 201901 ...]

Spec `docs/specs/2026-10-20-mic-near-miss-design.md` §2, §3.1, §8. For every sell unit-day
in `cab` declaring a minimum-income condition (fixed term F > 0 or variable term v > 0),
2019-01-01 → 2025-03-18:

    r   = (Σ_h p_h q_h − F) / Σ_h q_h − v         (€/MWh)

with p_h the published price of the unit's country and q_h its offered sell MW (status O)
at or below it. r ≥ 0: the offered output would have met the condition.

ACCEPTED means cleared (status C) in at least 4 periods. A withdrawn plant can clear in the
first 1–3 hours while it ramps down (OMIE's scheduled stop); those count as withdrawn.

r_A IS THE MARGIN HAD THE UNIT RUN. Withdrawing a plant raises the price, so a withdrawn
unit's r at the final prices overstates what it would have earned. For accepted units r_A =
r. For withdrawn units with r ≥ −5 (r_A ≤ r, so the rest stay outside any bandwidth), each
hour is re-cleared on the step cache's effective curve (`analysis/step_curves.py`:
`market_YYYYMM`, `hours_YYYYMM`) with the unit's offered steps below the price added
(`shift_price`); the price had it run is p_h + (p_clear' − p_clear), the shift and not the
re-cleared level, so the re-clearing error on the published price cancels. Hours the cache
marks not `valid` (split, clearing identity off, re-clear more than €0.50 from the price)
keep p_h and are counted in `n_left_out`; `flag` marks days with more than four. Other
units with a condition keep their status: first order, not OMIE's joint search. Days
without 24 periods (DST) are not in the cache and are left out.

Writes outputs/tables/mic_running.parquet: date, unit, country, group (largest owner that
day), F, v, cap_mw, q_mwh, rev, r, hours_cleared, accepted, r_A, far (withdrawn with
r < −5: r_A = r, not re-cleared), n_hours, n_left_out, flag, dp_mean (mean price shift over
the unit's hours, €/MWh).
"""
from __future__ import annotations

import sys
import time
from argparse import ArgumentParser
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "lib"))
from unit_ownership import majority_group, spells  # noqa: E402

DATA = ROOT / "data"
CACHE = ROOT / "outputs/cache/step"
OUT = ROOT / "outputs/tables/mic_running.parquet"
FIRST, LAST = "201901", "202503"
LAST_DAY = pd.Timestamp("2025-03-18")      # the variable term ends with cab's wide layout
MIN_HOURS = 4                              # cleared in fewer: the scheduled stop
FAR = -5.0                                 # r below this: not re-cleared
MAX_LEFT_OUT = 4
EPS = 0.005                                # €/MWh, as step_curves


def shift_price(prices: np.ndarray, a: np.ndarray, d_tot: float, add_p: np.ndarray, add_mw: np.ndarray) -> float:
    """One hour: the lowest price on the union grid where the effective curve's cumulative MW
    (`a` at the ascending unique `prices`) plus the added steps at or below it covers d_tot."""
    grid = np.union1d(prices, add_p)
    i = np.searchsorted(prices, grid, side="right") - 1
    base = np.where(i >= 0, a[np.maximum(i, 0)], 0.0)
    if len(add_p):
        order = np.argsort(add_p, kind="stable")
        cum = np.cumsum(add_mw[order])
        j = np.searchsorted(add_p[order], grid, side="right") - 1
        base = base + np.where(j >= 0, cum[np.maximum(j, 0)], 0.0)
    hit = np.nonzero(base - d_tot >= 0)[0]
    return float(grid[hit[0]]) if len(hit) else float("nan")


def declaring(ym: str) -> pd.DataFrame:
    c = pd.read_parquet(DATA / f"omie/cab/parquet/cab_{ym}.parquet",
                        columns=["date", "unit", "side", "version", "min_income_fixed_eur",
                                 "min_income_var_eur_mwh", "max_power_mw"])
    c = c[(c.side == "V") & ((c.min_income_fixed_eur > 0) | (c.min_income_var_eur_mwh > 0))].copy()
    c["date"] = pd.to_datetime(c.date)
    c["unit"] = c.unit.astype(str)
    c = c[c.date <= LAST_DAY].sort_values("version").drop_duplicates(["date", "unit"], keep="last")
    return c.rename(columns={"min_income_fixed_eur": "F", "min_income_var_eur_mwh": "v",
                             "max_power_mw": "cap_mw"})[["date", "unit", "F", "v", "cap_mw"]]


def month(ym: str, country: dict, px: pd.DataFrame) -> pd.DataFrame:
    dec = declaring(ym)
    hours = pd.read_parquet(CACHE / f"hours_{ym}.parquet", columns=["hid", "date", "period", "p_clear", "valid", "d_tot"])
    hours["date"] = pd.to_datetime(hours.date)
    dec = dec[dec.date.isin(hours.date.unique())]
    if dec.empty:
        return dec
    b = pq.read_table(DATA / f"omie/bids/parquet/bids_{ym}.parquet",
                      columns=["date", "period", "unit", "side", "status", "power_mw", "price_eur_mwh"],
                      filters=[("side", "==", "V")]).to_pandas()
    b["unit"] = b.unit.astype(str)
    b["status"] = b.status.astype(str)
    b["date"] = pd.to_datetime(b.date)
    b = b[b.unit.isin(set(dec.unit)) & (b.power_mw > 0)].merge(dec[["date", "unit"]], on=["date", "unit"])
    b = b.merge(px, on=["date", "period"]).merge(hours, on=["date", "period"])
    b["pt"] = b.unit.map(country).eq("PT")
    b["p"] = np.where(b.pt, b.price_pt, b.price_es)

    cl = (b[b.status == "C"].groupby(["date", "unit"]).period.nunique().rename("hours_cleared"))
    o = b[b.status == "O"]
    at = o[o.price_eur_mwh <= o.p + EPS]
    agg = (at.assign(rev=at.power_mw * at.p).groupby(["date", "unit"])
           .agg(q_mwh=("power_mw", "sum"), rev=("rev", "sum")))
    d = dec.merge(agg.reset_index(), on=["date", "unit"], how="left").merge(cl.reset_index(), on=["date", "unit"], how="left")
    d[["q_mwh", "rev", "hours_cleared"]] = d[["q_mwh", "rev", "hours_cleared"]].fillna(0)
    d["hours_cleared"] = d.hours_cleared.astype(int)
    d["accepted"] = d.hours_cleared >= MIN_HOURS
    d["r"] = np.where(d.q_mwh > 0, (d.rev - d.F) / d.q_mwh.where(d.q_mwh > 0) - d.v, np.nan)
    d["r_A"] = d.r
    d["far"] = ~d.accepted & (d.r < FAR)
    d["n_hours"] = 24
    d["n_left_out"] = 0
    d["dp_mean"] = 0.0

    todo = d[~d.accepted & (d.r >= FAR)]
    if len(todo):
        mk = pd.read_parquet(CACHE / f"market_{ym}.parquet")
        mk = mk[mk.hid.isin(hours.hid)].sort_values(["hid", "price"])
        mh = {h: (g.price.to_numpy(), g.a.to_numpy()) for h, g in mk.groupby("hid", sort=False)}
        dtot = hours.set_index("hid").d_tot.to_dict()
        pcl = hours.set_index("hid").p_clear.to_dict()
        ok = hours.set_index("hid").valid.to_dict()
        oo = o.merge(todo[["date", "unit"]], on=["date", "unit"])
        for (dt, u), g in oo.groupby(["date", "unit"], sort=False):
            row = d.index[(d.date == dt) & (d.unit == u)][0]
            F, v = d.at[row, "F"], d.at[row, "v"]
            q_tot = rev = 0.0
            left, shifts = 0, []
            for hid_, s in g.groupby("hid", sort=False):
                p = float(s.p.iloc[0])
                if ok.get(hid_, False) and hid_ in mh:
                    add = s[s.price_eur_mwh < p - EPS]
                    pr, a = mh[hid_]
                    p_new = shift_price(pr, a, dtot[hid_], add.price_eur_mwh.to_numpy(float), add.power_mw.to_numpy(float))
                    dp = min(p_new - pcl[hid_], 0.0) if np.isfinite(p_new) else 0.0
                else:
                    left, dp = left + 1, 0.0
                shifts.append(dp)
                pa_ = p + dp
                q = float(s.power_mw[s.price_eur_mwh <= pa_ + EPS].sum())
                q_tot += q
                rev += q * pa_
            d.at[row, "r_A"] = (rev - F) / q_tot - v if q_tot > 0 else np.nan
            d.at[row, "n_left_out"] = left
            d.at[row, "dp_mean"] = float(np.mean(shifts)) if shifts else 0.0
    d["flag"] = d.n_left_out > MAX_LEFT_OUT
    d["country"] = d.unit.map(country)
    return d


def main() -> int:
    ap = ArgumentParser(description=__doc__)
    ap.add_argument("--months", nargs="*")
    args = ap.parse_args()
    months = args.months or [p.strftime("%Y%m") for p in pd.period_range(FIRST[:4] + "-" + FIRST[4:], LAST[:4] + "-" + LAST[4:], freq="M")]
    reg = pd.read_parquet(DATA / "omie/registry/unit_registry.parquet", columns=["unit", "country"])
    country = dict(zip(reg.unit.astype(str), reg.country.astype(str)))
    px = pd.read_parquet(DATA / "omie/prices/omie_day_ahead_prices.parquet", columns=["date", "period", "price_es", "price_pt"])
    px["date"] = pd.to_datetime(px.date)
    out = []
    for ym in months:
        t0 = time.time()
        m = month(ym, country, px)
        out.append(m)
        print(f"  {ym}  {len(m):5d} unit-days, {int((~m.accepted).sum()) if len(m) else 0:5d} withdrawn, "
              f"{time.time() - t0:5.1f}s", flush=True)
    d = pd.concat(out, ignore_index=True)
    d["group"] = majority_group(d, spells(), unit_col="unit", date_col="date")
    cols = ["date", "unit", "country", "group", "F", "v", "cap_mw", "q_mwh", "rev", "r", "hours_cleared", "accepted",
            "r_A", "far", "n_hours", "n_left_out", "flag", "dp_mean"]
    if args.months:
        print(d[cols].head())
        return 0
    d[cols].to_parquet(OUT, index=False)
    print(f"wrote {OUT.relative_to(ROOT)}: {len(d):,} unit-days, {d.unit.nunique()} units, "
          f"{int(d.flag.sum()):,} flagged, |r_A| < 2: {int((d.r_A.abs() < 2).sum()):,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
