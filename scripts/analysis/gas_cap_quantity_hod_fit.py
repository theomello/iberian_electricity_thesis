#!/usr/bin/env python3
"""Stage 1 of the hour-of-day counterfactual: pre-cap fit by block (notes/rq-crisis-quantity.md, H7, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_hod_fit.py

Four six-hour blocks of the delivery hour; per block the weekly run20 matrix of the in-money main sample, the Italian week effect and factors of that block,
the Iberian pre-cap R^2 of the counterfactual and Xu's cross-validation error for r = 0..5, beside the pooled baseline. Estimates no rho.
Writes outputs/tables/gas_cap_quantity_hod_fit.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import em_factor, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, MIN_UNITS, matrix, panel  # noqa: E402

T = ROOT / "outputs" / "tables"
BLOCKS = {"1-6": (1, 6), "7-12": (7, 12), "13-18": (13, 18), "19-24": (19, 24)}


def fit_table(h: pd.DataFrame, label: str) -> list[dict]:
    W, thr = matrix(h, "run20")
    if len(W) == 0:
        print(f"{label}: dropped (fewer than {MIN_UNITS} Iberian units)")
        return []
    ib = h.drop_duplicates("unit").set_index("unit").iberia.reindex(W.index).to_numpy()
    cols = W.columns
    M = W.to_numpy()
    pre = cols < CAP0
    IT = M[~ib]
    cv = xu_cv(M, ib, pre)
    print(f"\n{label}: {ib.sum()} Iberian, {(~ib).sum()} Italian units, missing threshold {thr}; CV best r = {int(np.argmin(cv))}")
    rows = []
    for r in range(6):
        a, b, LF = em_factor(IT, r)
        F = (np.linalg.svd(LF, full_matrices=False)[2][:r].T * np.sqrt(M.shape[1])) if r else np.zeros((M.shape[1], 0))
        xi = b.ravel()
        r2 = []
        for y in M[ib]:
            o = ~np.isnan(y) & pre
            Z = np.column_stack([np.ones(o.sum()), F[o]])
            c = np.linalg.lstsq(Z, y[o] - xi[o], rcond=None)[0]
            res = y[o] - xi[o] - Z @ c
            r2.append(1 - (res ** 2).sum() / ((y[o] - y[o].mean()) ** 2).sum())
        rows.append({"block": label, "r": r, "iberian": int(ib.sum()), "italian": int((~ib).sum()), "cv_mse": cv[r],
                     "iberian_pre_r2": float(np.mean(r2))})
    D = pd.DataFrame(rows)
    print(D[["r", "cv_mse", "iberian_pre_r2"]].round(4).to_string(index=False))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all-hours", action="store_true", help="every hour, not predicted in-money hours (an addition to H7, diagnostic only)")
    a = ap.parse_args()
    sfx = "_allhours" if a.all_hours else ""
    h = panel(None if a.all_hours else 50.0)
    h["hod"] = h.period.clip(upper=24)
    rows = fit_table(h, "pooled (baseline)")
    for name, (lo, hi) in BLOCKS.items():
        rows += fit_table(h[h.hod.between(lo, hi)], name)
    D = pd.DataFrame(rows)
    D.to_csv(T / f"gas_cap_quantity_hod_fit{sfx}.csv", index=False)
    base = D[(D.block == "pooled (baseline)") & (D.r == 0)].iberian_pre_r2.iloc[0]
    blk = D[(D.block != "pooled (baseline)") & (D.r == 0)]
    med = blk.iberian_pre_r2.median()
    better = int((blk.iberian_pre_r2 > base).sum())
    go = (med - base >= 0.15) and better >= 3
    print(f"\nr = 0 pre-cap R^2: pooled {base:+.3f}; blocks " + ", ".join(f"{b} {v:+.3f}" for b, v in zip(blk.block, blk.iberian_pre_r2)))
    print(f"median across {len(blk)} blocks {med:+.3f} (improvement {med - base:+.3f}); {better} of {len(blk)} blocks improve")
    print(f"rule: {'GO to stage 2' if go else 'STOP: hour-of-day matching does not improve the pre-cap tracking'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
