#!/usr/bin/env python3
"""What the factors do in B3's weekly run20 matrices (descriptive; notes/rq-crisis-quantity.md, H1).

    .venv/bin/python scripts/analysis/gas_cap_quantity_factors.py

For the in-money main sample and the every-hour sample: Bai & Ng's IC_p2 on the Italian matrix, Xu's cross-validation error by r,
the share of the Italian two-way residual variance each factor carries, the correlation of the first factors with the dose g_w
and with the weekly gas price, the Iberian pre-cap R^2 by r, the mean gap after the subsidy ends, and B3's rho by r.
Writes outputs/tables/gas_cap_quantity_factors.csv.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import em_factor, gsc, ic_p2, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, MARGIN, matrix, panel  # noqa: E402
from gas_cap_quantity_b3_checks import weekly_gas  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402

T = ROOT / "outputs" / "tables"
AFTER = pd.Timestamp("2023-02-25")


def one(name: str, all_hours: bool) -> list[dict]:
    sfx = "_allhours" if all_hours else ""
    h = panel(None if all_hours else MARGIN)
    W, thr = matrix(h, "run20")
    ib = h.drop_duplicates("unit").set_index("unit").iberia.reindex(W.index).to_numpy()
    cols = W.columns
    M = W.to_numpy()
    pre = cols < CAP0
    e = pd.read_csv(T / f"gas_cap_quantity_b1_ends{sfx}.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
    X = weekly_gas(cols)
    psv = X[:, 0] + X[:, 1]
    IT = M[~ib]
    print(f"\n=== {name}: {ib.sum()} Iberian, {(~ib).sum()} Italian units x {len(cols)} weeks ({pre.sum()} pre-cap); "
          f"{np.isnan(M).mean():.0%} missing")
    k_ic, ics = ic_p2(IT)
    print(f"Bai-Ng IC_p2 on the Italian matrix: k = {k_ic}; IC by k = " + ", ".join(f"{v:.3f}" for v in ics))
    cv = xu_cv(M[:, cols < CAP0 if False else slice(None)], ib, pre)
    print("Xu CV mean squared error by r: " + ", ".join(f"{v:.5f}" for v in cv) + f"  (best r = {int(np.argmin(cv))})")
    a, b, LF = em_factor(IT, 8)
    R = np.where(np.isnan(IT), a + b + LF, IT)
    E = R - R.mean(axis=1, keepdims=True)
    E = E - E.mean(axis=0, keepdims=True)
    U, s, Vt = np.linalg.svd(E, full_matrices=False)
    share = s ** 2 / (s ** 2).sum()
    print("share of Italian two-way residual variance, factors 1-6: " + ", ".join(f"{v:.1%}" for v in share[:6]))
    gf = np.where(np.isnan(g), 0.0, g)
    gf = np.where(pre, 0.0, gf)
    for j in range(4):
        f = Vt[j]
        print(f"  factor {j + 1}: corr with dose {np.corrcoef(f, gf)[0, 1]:+.2f}, with MIBGAS "
              f"{pd.Series(f).corr(pd.Series(X[:, 0])):+.2f}, with PSV {pd.Series(f).corr(pd.Series(psv)):+.2f}")
    rows = []
    for r in range(6):
        a_, b_, LF_ = em_factor(IT, r)
        F = (np.linalg.svd(LF_, full_matrices=False)[2][:r].T * np.sqrt(M.shape[1])) if r else np.zeros((M.shape[1], 0))
        xi = b_.ravel()
        r2 = []
        for y in M[ib]:
            o = ~np.isnan(y) & pre
            Z = np.column_stack([np.ones(o.sum()), F[o]])
            c = np.linalg.lstsq(Z, y[o] - xi[o], rcond=None)[0]
            res = y[o] - xi[o] - Z @ c
            r2.append(1 - (res ** 2).sum() / ((y[o] - y[o].mean()) ** 2).sum())
        att = gsc(M, ib, pre, r)
        after = float(np.nanmean(att[cols > AFTER]))
        bb = slope(att, g, ~pre, None, False)
        rows.append({"sample": name, "r": r, "ic_k": k_ic, "cv_mse": cv[r], "iberian_pre_r2": float(np.mean(r2)),
                     "mean_gap_after_subsidy": after, "rho": 1 + bb})
    D = pd.DataFrame(rows)
    print(D.drop(columns=["sample", "ic_k"]).round(4).to_string(index=False))
    return rows


def main() -> int:
    rows = one("in-money (margin 50)", False) + one("every hour", True)
    pd.DataFrame(rows).to_csv(T / "gas_cap_quantity_factors.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
