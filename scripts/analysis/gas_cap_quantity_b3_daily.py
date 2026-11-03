#!/usr/bin/env python3
"""B3 on a unit x day panel with a daily dose (notes/rq-crisis-quantity.md, G2, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b3_daily.py [--reps 199]

Outcome: unit-day mean of run20 over predicted in-money hours (main margin). Dose g_d: mean over units of the day's full - none
gap (`ends(h, by="date")`). Xu (2017) `gsc`, pre = days before the cap, r by cross-validation; ATT_d = a + b g_d over post days,
rho = 1 + b. Firm block bootstrap, timing permutation (cyclic day shifts), linear trend, daily gas controls.
Writes outputs/tables/gas_cap_quantity_b3_daily.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "build"))
from build_italy_marginal_cost import psv_daily  # noqa: E402
from gas_cap_ife import gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, END, MIN_UNITS, WIN0, ends, panel  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402

T = ROOT / "outputs" / "tables"
WEEKLY = (0.51, 1.03)


def daily_matrix(h: pd.DataFrame) -> tuple[pd.DataFrame, float]:
    W = h.groupby(["unit", "date"]).run20.mean().unstack()
    W = W.reindex(columns=pd.date_range(WIN0, END, freq="D"))
    ib = h.drop_duplicates("unit").set_index("unit").iberia
    for thr in (0.30, 0.50):
        keep = W.isna().mean(axis=1) <= thr
        if ib.reindex(W.index[keep]).sum() >= MIN_UNITS:
            return W[keep], thr
    return W.iloc[0:0], float("nan")


def daily_gas(days: pd.DatetimeIndex) -> np.ndarray:
    m = pd.read_parquet(ROOT / "data" / "mibgas" / "mibgas_price_index_daily.parquet", columns=["date", "mibgas_es_eur_mwh"])
    m["date"] = pd.to_datetime(m.date)
    s = psv_daily()
    s["date"] = pd.to_datetime(s.date)
    d = m.merge(s, on="date").set_index("date")
    d["spread"] = d.psv_eur_mwh - d.mibgas_es_eur_mwh
    return d[["mibgas_es_eur_mwh", "spread"]].reindex(days).to_numpy()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261103)
    h = panel()
    W, thr = daily_matrix(h)
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    fi = pd.Series(meta.firm.reindex(W.index).to_numpy())
    days = W.columns
    M = W.to_numpy()
    pre = days < CAP0
    post = ~pre
    n_ib = int(ib.sum())
    print(f"daily panel: {n_ib} Iberian, {(~ib).sum()} Italian units x {len(days)} days (missing threshold {thr}); "
          f"{np.isnan(M).mean():.0%} of cells missing")
    if n_ib < MIN_UNITS:
        print("STOP: fewer than 25 Iberian units survive")
        return 1
    g = (lambda e: (e.full_run20 - e.none_run20).reindex(days).to_numpy())(ends(h, by="date"))
    print(f"{int((post & ~np.isnan(g)).sum())} post-cap days with g_d; g max {np.nanmax(g):.3f}, "
          f"days with g > 0: {int((g > 0).sum())}")
    r = int(np.argmin(xu_cv(M, ib, pre)))
    print(f"Xu CV -> r = {r}")
    att = gsc(M, ib, pre, r)
    b = slope(att, g, post, None, False)
    bt = slope(att, g, post, None, True)
    rho = 1 + b
    groups = {c: fi[ib == c].unique() for c in (True, False)}
    draws = []
    for _ in range(a.reps):
        idx = np.concatenate([np.flatnonzero((fi.to_numpy() == f_) & (ib == c))
                              for c in (True, False) for f_ in rng.choice(groups[c], size=len(groups[c]), replace=True)])
        at = gsc(M[idx], ib[idx], pre, r)
        draws.append([slope(at, g, post, None, False), slope(at, g, post, None, True)])
    dr = np.array(draws)
    lo, hi = np.nanpercentile(dr[:, 0], [2.5, 97.5])
    tlo, thi = np.nanpercentile(dr[:, 1], [2.5, 97.5])
    idx = np.flatnonzero(post & ~np.isnan(g) & ~np.isnan(att))
    sh = []
    for k in range(1, len(idx)):
        gs = np.full_like(g, np.nan)
        gs[idx] = np.roll(g[idx], k)
        sh.append(slope(att, gs, post, None, False))
    p = float((np.array(sh) <= b).mean())
    X = daily_gas(days)
    rg = {nm: 1 + slope(att, g, post, X[:, c], False) for nm, c in (("MIBGAS", [0]), ("spread", [1]), ("both", [0, 1]))}
    width = (1 + hi) - (1 + lo)
    inside_t = (1 + lo) <= (1 + bt) <= (1 + hi)
    print(f"\nrho = {rho:.2f}  95% [{1 + lo:.2f}, {1 + hi:.2f}] (width {width:.2f}; weekly {WEEKLY[0]}-{WEEKLY[1]}, width 0.52); "
          f"{len(groups[True])} Iberian, {len(groups[False])} Italian firms")
    print(f"permutation over {len(sh)} day shifts: shifted 5th pct {np.percentile(sh, 5):+.3f}, p {p:.3f} -> {'pass' if p <= 0.05 else 'FAIL'}")
    print(f"with trend: rho {1 + bt:.2f} [{1 + tlo:.2f}, {1 + thi:.2f}] -> {'inside' if inside_t else 'OUTSIDE'} the main interval")
    print("gas controls: " + ", ".join(f"{k} {v:.2f}" for k, v in rg.items()))
    sharper = p <= 0.05 and width < 0.52
    print(f"rule: daily dose {'sharpens' if sharper else 'does not sharpen'} the estimate (permutation "
          f"{'passes' if p <= 0.05 else 'fails'}, width {width:.2f} vs 0.52)")
    pd.DataFrame([{"r": r, "rho": rho, "rho_lo": 1 + lo, "rho_hi": 1 + hi, "width": width, "perm_p": p, "rho_trend": 1 + bt,
                   "rho_trend_lo": 1 + tlo, "rho_trend_hi": 1 + thi, "rho_mibgas": rg["MIBGAS"], "rho_spread": rg["spread"],
                   "rho_both": rg["both"], "iberian_units": n_ib, "days": int(len(idx)), "sharper": sharper}]
                 ).to_csv(T / "gas_cap_quantity_b3_daily.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
