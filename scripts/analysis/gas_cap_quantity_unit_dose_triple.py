#!/usr/bin/env python3
"""Design K step 5: unweighted triple difference with Italy, gas x near-cost-mass term per country, reference curve
built 4 weeks before the date (notes/rq-crisis-quantity.md, "K step 5", rules fixed before running; the sixth
specification using Italy).

    .venv/bin/python scripts/analysis/gas_cap_quantity_unit_dose_triple.py [--reps 199]

Placebos first (2022-01-01, 2022-03-01); the real triple is read only if both placebo intervals include 0 and both
MDEs are <= 0.5. Writes outputs/tables/gas_cap_quantity_unit_dose_triple.csv.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_quantity_b1 import CAP0, END, RUN  # noqa: E402
from gas_cap_quantity_unit_dose import PLACEBOS, REF, F, curves, dose, long  # noqa: E402
from gas_cap_quantity_unit_dose_robust import build, ci, fe_ols, resample  # noqa: E402

T = ROOT / "outputs" / "tables"
GAP = pd.Timedelta(weeks=4)
HEADLINE = (0.48, 1.00)


def frames(B, D: pd.Timestamp, Spath: pd.Series, stop: pd.Timestamp, last_week: pd.Timestamp) -> dict:
    h, W, ib, firm, src, gas = B["h"], B["W"], B["ib"], B["firm"], B["src"], B["gas"]
    lo = D - GAP - REF
    cols = [w for w in W.columns if w <= last_week and not (w < D and w + pd.Timedelta(days=7) > lo)]
    out = {}
    for c in (True, False):
        hc = h[h.iberia == c]
        cur = curves(hc, *src[c], D - GAP)
        z = {u: float(F(v, RUN) - F(v, RUN - 100.0)) for (u, hod), v in cur.items() if hod is None}
        G = dose(hc, *src[c], D, Spath, stop, cur).unstack()
        x = long(W[ib == c], G, cols)
        x["firm"] = x.unit.map(firm)
        x["gz"] = x.w.map(gas[c]).to_numpy() * x.unit.map(z)
        out[c] = x.dropna(subset=["gz"]).reset_index(drop=True)
    return out


def estimate(L: dict, reps: int, rng) -> dict:
    b = {c: fe_ols(L[c], ["g", "gz"])[0] for c in (True, False)}
    dr = []
    for _ in range(reps):
        try:
            dr.append([fe_ols(resample(L[c], rng), ["g", "gz"])[0] for c in (True, False)])
        except (np.linalg.LinAlgError, ValueError):
            dr.append([np.nan, np.nan])
    dr = np.array(dr)
    tri = dr[:, 0] - dr[:, 1]
    return {"b_ib": b[True], "b_it": b[False], "b_tri": b[True] - b[False],
            "ib_ci": ci(dr[:, 0]), "it_ci": ci(dr[:, 1]), "tri_ci": ci(tri),
            "mde": 2.8 * np.nanstd(tri, ddof=1), "n_ib": len(L[True]), "n_it": len(L[False]),
            "units_ib": L[True].unit.nunique(), "units_it": L[False].unit.nunique()}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261108)
    B = build()
    S = B["S"]
    rows, ok = [], True
    stop = CAP0 - pd.Timedelta(days=1)
    last_pre = max(w for w in B["W"].columns if w + pd.Timedelta(days=6) < CAP0)
    for P in PLACEBOS:
        Sp = pd.Series(S.reindex(pd.date_range(CAP0, CAP0 + (stop - P))).fillna(0.0).to_numpy(),
                       index=pd.date_range(P, stop))
        r = estimate(frames(B, P, Sp, stop, last_pre), a.reps, rng)
        lo, hi = r["tri_ci"]
        flat, small = lo <= 0 <= hi, r["mde"] <= 0.5
        ok &= flat and small
        rows.append({"estimate": f"placebo {P.date()}", **{k: v for k, v in r.items() if not k.endswith("_ci")},
                     "tri_lo": lo, "tri_hi": hi, "ib_lo": r["ib_ci"][0], "ib_hi": r["ib_ci"][1],
                     "it_lo": r["it_ci"][0], "it_hi": r["it_ci"][1], "flat": flat, "mde_ok": small})
        print(f"placebo {P.date()}: Iberia b {r['b_ib']:+.3f} [{r['ib_ci'][0]:+.3f}, {r['ib_ci'][1]:+.3f}]; "
              f"Italy b {r['b_it']:+.3f} [{r['it_ci'][0]:+.3f}, {r['it_ci'][1]:+.3f}]; triple {r['b_tri']:+.3f} "
              f"[{lo:+.3f}, {hi:+.3f}], MDE {r['mde']:.3f}  ({r['units_ib']} / {r['units_it']} units)"
              f"{'' if flat else '  <-- excludes 0'}{'' if small else '  <-- MDE > 0.5'}")
    if not ok:
        verdict = "STOP at the placebos: triple difference not read"
    else:
        r = estimate(frames(B, CAP0, S, END, B["W"].columns.max()), a.reps, rng)
        lo, hi = r["tri_ci"]
        rows.append({"estimate": "real", **{k: v for k, v in r.items() if not k.endswith("_ci")},
                     "tri_lo": lo, "tri_hi": hi, "ib_lo": r["ib_ci"][0], "ib_hi": r["ib_ci"][1],
                     "it_lo": r["it_ci"][0], "it_hi": r["it_ci"][1],
                     "rho_triple": 1 + r["b_tri"], "rho_lo": 1 + lo, "rho_hi": 1 + hi})
        overlap = not (1 + hi < HEADLINE[0] or 1 + lo > HEADLINE[1])
        print(f"real: Iberia rho {1 + r['b_ib']:.3f} [{1 + r['ib_ci'][0]:.3f}, {1 + r['ib_ci'][1]:.3f}]; "
              f"Italy b (falsification) {r['b_it']:+.3f} [{r['it_ci'][0]:+.3f}, {r['it_ci'][1]:+.3f}]")
        print(f"      triple rho {1 + r['b_tri']:.3f} [{1 + lo:.3f}, {1 + hi:.3f}]")
        verdict = (f"placebos pass; triple rho {1 + r['b_tri']:.2f} [{1 + lo:.2f}, {1 + hi:.2f}], "
                   f"{'overlaps' if overlap else 'does NOT overlap'} the headline [0.48, 1.00] (check only)")
    pd.DataFrame(rows).to_csv(T / "gas_cap_quantity_unit_dose_triple.csv", index=False)
    print("\nRule:", verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
