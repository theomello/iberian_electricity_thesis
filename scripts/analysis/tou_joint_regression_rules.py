"""Rules J0-J6 of docs/specs/2026-11-26-joint-regression-design.md from the per-tariff files."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_drift_location as DL  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402
import tou_tariff_drift as TD  # noqa: E402

OUT = S6.OUT
PL = S6.SUMMERS
COMMITTED = {"6.2": (-0.06369, 0.01955, 0.01684), "6.3": (-0.23291, 0.19751, 0.1808), "6.4": (-0.33676, 0.32562, 0.0830)}


def effect(b):
    return float(b[2021] - b.drop(2021).mean())


def main():
    summary = []
    for tar in ("6.2", "6.3", "6.4"):
        R = pd.read_csv(OUT / f"tou_joint_regression_{tar}.csv")
        g = lambda v: R[R.variant == v].set_index("summer")
        base, main_ = g("base").beta, g("main").beta
        e, mu, sd = COMMITTED[tar]
        j0 = abs(base[2021] - e) < 0.0015 and abs(base.drop(2021).mean() - mu) < 0.0015 and abs(base.drop(2021).std(ddof=1) - sd) < 0.0015
        print(f"\n=== {tar} ===  J0 baseline reproduction: {'pass' if j0 else 'FAIL'}   J per summer {g('main').n_controls.to_dict()}  variance explained {g('main').var_expl_J.round(2).to_dict()}")
        if not j0:
            continue
        j1v = g("main").dose_var_left
        j1 = bool((j1v >= 0.20).all())
        print(f"J1 real-dose variance left after FE and controls: min {j1v.min():.2f} (per summer {j1v.round(2).to_dict()}) -> {'pass' if j1 else 'FAIL'}")
        pl = main_.drop(2021)
        sl, se = DL.slope(pl.to_dict())
        j2 = not (abs(sl) >= 1.5 * se)
        j3 = float(pl.std(ddof=1)) <= sd
        mean, trend, *_ = TD.nulls(float(main_[2021]), pl.to_dict())
        det_mean = mean["eff"] < 0 and mean["p"] <= 0.05
        det_trend = trend["eff"] < 0 and trend["p"] <= 0.05
        j4 = det_mean and (j2 or det_trend)
        print(f"main betas: 2021 {main_[2021]:+.4f}; placebos {' '.join(f'{k}:{v:+.3f}' for k, v in pl.items())}")
        print(f"J2 placebo slope {sl:+.4f} (se {se:.4f}) not established: {j2}")
        print(f"J3 placebo sd {pl.std(ddof=1):.4f} <= baseline {sd:.4f}: {j3}")
        print(f"J4 mean null: effect {mean['eff']:+.3f} p {mean['p']:.4f} [{mean['lo']:+.3f},{mean['hi']:+.3f}] detected {det_mean} | trend null: effect {trend['eff']:+.3f} p {trend['p']:.3f} [{trend['lo']:+.3f},{trend['hi']:+.3f}] detected {det_trend} -> {'pass' if j4 else 'FAIL'}")
        eff = effect(main_)
        loo = []
        for y in PL:
            p2 = main_.drop([2021, y])
            loo.append(float(main_[2021] - p2.mean()))
        j5a = all(np.sign(v) == np.sign(eff) and abs(v - eff) <= 0.10 for v in loo)
        j5b_vals = {v: effect(g(v).beta) for v in ("mainJm1", "mainJp1") if (R.variant == v).any()}
        j5b = all(abs(v - eff) <= 0.05 for v in j5b_vals.values())
        print(f"J5a leave-one-placebo-out effects {[round(v, 3) for v in loo]} -> {j5a}; J5b other J: {{{', '.join(f'{k}: {v:+.3f}' for k, v in j5b_vals.items())}}} (main {eff:+.3f}) -> {j5b}")
        works = j1 and j2 and j4
        print(f"J6 tariff works (J1 and J2 and J4): {works}")
        if not det_mean:
            S = len(pl)
            sep = pl.std(ddof=1) * np.sqrt(1 + 1 / S)
            lb = eff - stats.t.ppf(0.95, S - 1) * sep
            print(f"   bound: one-sided 95% lower bound of the effect {lb:+.3f} (effect not more negative than this)")
        for v in ("S1", "S2"):
            bv = g(v).beta
            print(f"   {v}: 2021 {bv[2021]:+.4f}, placebo sd {bv.drop(2021).std(ddof=1):.4f}, effect {effect(bv):+.3f}, dose var left min {g(v).dose_var_left.min():.2f}")
        summary.append(dict(tariff=tar, effect=eff, J1=j1, J2=j2, J3=j3, J4=j4, J5a=j5a, J5b=j5b, works=works, slope=sl, slope_se=se, placebo_sd=float(pl.std(ddof=1))))
    pd.DataFrame(summary).to_csv(OUT / "tou_joint_regression_summary.csv", index=False)


if __name__ == "__main__":
    main()
