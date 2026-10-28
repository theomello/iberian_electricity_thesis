#!/usr/bin/env python3
"""Step B2 of the crisis quantity design: the cap's pass-through, Iberia against a counterfactual
built from Italy (docs/specs/2026-10-28-crisis-quantity-design.md §5, §7; B1 amended).

    .venv/bin/python scripts/analysis/gas_cap_quantity_b2.py [--reps 199]

Outcome: weekly unit means of run20 (MW offered at or below net cost + EUR 20, over K) in predicted
in-money hours (`gas_cap_quantity_b1.panel`), units as in B1. Estimator B (Xu 2017, main): factors
from Italian units over the whole window, each Iberian unit's loadings from the weeks before
2022-06-15, its no-cap path imputed; ATT_w = mean gap. r by Xu's cross-validation on the pre-cap
weeks; r = 0..5 as sensitivity. Estimator A (Bai 2009) beside it: theta on Iberia x high-subsidy week.

Effect: mean ATT over the weeks with a subsidy in June-September and December 2022 (B1 amended).
Without the cap a unit offers at gross cost + its markup, so its run20 is F(20); with the cap, full
pass-through keeps F(20) (ATT 0) and none gives F(20 - S) (ATT = -gap). So rho = 1 + ATT / gap, gap
the full-none difference over the same weeks (0.410, `gas_cap_quantity_b1_ends.csv`, held fixed).

Stop rule (fixed): the mean ATT over weeks after 2023-02-25 (no subsidy) outside [-0.05, +0.05] means
the counterfactual does not hold -- report and stop. Firm block bootstrap within country, 199 draws.

Checks (point estimates at the chosen r): (a) all hours, (b) margin EUR 20, (c) the main sample with
Iberian post-cap hours reweighted to the pre-cap hour-of-day mix.

Writes outputs/tables/gas_cap_quantity_b2.csv (estimates) and gas_cap_quantity_b2_weekly.csv (ATT_w).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
from gas_cap_ife import bai, gsc, xu_cv  # noqa: E402
from gas_cap_quantity_b1 import CAP0, matrix, panel  # noqa: E402

T = ROOT / "outputs" / "tables"
CAP1 = pd.Timestamp("2023-02-25")
HIGH = ["2022-06", "2022-07", "2022-08", "2022-09", "2022-12"]
TOL = 0.05


def weeks_info(cols: pd.DatetimeIndex) -> tuple[np.ndarray, np.ndarray, float]:
    e = pd.read_csv(T / "gas_cap_quantity_b1_ends.csv", parse_dates=["w"]).set_index("w")
    s = e.subsidy.reindex(cols).fillna(0.0)
    high = (s > 0).to_numpy() & cols.strftime("%Y-%m").isin(HIGH)
    gap = float((e.full_run20 - e.none_run20).reindex(cols)[high].mean())
    after = (cols > CAP1)
    return high, after, gap


def estimate(M, ib, pre, high, after, r):
    att = gsc(M, ib, pre, r)
    return float(np.nanmean(att[high])), float(np.nanmean(att[after])), att


def reweighted(h: pd.DataFrame) -> pd.DataFrame:
    h = h.copy()
    h["hod"] = h.period.clip(upper=24)
    ib = h.iberia
    pre_mix = h[ib & (h.date < CAP0)].hod.value_counts(normalize=True)
    post_mix = h[ib & (h.date >= CAP0)].hod.value_counts(normalize=True)
    h["wt"] = 1.0
    post = ib & (h.date >= CAP0)
    h.loc[post, "wt"] = (h.loc[post, "hod"].map(pre_mix) / h.loc[post, "hod"].map(post_mix)).fillna(0.0)
    h["run20"] = h.run20 * h.wt
    g = h.groupby(["unit", "w"])
    return (g.run20.sum() / g.wt.sum()).rename("run20").reset_index().merge(
        h.drop_duplicates("unit")[["unit", "iberia", "firm"]], on="unit")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--reps", type=int, default=199)
    a = ap.parse_args()
    rng = np.random.default_rng(20261028)
    h = panel()
    W, thr = matrix(h, "run20")
    meta = h.drop_duplicates("unit").set_index("unit")
    ib = meta.iberia.reindex(W.index).to_numpy()
    firm = meta.firm.reindex(W.index).to_numpy()
    cols = W.columns
    M = W.to_numpy()
    pre = cols < CAP0
    high, after, gap = weeks_info(cols)
    print(f"{ib.sum()} Iberian, {(~ib).sum()} Italian units x {len(cols)} weeks (missing limit {thr:.0%}); "
          f"{high.sum()} high-subsidy weeks, {after.sum()} weeks after the subsidy; gap full - none {gap:.3f}")
    cv = xu_cv(M, ib, pre)
    r = int(np.argmin(cv))
    print("Xu CV MSPE (r=0..5): " + ", ".join(f"{v:.5f}" for v in cv) + f" -> r = {r}")
    D = np.outer(ib.astype(float), high.astype(float))
    print("\nsensitivity:  r | B ATT high | B ATT after | B rho | A theta (Iberia x high)")
    sens = []
    for k in range(6):
        ah, aa, _ = estimate(M, ib, pre, high, after, k)
        tA = bai(M, D, k)
        sens.append({"r": k, "att_high": ah, "att_after": aa, "rho": 1 + ah / gap, "bai_theta": tA})
        print(f"  {k}{' *' if k == r else '  '} | {ah:+.3f} | {aa:+.3f} | {1 + ah / gap:.2f} | {tA:+.3f}")
    ah, aa, att = estimate(M, ib, pre, high, after, r)
    fi = pd.Series(firm)
    groups = {c: fi[ib == c].unique() for c in (True, False)}
    draws = []
    for _ in range(a.reps):
        idx = np.concatenate([np.flatnonzero((fi.to_numpy() == f_) & (ib == c))
                              for c in (True, False)
                              for f_ in rng.choice(groups[c], size=len(groups[c]), replace=True)])
        draws.append(estimate(M[idx], ib[idx], pre, high, after, r)[:2])
    dr = np.array(draws)
    ci_h, ci_a = np.nanpercentile(dr[:, 0], [2.5, 97.5]), np.nanpercentile(dr[:, 1], [2.5, 97.5])
    stop = abs(aa) > TOL
    print(f"\nmain, r = {r}, firm block bootstrap {a.reps} ({len(groups[True])} Iberian, {len(groups[False])} Italian firms):")
    print(f"  ATT, high-subsidy weeks   {ah:+.3f}  95% [{ci_h[0]:+.3f}, {ci_h[1]:+.3f}]")
    print(f"  rho = 1 + ATT / gap       {1 + ah / gap:.2f}  95% [{1 + ci_h[0] / gap:.2f}, {1 + ci_h[1] / gap:.2f}]")
    print(f"  ATT after 2023-02-25      {aa:+.3f}  95% [{ci_a[0]:+.3f}, {ci_a[1]:+.3f}]  "
          f"{'<-- outside +-0.05: STOP' if stop else '(within +-0.05: check holds)'}")
    checks = []
    for lab, hh in (("all hours", panel(None)), ("margin > 20", panel(20.0))):
        Wc, _ = matrix(hh, "run20")
        m2 = hh.drop_duplicates("unit").set_index("unit")
        ibc = m2.iberia.reindex(Wc.index).to_numpy()
        c_h, c_a, _ = estimate(Wc.to_numpy(), ibc, Wc.columns < CAP0, *weeks_info(Wc.columns)[:2], r)
        checks.append({"check": lab, "att_high": c_h, "att_after": c_a, "iberian_units": int(ibc.sum())})
    rw = reweighted(h)
    Wr = rw.pivot(index="unit", columns="w", values="run20").reindex(index=W.index, columns=cols)
    c_h, c_a, _ = estimate(Wr.to_numpy(), ib, pre, high, after, r)
    checks.append({"check": "pre-cap hour-of-day mix", "att_high": c_h, "att_after": c_a, "iberian_units": int(ib.sum())})
    print("\nchecks (point estimates, r as main):")
    for c in checks:
        print(f"  {c['check']:<26} ATT high {c['att_high']:+.3f}, after {c['att_after']:+.3f} ({c['iberian_units']} Iberian units)")
    out = pd.concat([pd.DataFrame([{"estimate": "main", "r": r, "att_high": ah, "att_high_lo": ci_h[0],
                                    "att_high_hi": ci_h[1], "rho": 1 + ah / gap, "rho_lo": 1 + ci_h[0] / gap,
                                    "rho_hi": 1 + ci_h[1] / gap, "att_after": aa, "att_after_lo": ci_a[0],
                                    "att_after_hi": ci_a[1], "gap": gap, "stop": stop}]),
                     pd.DataFrame(sens).assign(estimate="sensitivity"),
                     pd.DataFrame(checks).assign(estimate="check")], ignore_index=True)
    out.to_csv(T / "gas_cap_quantity_b2.csv", index=False)
    pd.DataFrame({"week": cols, "high": high, "after": after, "att": att}).to_csv(
        T / "gas_cap_quantity_b2_weekly.csv", index=False)
    print(f"\nB2 rule: {'STOP (counterfactual fails after the subsidy)' if stop else 'counterfactual holds'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
