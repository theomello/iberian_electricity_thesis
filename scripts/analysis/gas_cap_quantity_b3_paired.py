#!/usr/bin/env python3
"""Paired test of B3's offer rho against the declared-cost rho (notes/rq-crisis-quantity.md, G1b, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b3_paired.py [--reps 199]

One firm block bootstrap (within country, as B3). In each draw: rho_offer = 1 + b of B3 (r by CV, no controls, ATT re-estimated
on the draw, g_w fixed) and rho_decl = median `rho_bid` (gas_cap_declared_cost.panel(), S >= 20) of the drawn Iberian firms'
unit-days 2022-06-15 -> 2023-02-25. d = rho_decl - rho_offer. Writes outputs/tables/gas_cap_quantity_b3_paired.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_declared_cost import panel as decl_panel  # noqa: E402
from gas_cap_ife import gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, matrix, panel  # noqa: E402
from gas_cap_quantity_b3 import slope  # noqa: E402

T = ROOT / "outputs" / "tables"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261103)
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
    r = int(np.argmin(xu_cv(M, ib, pre)))
    d = decl_panel()
    d = d[d.date.between(CAP0, "2023-02-25") & d.rho_bid.notna()]
    by_firm = {f: x.rho_bid.to_numpy() for f, x in d.groupby("firm")}
    groups = {c: fi[ib == c].unique() for c in (True, False)}
    off0 = 1 + slope(gsc(M, ib, pre, r), g, post, False)[1]
    dec0 = float(np.median(np.concatenate([by_firm[f] for f in groups[True] if f in by_firm])))
    print(f"r = {r}; offer rho {off0:.2f}; declared rho {dec0:.2f} ({sum(f in by_firm for f in groups[True])} of "
          f"{len(groups[True])} Iberian firms declare); d = {dec0 - off0:+.2f}")
    rows = []
    for _ in range(a.reps):
        draw = {c: rng.choice(groups[c], size=len(groups[c]), replace=True) for c in (True, False)}
        idx = np.concatenate([np.flatnonzero((fi.to_numpy() == f_) & (ib == c)) for c in (True, False) for f_ in draw[c]])
        off = 1 + slope(gsc(M[idx], ib[idx], pre, r), g, post, False)[1]
        v = [by_firm[f] for f in draw[True] if f in by_firm]
        if not v:
            continue
        rows.append({"rho_offer": off, "rho_decl": float(np.median(np.concatenate(v)))})
    D = pd.DataFrame(rows)
    D["d"] = D.rho_decl - D.rho_offer
    lo, hi = np.nanpercentile(D.d, [2.5, 97.5])
    olo, ohi = np.nanpercentile(D.rho_offer, [2.5, 97.5])
    dlo, dhi = np.nanpercentile(D.rho_decl, [2.5, 97.5])
    print(f"{len(D)} draws: offer rho 95% [{olo:.2f}, {ohi:.2f}]; declared rho 95% [{dlo:.2f}, {dhi:.2f}]; "
          f"corr(offer, declared) {D.rho_offer.corr(D.rho_decl):+.2f}")
    print(f"d = declared - offer: point {dec0 - off0:+.2f}, mean {D.d.mean():+.2f}, 95% [{lo:+.2f}, {hi:+.2f}]; share d > 0 {np.mean(D.d > 0):.0%}")
    verdict = ("offers pass through less than declared costs" if lo > 0 else
               "offers pass through more than declared costs" if hi < 0 else "no difference detectable")
    print(f"rule: {verdict}")
    pd.DataFrame([{"r": r, "rho_offer": off0, "rho_decl": dec0, "d": dec0 - off0, "d_mean": D.d.mean(), "d_lo": lo, "d_hi": hi,
                   "share_d_pos": float(np.mean(D.d > 0)), "corr": D.rho_offer.corr(D.rho_decl), "draws": len(D),
                   "verdict": verdict}]).to_csv(T / "gas_cap_quantity_b3_paired.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
