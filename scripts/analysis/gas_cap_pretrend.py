#!/usr/bin/env python3
"""Step 1 of the gas-cap design: do Iberian and Italian gas plants' markups move together
before the cap? (docs/specs/2026-10-28-gas-cap-conduct-design.md §6)

    .venv/bin/python scripts/analysis/gas_cap_pretrend.py

Reads outputs/tables/gas_cap_offer_panel.parquet. Outcome: p50 (the price at half the unit's
own pre-cap capacity) minus its cost after the subsidy, averaged over the unit's hours in a
day. Pre-period 2021-06-15 -> 2022-06-14.

1. Monthly mean markup by country and the Iberia - Italy gap, with unit fixed effects
   (each unit's pre-period mean removed, so composition does not move the gap).
2. A linear trend in the weekly gap over the pre-period.
3. Placebo caps at 2021-10-01, 2022-01-01, 2022-03-01: unit + date fixed effects, Iberia x
   after-placebo, pre-period data only, standard errors clustered by firm.

`--outcome mic` (2026-10-28): for an Iberian unit-day that declares a minimum-income
condition, the reservation price is the higher of p50 and the condition's declared variable
term (`cab` `min_income_var_eur_mwh`; 999 means "never" and is dropped). Iberian combined
cycles often offer low and protect themselves through the condition, so p50 alone is not
their reservation price; Italian plants have no such condition and keep p50.

Stop rule (fixed before running): stop if the pre-period gap trends, or if a placebo effect
is as large as a fifth of the mean subsidy over the binding period.
"""
from __future__ import annotations

import argparse
import pyarrow.dataset as ds
import pyarrow.compute as pc
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
PANEL = ROOT / "outputs" / "tables" / "gas_cap_offer_panel.parquet"
PRE_END = pd.Timestamp("2022-06-14")
PLACEBOS = ["2021-10-01", "2022-01-01", "2022-03-01"]


def demean2(y: np.ndarray, a: np.ndarray, b: np.ndarray, it: int = 200) -> np.ndarray:
    r = y.astype(float).copy()
    for _ in range(it):
        r -= pd.Series(r).groupby(a).transform("mean").to_numpy()
        r -= pd.Series(r).groupby(b).transform("mean").to_numpy()
    return r


def did(d: pd.DataFrame, treat: np.ndarray) -> tuple[float, float]:
    ua, ub = pd.factorize(d.unit)[0], pd.factorize(d.date)[0]
    y = demean2(d.m.to_numpy(), ua, ub)
    x = demean2(treat.astype(float), ua, ub)
    beta = (x @ y) / (x @ x)
    e = y - beta * x
    g = pd.factorize(d.firm)[0]
    s = pd.Series(x * e).groupby(g).sum().to_numpy()
    G = len(s)
    se = np.sqrt((s @ s) / (x @ x) ** 2 * G / (G - 1))
    return beta, se


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--outcome", choices=["p50", "mic", "m25", "run10", "run20", "run50"], default="p50")
    a = ap.parse_args()
    h = pd.read_parquet(PANEL, columns=["unit", "date", "iberia", "firm", "p25", "p50", "cost", "subsidy",
                                        "run10", "run20", "run50"])
    ybar = h[h.subsidy > 0].drop_duplicates("date").subsidy.mean()
    if a.outcome.startswith("run") or a.outcome == "m25":
        # The two-part outcome (design §6, step 1 second run), thresholds fixed there.
        col = "p25" if a.outcome == "m25" else a.outcome
        h = h.dropna(subset=[col, "cost"])
        h["p50"] = h[col]
        if a.outcome == "m25":
            h["p50"] = h.p25
        else:
            h["cost"] = 0.0
    else:
        h = h.dropna(subset=["p50", "cost"])
    if a.outcome == "mic":
        units = sorted(h[h.iberia].unit.unique())
        cab = ds.dataset(ROOT / "data" / "omie" / "cab" / "parquet").to_table(
            filter=pc.field("unit").isin(units) & (pc.field("side") == "V"),
            columns=["date", "unit", "min_income_var_eur_mwh"]).to_pandas()
        cab["unit"] = cab.unit.astype(str)
        cab["date"] = pd.to_datetime(cab.date)
        v = cab.groupby(["unit", "date"]).min_income_var_eur_mwh.max().rename("mic_var")
        v = v.where((v > 0) & (v < 999))
        h = h.merge(v.reset_index(), on=["unit", "date"], how="left")
        share = h[h.iberia].mic_var.notna().mean()
        print(f"Iberian unit-hours with a declared variable term: {share:.1%}")
        h["p50"] = np.where(h.iberia & h.mic_var.notna(), np.fmax(h.p50, h.mic_var), h.p50)
    h["m"] = h.p50 - h.cost
    d = h.groupby(["unit", "date"], as_index=False).agg(m=("m", "mean"), iberia=("iberia", "first"),
                                                        firm=("firm", "first"))
    d["firm"] = d.firm.fillna(d.unit)
    pre = d[d.date <= PRE_END].copy()
    pre["m_u"] = pre.m - pre.groupby("unit").m.transform("mean")
    mon = pre.assign(ym=pre.date.dt.to_period("M")).groupby(["ym", "iberia"]).m_u.mean().unstack()
    mon.columns = ["Italy", "Iberia"]
    mon["gap"] = mon.Iberia - mon.Italy
    thr = 0.05 if a.outcome.startswith("run") else ybar / 5
    print(f"outcome {a.outcome}; mean subsidy over the binding period: {ybar:.1f} EUR/MWh; "
          f"stop threshold {thr:.3g}\n")
    print("pre-period, unit-demeaned outcome\n", mon.round(3 if a.outcome.startswith("run") else 1).to_string())
    wk = pre.assign(w=pre.date.dt.to_period("W")).groupby(["w", "iberia"]).m_u.mean().unstack()
    gap = (wk[True] - wk[False]).dropna()
    t = np.arange(len(gap), dtype=float)
    X = np.column_stack([np.ones_like(t), t])
    b, *_ = np.linalg.lstsq(X, gap.to_numpy(), rcond=None)
    e = gap.to_numpy() - X @ b
    # Newey-West, 4 lags, for the weekly trend
    L, n = 4, len(e)
    S = sum((1 - l / (L + 1)) * (2 if l else 1) * (X[l:] * e[l:, None]).T @ (X[:n - l] * e[:n - l, None])
            for l in range(L + 1)) / 1
    S = (S + S.T) / 2
    V = np.linalg.inv(X.T @ X) @ S @ np.linalg.inv(X.T @ X)
    se_t = np.sqrt(V[1, 1])
    trend_fail = abs(b[1] / se_t) > 1.96 and abs(b[1] * 52) >= thr
    print(f"\nweekly gap trend: {b[1]:.4g} per week (se {se_t:.3g}), {b[1] * 52:.3g} over a year; "
          f"{len(gap)} weeks{'  <-- FAILS' if trend_fail else ''}")
    print(f"\nplacebo caps (pre-period only, unit + date FE, firm clusters, {pre.firm.nunique()} firms):")
    for p in PLACEBOS:
        tr = (pre.iberia & (pre.date >= p)).to_numpy()
        bt, se = did(pre, tr)
        flag = "  <-- exceeds threshold" if abs(bt) >= thr else ""
        print(f"  {p}: {bt:+.3g} (se {se:.3g}){flag}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
