#!/usr/bin/env python3
"""Specification curve for B3's rho (notes/rq-crisis-quantity.md, G1a, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b3_curve.py

Grid: margin (20, 50, every hour; 100 is not constructible) x r (0..5) x gas controls (none, MIBGAS, both) x trend (no, yes) x window end
(2023-06-30, 2023-02-25). Point estimates of rho = 1 + b, plus the timing permutation p of each cell. The B1 ends are
recomputed for each margin. Writes outputs/tables/gas_cap_quantity_b3_curve.csv.
"""
from __future__ import annotations

import sys
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, ends, matrix, panel  # noqa: E402
from gas_cap_quantity_b3_checks import weekly_gas  # noqa: E402

T = ROOT / "outputs" / "tables"
MARGINS = [20.0, 50.0, None]  # EUR 100 dropped: no reference hours in the 8 weeks before the cap, so no ends
CONTROLS = {"none": [], "MIBGAS": [0], "both": [0, 1]}
ENDS = {"2023-06-30": pd.Timestamp("2023-06-30"), "2023-02-25": pd.Timestamp("2023-02-25")}


def slope(att, g, keep, X, trend):
    o = keep & ~np.isnan(att) & ~np.isnan(g)
    if X is not None:
        o &= ~np.isnan(X).any(axis=1)
    t = np.arange(len(att))[o].astype(float)
    Z = [np.ones(o.sum()), g[o]] + ([X[o]] if X is not None else []) + ([t - t.mean()] if trend else [])
    return float(np.linalg.lstsq(np.column_stack(Z), att[o], rcond=None)[0][1])


def main() -> int:
    rows = []
    for m in MARGINS:
        lab = "all" if m is None else int(m)
        h = panel(m)
        W, thr = matrix(h, "run20")
        meta = h.drop_duplicates("unit").set_index("unit")
        ib = meta.iberia.reindex(W.index).to_numpy()
        cols = W.columns
        M = W.to_numpy()
        pre = cols < CAP0
        e = ends(h)
        g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
        Xg = weekly_gas(cols)
        r_cv = int(np.argmin(xu_cv(M, ib, pre)))
        print(f"margin {lab}: {ib.sum()} Iberian, {(~ib).sum()} Italian units, missing threshold {thr}, CV r = {r_cv}", flush=True)
        for r in range(6):
            att = gsc(M, ib, pre, r)
            for (cn, cj), tr, (en, end) in product(CONTROLS.items(), (False, True), ENDS.items()):
                X = Xg[:, cj] if cj else None
                keep = ~pre & (cols <= end)
                b = slope(att, g, keep, X, tr)
                idx = np.flatnonzero(keep & ~np.isnan(g) & ~np.isnan(att))
                if X is not None:
                    idx = idx[~np.isnan(X[idx]).any(axis=1)]
                sh = []
                for k in range(1, len(idx)):
                    gs = np.full_like(g, np.nan)
                    gs[idx] = np.roll(g[idx], k)
                    sh.append(slope(att, gs, keep, X, tr))
                p = float((np.array(sh) <= b).mean()) if sh else np.nan
                rows.append({"margin": lab, "r": r, "r_cv": r == r_cv, "controls": cn, "trend": tr, "end": en,
                             "rho": 1 + b, "perm_p": p, "weeks": len(idx), "iberian": int(ib.sum())})
    R = pd.DataFrame(rows)
    R.to_csv(T / "gas_cap_quantity_b3_curve.csv", index=False)
    print(f"{len(R)} cells")
    q = R.rho.quantile([0, .25, .5, .75, 1])
    print(f"rho min {q[0]:.2f}, 25% {q[.25]:.2f}, median {q[.5]:.2f}, 75% {q[.75]:.2f}, max {q[1]:.2f}")
    print(f"inside [0.51, 1.03]: {R.rho.between(0.51, 1.03).mean():.0%}; permutation p <= 0.05: {(R.perm_p <= 0.05).mean():.0%}")
    for ax in ("margin", "r", "controls", "trend", "end"):
        s = R.groupby(ax).rho.agg(["median", lambda x: x.quantile(.25), lambda x: x.quantile(.75)])
        s.columns = ["median", "q25", "q75"]
        print(f"\nby {ax}:\n{s.round(2).to_string()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
