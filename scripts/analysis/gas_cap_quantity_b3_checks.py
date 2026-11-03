#!/usr/bin/env python3
"""Checks on B3, the cap's pass-through as a dose-response against Italy (notes/rq-crisis-quantity.md,
"B3 checks", rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b3_checks.py [--all-hours]

At B3's r and ATT_w:
1. timing permutation: g_w shifted cyclically by k = 1 .. n-1 within the post-cap weeks carrying g_w;
   pass if the real b is at or below the 5th percentile of the shifted b's;
2. leave one episode out (December 2022; October-November 2022); pass if rho stays inside B3's interval;
3. gas price controls (weekly mean MIBGAS, weekly mean PSV - MIBGAS); pass if rho stays inside.

Writes outputs/tables/gas_cap_quantity_b3_checks{,_allhours}.csv.
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
from gas_cap_ife import gsc  # noqa: E402
from gas_cap_quantity_b1 import CAP0, MARGIN, matrix, panel  # noqa: E402

T = ROOT / "outputs" / "tables"


def fit(att: np.ndarray, g: np.ndarray, keep: np.ndarray, X: np.ndarray | None = None) -> float:
    """b of ATT_w on g_w (and controls X) over weeks in `keep` with everything observed."""
    o = keep & ~np.isnan(att) & ~np.isnan(g)
    if X is not None:
        o &= ~np.isnan(X).any(axis=1)
    Z = np.column_stack([np.ones(o.sum()), g[o]] + ([X[o]] if X is not None else []))
    return float(np.linalg.lstsq(Z, att[o], rcond=None)[0][1])


def weekly_gas(cols: pd.DatetimeIndex) -> np.ndarray:
    m = pd.read_parquet(ROOT / "data" / "mibgas" / "mibgas_price_index_daily.parquet", columns=["date", "mibgas_es_eur_mwh"])
    m["date"] = pd.to_datetime(m.date)
    s = psv_daily()
    s["date"] = pd.to_datetime(s.date)
    d = m.merge(s, on="date", how="inner")
    d["w"] = pd.to_datetime(d.date).dt.to_period("W").dt.start_time
    w = d.groupby("w").agg(mibgas=("mibgas_es_eur_mwh", "mean"), psv=("psv_eur_mwh", "mean"))
    w["spread"] = w.psv - w.mibgas
    return w[["mibgas", "spread"]].reindex(cols).to_numpy()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all-hours", action="store_true")
    a = ap.parse_args()
    sfx = "_allhours" if a.all_hours else ""
    b3 = pd.read_csv(T / f"gas_cap_quantity_b3{sfx}.csv")
    main_row = b3[b3.estimate == "main"].iloc[0]
    r, lo, hi, rho0 = int(main_row.r), main_row.rho_lo, main_row.rho_hi, main_row.rho
    h = panel(None if a.all_hours else MARGIN)
    W, _ = matrix(h, "run20")
    ib = h.drop_duplicates("unit").set_index("unit").iberia.reindex(W.index).to_numpy()
    cols = W.columns
    pre = cols < CAP0
    post = ~pre
    e = pd.read_csv(T / f"gas_cap_quantity_b1_ends{sfx}.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
    att = gsc(W.to_numpy(), ib, pre, r)
    b_real = fit(att, g, post)
    assert abs(1 + b_real - rho0) < 1e-9, "must reproduce B3's main rho"
    print(f"{'all hours' if a.all_hours else 'in-money'}: r = {r}, B3 rho {rho0:.2f} [{lo:.2f}, {hi:.2f}]")
    rows = []

    # 1. timing permutation
    idx = np.flatnonzero(post & ~np.isnan(g) & ~np.isnan(att))
    n = len(idx)
    shifted = []
    for k in range(1, n):
        gs = np.full_like(g, np.nan)
        gs[idx] = np.roll(g[idx], k)
        shifted.append(fit(att, gs, post))
    shifted = np.array(shifted)
    p = float((shifted <= b_real).mean())
    q05 = float(np.percentile(shifted, 5))
    ok1 = p <= 0.05
    print(f"\n1. timing permutation, {n - 1} shifts: real b {b_real:+.3f}, shifted 5th pct {q05:+.3f}, "
          f"median {np.median(shifted):+.3f}; one-sided p {p:.3f} -> {'pass' if ok1 else 'FAIL'}")
    rows.append({"check": "timing permutation", "value": b_real, "p": p, "q05": q05, "n": n - 1, "pass": ok1})

    # 2. leave one episode out
    ym = cols.strftime("%Y-%m")
    for lab, months in (("without December 2022", ["2022-12"]), ("without October-November 2022", ["2022-10", "2022-11"])):
        rho = 1 + fit(att, g, post & ~ym.isin(months))
        ok = lo <= rho <= hi
        print(f"2. {lab:<32} rho {rho:.2f} -> {'pass' if ok else 'FAIL'}")
        rows.append({"check": lab, "value": rho, "pass": ok})

    # 3. gas price controls
    X = weekly_gas(cols)
    for lab, Xc in (("MIBGAS", X[:, :1]), ("PSV - MIBGAS", X[:, 1:]), ("both", X)):
        rho = 1 + fit(att, g, post, Xc)
        ok = lo <= rho <= hi
        print(f"3. control {lab:<14} rho {rho:.2f} -> {'pass' if ok else 'FAIL'}")
        rows.append({"check": f"control {lab}", "value": rho, "pass": ok})
    gate = ok1 and all(x["pass"] for x in rows[1:3]) and rows[-1]["pass"]
    pd.DataFrame(rows).to_csv(T / f"gas_cap_quantity_b3_checks{sfx}.csv", index=False)
    print(f"\nB3 checks (decisive: 1, both of 2, 3 with both controls): {'ALL PASS' if gate else 'FAIL'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
