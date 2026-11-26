"""Part 2 of docs/specs/2026-11-26-calendar-randomization-design.md: a local-level model for the six placebo betas per tariff.

Random walk plus noise, diffuse start, q = var(level shock)/var(noise) on a grid, sigma^2 concentrated out. 2021 is two steps past 2019.
The 2021 estimate's standard error comes from the calendar-randomization files (real calendar, summer 2021).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
GRID = [0.0, 0.01, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0]
STEP3 = {"6.2": (-0.0832, -0.0792), "6.3": (-0.4304, -0.0198), "6.4": (-0.6624, -0.5719)}


def filt(y, q):
    a, P = y[0], 1.0  # diffuse start: first observation initialises the level (variance 1 in noise units)
    v, F = [], []
    for t in range(1, len(y)):
        P = P + q
        Ft = P + 1.0
        vt = y[t] - a
        K = P / Ft
        a, P = a + K * vt, P * (1 - K)
        v.append(vt); F.append(Ft)
    v, F = np.array(v), np.array(F)
    n = len(v)
    s2 = float((v ** 2 / F).sum() / n)
    ll = -0.5 * (np.log(F).sum() + n * np.log(s2))
    return a, P, s2, ll


def main():
    rows = []
    for tar in ("6.2", "6.3", "6.4"):
        R = pd.read_csv(OUT / f"tou_calendar_randomization_{tar}.csv")
        real = R[R["shift"] == 0].set_index("summer")
        y = np.array([real.beta[s] for s in S6.SUMMERS])
        eta, se21 = float(real.beta[2021]), float(real.se[2021])
        res = {q: filt(y, q) for q in GRID}
        qhat = max(GRID, key=lambda q: res[q][3])
        print(f"\n=== {tar}: eta_2021 {eta:+.4f} (se {se21:.4f}); placebos {' '.join(f'{v:+.3f}' for v in y)}")
        print("profile (q: loglik): " + " ".join(f"{q:g}:{res[q][3]:.2f}" for q in GRID) + f"  -> q_hat {qhat:g}")
        for q in (0.0, qhat, 10.0):
            a, P, s2, ll = res[q]
            n = len(y) - 1
            var = s2 * (P + 2 * q + 1.0)  # 2021 is two steps past the last placebo
            sd = np.sqrt(var + se21 ** 2)
            tq = stats.t.ppf(0.975, n)
            eff = eta - a
            lo, hi = eff - tq * sd, eff + tq * sd
            tag = "q_hat" if q == qhat else f"q={q:g}"
            rows.append(dict(tariff=tar, q=q, q_hat=qhat, predicted_2021=a, effect=eff, lo=lo, hi=hi))
            print(f"   {tag:8s} predicted {a:+.3f}  effect {eff:+.3f}  95% [{lo:+.3f}, {hi:+.3f}]")
        mean_e, trend_e = STEP3[tar]
        a, P, s2, _ = res[qhat]
        sd = np.sqrt(s2 * (P + 2 * qhat + 1.0) + se21 ** 2)
        eff = eta - a
        tq = stats.t.ppf(0.975, len(y) - 1)
        lo, hi = eff - tq * sd, eff + tq * sd
        both = lo <= min(mean_e, trend_e) and hi >= max(mean_e, trend_e)
        print(f"   L2: interval at q_hat [{lo:+.3f}, {hi:+.3f}] contains mean-null {mean_e:+.3f} and trend-null {trend_e:+.3f}: {both}; excludes zero: {not (lo <= 0 <= hi)}")
    pd.DataFrame(rows).to_csv(OUT / "tou_local_level.csv", index=False)


if __name__ == "__main__":
    main()
