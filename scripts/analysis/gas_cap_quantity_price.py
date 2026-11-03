#!/usr/bin/env python3
"""B3-style slope on the offer price in euros per euro of subsidy (notes/rq-crisis-quantity.md, I4, rules fixed before running).

    .venv/bin/python scripts/analysis/gas_cap_quantity_price.py [--reps 199]

y = min(p, 1000) - cost_gross, weekly unit median over predicted in-money hours; ATT_w by Xu (2017) gsc; ATT_w = a + c * S_w over the post-cap weeks,
rho = -c. Timing permutation, linear trend, MIBGAS control, firm-block bootstrap. Writes outputs/tables/gas_cap_quantity_price.csv.
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
from gas_cap_quantity_b1 import CAP0, END, MARGIN, MIN_UNITS, PANEL, WIN0  # noqa: E402
from gas_cap_quantity_b3_checks import weekly_gas  # noqa: E402
from gas_cap_quantity_b3_curve import slope  # noqa: E402

T = ROOT / "outputs" / "tables"
CAPP = 1000.0


def load() -> pd.DataFrame:
    h = pd.read_parquet(PANEL, columns=["unit", "date", "period", "iberia", "zone", "firm", "cost", "cost_gross", "subsidy", "price", "p50",
                                        "p_mid", "essential"])
    p = h.groupby(["zone", "date", "period"], as_index=False).price.first()
    p["date"] = p.date + pd.Timedelta(days=1)
    h = h.merge(p.rename(columns={"price": "price_lag"}), on=["zone", "date", "period"], how="left")
    h["firm"] = h.firm.fillna(h.unit)
    h = h[~h.essential & h.cost.notna() & ((h.price_lag - h.cost) > MARGIN) & h.date.between(WIN0, END)].copy()
    h["w"] = h.date.dt.to_period("W").dt.start_time
    h["y50"] = np.minimum(h.p50, CAPP) - h.cost_gross
    h["ymid"] = np.minimum(h.p_mid, CAPP) - h.cost_gross
    return h


def build(h: pd.DataFrame, y: str):
    W = h.groupby(["unit", "w"])[y].median().unstack()
    W = W.reindex(columns=pd.date_range(WIN0.to_period("W").start_time, END, freq="W-MON"))
    ibs = h.drop_duplicates("unit").set_index("unit").iberia
    for thr in (0.30, 0.50):
        keep = W.isna().mean(axis=1) <= thr
        if ibs.reindex(W.index[keep]).sum() >= MIN_UNITS:
            W = W[keep]
            break
    else:
        return None
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    fi = pd.Series(meta.firm.reindex(W.index).to_numpy())
    S = h[h.iberia].groupby("w").subsidy.mean().reindex(W.columns).fillna(0.0).to_numpy()
    return W.to_numpy(), ib, fi, W.columns, S


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261103)
    h = load()
    rows = []
    for y in ("y50", "ymid"):
        out = build(h, y)
        if out is None:
            print(f"{y}: fewer than {MIN_UNITS} Iberian units, STOP")
            continue
        M, ib, fi, cols, S = out
        pre = cols < CAP0
        post = ~pre
        r = int(np.argmin(xu_cv(M, ib, pre)))
        att = gsc(M, ib, pre, r)
        c = slope(att, S, post, None, False)
        ct = slope(att, S, post, None, True)
        groups = {k: fi[ib == k].unique() for k in (True, False)}
        dr = []
        for _ in range(a.reps):
            idx = np.concatenate([np.flatnonzero((fi.to_numpy() == f_) & (ib == k)) for k in (True, False)
                                  for f_ in rng.choice(groups[k], size=len(groups[k]), replace=True)])
            at = gsc(M[idx], ib[idx], pre, r)
            dr.append([slope(at, S, post, None, False), slope(at, S, post, None, True)])
        dr = np.array(dr)
        lo, hi = np.nanpercentile(-dr[:, 0], [2.5, 97.5])
        tlo, thi = np.nanpercentile(-dr[:, 1], [2.5, 97.5])
        idx = np.flatnonzero(post & ~np.isnan(att) & (S >= 0))
        sh = []
        for k in range(1, len(idx)):
            Ss = np.zeros_like(S)
            Ss[idx] = np.roll(S[idx], k)
            sh.append(slope(att, Ss, post, None, False))
        p = float((np.array(sh) <= c).mean())
        Xg = weekly_gas(cols)
        cm = slope(att, S, post, Xg[:, :1], False)
        inside = lo <= -ct <= hi
        gate = (p <= 0.05) and inside
        print(f"\n{y}: {ib.sum()} Iberian, {(~ib).sum()} Italian units x {len(cols)} weeks, r = {r}")
        print(f"  c = {c:+.3f} euros of offer per euro of subsidy -> rho = {-c:.2f}  95% [{lo:.2f}, {hi:.2f}]")
        print(f"  permutation ({len(sh)} shifts): shifted 5th pct {np.percentile(sh, 5):+.3f}, p {p:.3f} -> {'pass' if p <= 0.05 else 'FAIL'}")
        print(f"  with trend: rho {-ct:.2f} [{tlo:.2f}, {thi:.2f}] -> {'inside' if inside else 'OUTSIDE'} the main interval; MIBGAS control rho {-cm:.2f}")
        print(f"  gates: {'ALL PASS' if gate else 'FAIL: the price outcome does not size rho'}")
        rows.append({"outcome": y, "r": r, "iberian": int(ib.sum()), "rho": -c, "lo": lo, "hi": hi, "perm_p": p, "rho_trend": -ct,
                     "trend_lo": tlo, "trend_hi": thi, "rho_mibgas": -cm, "gate": gate})
    pd.DataFrame(rows).to_csv(T / "gas_cap_quantity_price.csv", index=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
