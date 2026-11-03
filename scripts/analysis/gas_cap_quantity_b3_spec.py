#!/usr/bin/env python3
"""Which gas-control set to quote for B3 (notes/rq-crisis-quantity.md, E2, fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b3_spec.py [--reps 199]

(a) Placebo. Before the cap there is no subsidy. Treat Iberia as capped from 2022-01-01 and from 2022-03-01
    (Xu 2017, `gas_cap_ife.gsc`, r by cross-validation as in B1 and also r = 0) and take the out-of-sample weekly
    gap up to 2022-06-14. Regress it on the weekly MIBGAS price and on the PSV - MIBGAS spread. Firm block
    bootstrap, ATT re-estimated each draw. Rule: controls justified if the 95% interval of the MIBGAS slope
    excludes zero with the same sign at both placebo dates; not justified if it includes zero at both; mixed
    otherwise.
(b) The timing permutation of B3's slope under both controls (cyclic shifts of g_w), pass if p <= 0.05.

Writes outputs/tables/gas_cap_quantity_b3_spec.csv.
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
from gas_cap_quantity_b1 import CAP0, PLACEBOS, matrix, panel  # noqa: E402
from gas_cap_quantity_b3_checks import fit, weekly_gas  # noqa: E402

T = ROOT / "outputs" / "tables"


def ols(y: np.ndarray, X: np.ndarray) -> np.ndarray:
    o = ~np.isnan(y) & ~np.isnan(X).any(axis=1)
    Z = np.column_stack([np.ones(o.sum()), X[o]])
    return np.linalg.lstsq(Z, y[o], rcond=None)[0][1:]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261103)
    h = panel()
    W, _ = matrix(h, "run20")
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    firm = pd.Series(meta.firm.reindex(W.index).to_numpy())
    cols = W.columns
    M = W.to_numpy()
    X = weekly_gas(cols)
    groups = {k: firm[ib == k].unique() for k in (True, False)}
    rows = []
    print("(a) placebo: out-of-sample weekly gap on the gas controls (slope per EUR/MWh; spread in the same units)")
    for p in PLACEBOS:
        pre = cols < p
        out = (cols >= p) & (cols < CAP0)
        r_cv = int(np.argmin(xu_cv(M[:, cols < CAP0], ib, pre[cols < CAP0])))
        for lab, r in (("CV", r_cv), ("r=0", 0)):
            att = gsc(M, ib, pre, r)
            b = ols(att[out], X[out])
            draws = []
            for _ in range(a.reps):
                idx = np.concatenate([np.flatnonzero((firm.to_numpy() == f_) & (ib == c))
                                      for c in (True, False) for f_ in rng.choice(groups[c], size=len(groups[c]), replace=True)])
                at = gsc(M[idx], ib[idx], pre, r)
                draws.append(ols(at[out], X[out]))
            dr = np.array(draws)
            lo, hi = np.nanpercentile(dr, [2.5, 97.5], axis=0)
            for j, nm in enumerate(("MIBGAS", "spread")):
                rows.append({"test": "placebo", "placebo": p.date(), "r": lab + f" ({r})", "regressor": nm,
                             "slope": b[j], "lo": lo[j], "hi": hi[j], "excludes_zero": bool(lo[j] > 0 or hi[j] < 0),
                             "weeks": int(out.sum())})
                print(f"  placebo {p.date()} {lab} r={r}: {nm:<6} slope {b[j]:+.4f} [{lo[j]:+.4f}, {hi[j]:+.4f}] "
                      f"{'excludes 0' if lo[j] > 0 or hi[j] < 0 else 'includes 0'} ({int(out.sum())} weeks)")
    pr = pd.DataFrame(rows)
    m = pr[(pr.regressor == "MIBGAS") & pr.r.str.startswith("CV")]
    both_excl = m.excludes_zero.all() and (np.sign(m.slope).nunique() == 1)
    neither = (~m.excludes_zero).all()
    verdict = "controls justified" if both_excl else ("controls not justified" if neither else "mixed")
    print(f"\nrule, MIBGAS slope at both placebos (CV r): {verdict}")

    # (b) permutation of B3's slope under both controls
    pre = cols < CAP0
    post = ~pre
    e = pd.read_csv(T / "gas_cap_quantity_b1_ends.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
    att = gsc(M, ib, pre, 0)
    b_real = fit(att, g, post, X)
    idx = np.flatnonzero(post & ~np.isnan(g) & ~np.isnan(att))
    sh = []
    for k in range(1, len(idx)):
        gs = np.full_like(g, np.nan)
        gs[idx] = np.roll(g[idx], k)
        sh.append(fit(att, gs, post, X))
    sh = np.array(sh)
    pval = float((sh <= b_real).mean())
    print(f"(b) timing permutation under both controls: real b {b_real:+.3f} (rho {1 + b_real:.2f}); shifted 5th pct "
          f"{np.percentile(sh, 5):+.3f}; p {pval:.3f} -> {'pass' if pval <= 0.05 else 'FAIL'}")
    rows.append({"test": "permutation_both_controls", "slope": b_real, "lo": float(np.percentile(sh, 5)), "hi": np.nan,
                 "excludes_zero": pval <= 0.05, "weeks": len(idx), "r": "0", "regressor": "g_w"})
    pd.DataFrame(rows).to_csv(T / "gas_cap_quantity_b3_spec.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
