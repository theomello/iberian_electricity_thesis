#!/usr/bin/env python3
"""Step 1 of the gas-cap design again, on capacity offered near cost in hours a plant can expect
to be in the money (2026-10-28; idea from the second repo sweep, `notes/rq-gas-cap-declared-cost.md`).

    .venv/bin/python scripts/analysis/gas_cap_inmoney_pretrend.py

Why. The price outcomes (p50, m25, p_mid) read fixed shares of capacity, which often land in
high-priced blocks that almost never clear (the Spanish price reached EUR 450 in 48 of 6,168
hours from 2021-10-01 to the cap), and Iberia could not post such blocks before 2021-07-07
(OMIE's limits were EUR 0-180.30). `run20` (MW offered at or below cost + 20, over K) ignores
the price of blocks that do not run, but pooled over all hours it also counts hours a plant
was never going to run (in-money unit-hours went from 4-16% in June-August 2021 to about half
from September 2021).

Sample. Unit-hours whose expected margin is positive: the price of the same zone and hour the
day before (known when offers close at 12:00 on D-1) minus the unit's cost (after the subsidy)
above M. Main M = EUR 50, check M = EUR 20; also the realised-price version, for comparison only
(it conditions on the outcome the offers set).

Rule: design §6 step 1 second run, unchanged. Weekly Iberia-Italy gap in unit-demeaned run20
over 2021-06-15 -> 2022-06-14: stop if its trend is significant at 5% (Newey-West, 4 lags) and
over a year reaches 0.05, or if any placebo cap (2021-10-01, 2022-01-01, 2022-03-01; unit and
date effects, firm clusters) reaches 0.05. Same functions as `gas_cap_pretrend.py`.

Writes outputs/tables/gas_cap_inmoney_pretrend.csv (results) and
outputs/tables/gas_cap_inmoney_monthly.csv (monthly means by country, all months to 2023-06).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_pretrend import PLACEBOS, PRE_END, did  # noqa: E402

PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
T = ROOT / "outputs" / "tables"
THR = 0.05


def load() -> pd.DataFrame:
    h = pd.read_parquet(PANEL, columns=["unit", "date", "period", "iberia", "zone", "firm", "cost", "price",
                                        "run20", "run50"])
    p = h.groupby(["zone", "date", "period"], as_index=False).price.first()
    p["date"] = p.date + pd.Timedelta(days=1)
    h = h.merge(p.rename(columns={"price": "price_lag"}), on=["zone", "date", "period"], how="left")
    h["firm"] = h.firm.fillna(h.unit)
    return h.dropna(subset=["cost", "run20"])


def trend(pre: pd.DataFrame, y: str) -> tuple[float, float]:
    wk = pre.assign(w=pre.date.dt.to_period("W")).groupby(["w", "iberia"])[f"{y}_u"].mean().unstack()
    gap = (wk[True] - wk[False]).dropna()
    t = np.arange(len(gap), dtype=float)
    X = np.column_stack([np.ones_like(t), t])
    b, *_ = np.linalg.lstsq(X, gap.to_numpy(), rcond=None)
    e = gap.to_numpy() - X @ b
    L, n = 4, len(e)
    S = sum((1 - l / (L + 1)) * (2 if l else 1) * (X[l:] * e[l:, None]).T @ (X[:n - l] * e[:n - l, None])
            for l in range(L + 1))
    S = (S + S.T) / 2
    A = np.linalg.inv(X.T @ X)
    return float(b[1] * 52), float(np.sqrt((A @ S @ A)[1, 1]) * 52)


def run(h: pd.DataFrame, label: str, y: str = "run20") -> tuple[list[dict], pd.DataFrame]:
    d = h.groupby(["unit", "date"], as_index=False).agg(m=(y, "mean"), iberia=("iberia", "first"),
                                                        firm=("firm", "first"))
    pre = d[d.date <= PRE_END].copy()
    pre[f"{y}_u"] = pre.m - pre.groupby("unit").m.transform("mean")
    tr, se = trend(pre, y)
    fail_t = abs(tr / se) > 1.96 and abs(tr) >= THR
    rows = [{"sample": label, "outcome": y, "test": "trend per year", "b": tr, "se": se, "fails": fail_t,
             "unit_days_pre": len(pre)}]
    for p in PLACEBOS:
        b, s = did(pre, (pre.iberia & (pre.date >= p)).to_numpy())
        rows.append({"sample": label, "outcome": y, "test": f"placebo {p}", "b": b, "se": s, "fails": abs(b) >= THR,
                     "unit_days_pre": len(pre)})
    mon = d.assign(ym=d.date.dt.strftime("%Y-%m")).groupby(["ym", "iberia"]).m.agg(["mean", "size"]).unstack()
    mon.columns = [f"{a}_{'iberia' if b else 'italy'}" for a, b in mon.columns]
    return rows, mon.assign(sample=label, outcome=y)


def main() -> int:
    h = load()
    samples = {"predicted in money, margin > 50": h[(h.price_lag - h.cost) > 50],
               "predicted in money, margin > 20": h[(h.price_lag - h.cost) > 20],
               "realised in money, margin > 50 (comparison only)": h[(h.price - h.cost) > 50],
               "all hours (step 1 second run)": h}
    res, mons = [], []
    for lab, s in samples.items():
        r, m = run(s, lab)
        res += r
        mons.append(m)
    r, m = run(samples["predicted in money, margin > 50"], "predicted in money, margin > 50", "run50")
    res += r
    mons.append(m)
    out = pd.DataFrame(res)
    out.to_csv(T / "gas_cap_inmoney_pretrend.csv", index=False)
    mon = pd.concat(mons)
    mon.to_csv(T / "gas_cap_inmoney_monthly.csv")
    with pd.option_context("display.width", 200, "display.max_rows", 200):
        print(out.round(4).to_string(index=False))
        main_m = mon[(mon["sample"] == "predicted in money, margin > 50") & (mon.outcome == "run20")]
        print("\nrun20, predicted in money (margin > 50), monthly mean and unit-days\n",
              main_m.drop(columns=["sample", "outcome"]).round(3).to_string())
    for lab in samples:
        f = out[(out["sample"] == lab) & (out.outcome == "run20")].fails.any()
        print(f"step 1 rule, run20, {lab}: {'FAILS' if f else 'PASSES'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
