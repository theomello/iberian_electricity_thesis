#!/usr/bin/env python3
"""Step B3 of the crisis quantity design: the cap's pass-through as a dose-response against Italy
(notes/rq-crisis-quantity.md, B3, fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b3.py [--reps 199] [--all-hours]

ATT_w is the weekly Iberia - counterfactual gap from estimator B (Xu 2017, as in B2), g_w the full - none
difference of the B1 ends. Over every week from the cap's first to 2023-06-30:
    ATT_w = a + b * g_w           rho = 1 + b   (full pass-through b = 0, none b = -1)
The intercept absorbs a constant post-cap drift. Check (stop rule): with a linear time trend added, rho
outside the main 95% interval means the slope is time, not subsidy.

Writes outputs/tables/gas_cap_quantity_b3{,_allhours}.csv.
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
from gas_cap_quantity_b1 import CAP0, MARGIN, matrix, panel  # noqa: E402

T = ROOT / "outputs" / "tables"


def slope(att: np.ndarray, g: np.ndarray, post: np.ndarray, trend: bool) -> tuple[float, float]:
    """(a, b) of ATT_w on g_w over post weeks with both observed; a linear trend if asked."""
    o = post & ~np.isnan(att) & ~np.isnan(g)
    t = np.arange(len(att))[o].astype(float)
    Z = np.column_stack([np.ones(o.sum()), g[o]] + ([t - t.mean()] if trend else []))
    c = np.linalg.lstsq(Z, att[o], rcond=None)[0]
    return float(c[0]), float(c[1])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    ap.add_argument("--all-hours", action="store_true", help="every hour, ends from b1 --all-hours")
    a = ap.parse_args()
    sfx = "_allhours" if a.all_hours else ""
    rng = np.random.default_rng(20261102)
    h = panel(None if a.all_hours else MARGIN)
    W, thr = matrix(h, "run20")
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    firm = meta.firm.reindex(W.index).to_numpy()
    cols = W.columns
    M = W.to_numpy()
    pre = cols < CAP0
    post = ~pre
    e = pd.read_csv(T / f"gas_cap_quantity_b1_ends{sfx}.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()  # NaN where a week has no ends: dropped
    print(f"{'all hours' if a.all_hours else 'in-money hours'}: {ib.sum()} Iberian, {(~ib).sum()} Italian units x "
          f"{len(cols)} weeks; {int((post & ~np.isnan(g)).sum())} post-cap weeks with g_w, g max {np.nanmax(g):.3f}")
    r = int(np.argmin(xu_cv(M, ib, pre)))
    print(f"Xu CV -> r = {r}")
    print("\nsensitivity:  r | a | b | rho | rho with trend")
    rows = []
    for k in range(6):
        att = gsc(M, ib, pre, k)
        a0, b0 = slope(att, g, post, False)
        _, bt = slope(att, g, post, True)
        rows.append({"estimate": "sensitivity", "r": k, "a": a0, "b": b0, "rho": 1 + b0, "rho_trend": 1 + bt})
        print(f"  {k}{' *' if k == r else '  '} | {a0:+.3f} | {b0:+.3f} | {1 + b0:.2f} | {1 + bt:.2f}")
    att = gsc(M, ib, pre, r)
    a0, b0 = slope(att, g, post, False)
    _, bt = slope(att, g, post, True)
    fi = pd.Series(firm)
    groups = {c: fi[ib == c].unique() for c in (True, False)}
    draws = []
    for _ in range(a.reps):
        idx = np.concatenate([np.flatnonzero((fi.to_numpy() == f_) & (ib == c))
                              for c in (True, False)
                              for f_ in rng.choice(groups[c], size=len(groups[c]), replace=True)])
        at = gsc(M[idx], ib[idx], pre, r)
        draws.append([slope(at, g, post, False)[1], slope(at, g, post, True)[1]])
    dr = np.array(draws)
    lo, hi = np.nanpercentile(dr[:, 0], [2.5, 97.5])
    tlo, thi = np.nanpercentile(dr[:, 1], [2.5, 97.5])
    stop = not (1 + lo <= 1 + bt <= 1 + hi)
    print(f"\nmain, r = {r}, firm block bootstrap {a.reps} ({len(groups[True])} Iberian, {len(groups[False])} Italian firms):")
    print(f"  intercept a (constant drift)  {a0:+.3f}")
    print(f"  rho = 1 + b                   {1 + b0:.2f}  95% [{1 + lo:.2f}, {1 + hi:.2f}]")
    print(f"  rho with linear trend         {1 + bt:.2f}  95% [{1 + tlo:.2f}, {1 + thi:.2f}]  "
          f"{'<-- outside the main interval: STOP' if stop else '(inside the main interval: check holds)'}")
    rows.insert(0, {"estimate": "main", "r": r, "a": a0, "b": b0, "rho": 1 + b0, "rho_lo": 1 + lo, "rho_hi": 1 + hi,
                    "rho_trend": 1 + bt, "rho_trend_lo": 1 + tlo, "rho_trend_hi": 1 + thi, "stop": stop})
    pd.DataFrame(rows).to_csv(T / f"gas_cap_quantity_b3{sfx}.csv", index=False)
    print(f"\nB3 rule: {'STOP (slope is time, not subsidy)' if stop else 'check holds'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
