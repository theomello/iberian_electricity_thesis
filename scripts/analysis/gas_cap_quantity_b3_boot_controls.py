#!/usr/bin/env python3
"""Firm-block bootstrap of B3 with and without gas-price controls (notes/rq-crisis-quantity.md, H6, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b3_boot_controls.py [--reps 199]

Same draws for three versions of the slope regression (no control, MIBGAS, MIBGAS + PSV - MIBGAS) and for their contrast.
Writes outputs/tables/gas_cap_quantity_b3_boot_controls.csv.
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
from gas_cap_quantity_b1 import CAP0, matrix, panel  # noqa: E402
from gas_cap_quantity_b3_checks import weekly_gas  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402

T = ROOT / "outputs" / "tables"
VERSIONS = {"none": None, "MIBGAS": [0], "both": [0, 1]}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261102)  # B3's seed
    h = panel()
    W, _ = matrix(h, "run20")
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    fi = pd.Series(meta.firm.reindex(W.index).to_numpy())
    cols = W.columns
    M = W.to_numpy()
    pre = cols < CAP0
    post = ~pre
    e = pd.read_csv(T / "gas_cap_quantity_b1_ends.csv", parse_dates=["w"]).set_index("w")
    g = (e.full_run20 - e.none_run20).reindex(cols).to_numpy()
    Xg = weekly_gas(cols)
    r = int(np.argmin(xu_cv(M, ib, pre)))

    def est(att):
        return {k: 1 + slope(att, g, post, None if c is None else Xg[:, c], False) for k, c in VERSIONS.items()}

    point = est(gsc(M, ib, pre, r))
    groups = {c: fi[ib == c].unique() for c in (True, False)}
    draws = []
    for _ in range(a.reps):
        idx = np.concatenate([np.flatnonzero((fi.to_numpy() == f_) & (ib == c))
                              for c in (True, False) for f_ in rng.choice(groups[c], size=len(groups[c]), replace=True)])
        draws.append(est(gsc(M[idx], ib[idx], pre, r)))
    D = pd.DataFrame(draws)
    D["d"] = D["none"] - D["both"]
    print(f"r = {r}; {len(D)} draws; {len(groups[True])} Iberian, {len(groups[False])} Italian firms")
    rows = []
    for k in list(VERSIONS) + ["d"]:
        lo, hi = np.nanpercentile(D[k], [2.5, 97.5])
        pt = point[k] if k in point else point["none"] - point["both"]
        rows.append({"version": k, "point": pt, "mean": D[k].mean(), "lo": lo, "hi": hi, "width": hi - lo, "sd": D[k].std()})
        print(f"  {k:<7} point {pt:+.3f}  mean {D[k].mean():+.3f}  95% [{lo:+.3f}, {hi:+.3f}]  width {hi - lo:.3f}")
    R = pd.DataFrame(rows)
    print(f"width ratio, both / none: {R.width[2] / R.width[0]:.2f}; MIBGAS / none: {R.width[1] / R.width[0]:.2f}")
    d = R[R.version == "d"].iloc[0]
    verdict = ("gas response detectable (d above 0)" if d.lo > 0 else "gas response detectable (d below 0)" if d.hi < 0
               else "not detectable: quote both")
    print(f"rule: {verdict}")
    R["verdict"] = verdict
    R.to_csv(T / "gas_cap_quantity_b3_boot_controls.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
