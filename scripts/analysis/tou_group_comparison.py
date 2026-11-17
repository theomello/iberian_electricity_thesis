"""Randomization test of the difference in elasticity between a customer group and households (docs/specs/2026-11-17-group-comparison-design.md, rules C0-C3).

    .venv/bin/python scripts/analysis/tou_group_comparison.py

Reads the window-level estimates of tou_randomization_inference.py (real estimate from tou_randomization_inference_summary.csv, placebo estimates from tou_randomization_inference.csv). No model is fitted.
Writes outputs/tables/tou_group_comparison.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_did as T  # noqa: E402

OUT = T.OUT


def main():
    W = pd.read_csv(OUT / "tou_randomization_inference.csv", parse_dates=["start", "end"])
    S = pd.read_csv(OUT / "tou_randomization_inference_summary.csv")
    ks = sorted(W.k.unique())
    n_ok = W.groupby("series").k.nunique()
    print("C0 windows per series:", n_ok.to_dict(), "->", bool((n_ok == 109).all()), flush=True)
    real = S[S.subset == "all"].set_index("series").eta_real
    piv = W.pivot(index="k", columns="series", values="eta")
    # subsets as in the RI run
    non, last = [], -999
    for k in ks:
        if last == -999 or abs(k - last) >= 16:
            non.append(k)
            last = k
    st = W.drop_duplicates("k").set_index("k").start
    sm = [k for k in ks if st[k].year in (2018, 2019) and abs((st[k] - pd.Timestamp(year=st[k].year, month=6, day=1)).days) <= 45]
    subsets = {"all": ks, "non-overlapping": non, "season-matched": sm}
    rows = []
    for g in ("E1+E2", "IND", "6.2", "6.3", "6.4"):
        Dreal = real[g] - real["E0"]
        for lab, kk in subsets.items():
            D = (piv.loc[kk, g] - piv.loc[kk, "E0"]).to_numpy()
            m = D.mean()
            N = len(D)
            p2 = (1 + (np.abs(D - m) >= abs(Dreal - m)).sum()) / (1 + N)
            p1 = (1 + (D <= Dreal).sum()) / (1 + N)
            rows.append(dict(group=g, subset=lab, N=N, eta_group=real[g], eta_house=real["E0"], gap=Dreal, placebo_mean_gap=m, placebo_sd_gap=D.std(ddof=1), adjusted_gap=Dreal - m,
                             ci_lo=Dreal - np.quantile(D, 0.975), ci_hi=Dreal - np.quantile(D, 0.025), p_two_sided=p2, p_one_sided=p1, detectable_gap=2.8 * D.std(ddof=1)))
    R = pd.DataFrame(rows)
    R.round(5).to_csv(OUT / "tou_group_comparison.csv", index=False)
    pd.set_option("display.width", 220)
    print(R.round(3).to_string(index=False))
    household = abs(real["E0"])
    for g in ("E1+E2", "IND"):
        a = R[(R.group == g) & (R.subset == "all")].iloc[0]
        s = R[(R.group == g) & (R.subset == "season-matched")].iloc[0]
        n = R[(R.group == g) & (R.subset == "non-overlapping")].iloc[0]
        if a.detectable_gap > household:
            cls = "uninformative"
        elif a.p_two_sided <= 0.10 and s.p_two_sided <= 0.10 and a.detectable_gap < abs(a.gap):
            cls = "distinguishable"
        else:
            cls = "not distinguishable"
        cls_n = ("uninformative" if n.detectable_gap > household else "distinguishable" if (n.p_two_sided <= 0.15 and n.detectable_gap < abs(n.gap)) else "not distinguishable")
        print(f"C1 {g}: gap {a.gap:+.3f} (adjusted {a.adjusted_gap:+.3f}, interval [{a.ci_lo:+.3f}, {a.ci_hi:+.3f}]), p all {a.p_two_sided:.3f}, season {s.p_two_sided:.3f}, detectable gap {a.detectable_gap:.3f} vs household {household:.3f} -> {cls}")
        print(f"C2 {g}: non-overlapping p {n.p_two_sided:.3f} (N {int(n.N)}) classification {cls_n}; unchanged: {cls_n == cls}")
        if cls == "distinguishable":
            print(f"C3 {g}: adjusted gap sign {'more' if a.adjusted_gap < 0 else 'less'} elastic than households")


if __name__ == "__main__":
    main()
