"""Rules C0-C5 of docs/specs/2026-11-26-calendar-randomization-design.md, from the per-tariff beta files."""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_drift_location as DL  # noqa: E402
import tou_industry_six_summer as S6  # noqa: E402

OUT = S6.OUT
COMMITTED = {"6.2": (-0.06369, 0.01955, 0.01684), "6.3": (-0.23291, 0.19751, 0.1808), "6.4": (-0.33676, 0.32562, 0.0830)}
PL = S6.SUMMERS


def pred_t(real, pl):
    pl = np.asarray(pl, float)
    S = len(pl)
    t = (real - pl.mean()) / (pl.std(ddof=1) * np.sqrt(1 + 1 / S))
    return float(t), float(stats.t.cdf(t, S - 1))


def analyse(R, cap):
    """R: beta rows for one tariff. Returns dict of the quantities for calendars with |corr| <= cap."""
    real = R[R["shift"] == 0].set_index("summer").beta
    cf = R[(R["shift"] != 0) & (R.corr_with_real.abs() <= cap)]
    m = cf.groupby("summer").beta.mean()
    d = real - m
    return real, cf, m, d


def main():
    for tar in ("6.2", "6.3", "6.4"):
        p = OUT / f"tou_calendar_randomization_{tar}.csv"
        if not p.exists():
            print(tar, "missing"); continue
        R = pd.read_csv(p)
        e, mu, sd = COMMITTED[tar]
        real = R[R["shift"] == 0].set_index("summer").beta
        pl = real.drop(2021)
        ok = abs(real[2021] - e) < 0.0015 and abs(pl.mean() - mu) < 0.0015 and abs(pl.std(ddof=1) - sd) < 0.0015
        print(f"\n=== {tar} ===\nC0 reproduction: eta {real[2021]:+.5f} mean {pl.mean():+.5f} sd {pl.std(ddof=1):.5f} -> {'pass' if ok else 'FAIL'}")
        if not ok:
            continue
        for cap in (0.5, 0.3):
            real, cf, m, d = analyse(R, cap)
            ncal = cf.groupby("shift").ngroups
            print(f"-- screen |corr| <= {cap}: {ncal} calendars {sorted(cf['shift'].unique().tolist())}")
            if cap == 0.5 and ncal < 6:
                print("C1 fail: fewer than 6 calendars; not run"); break
            if ncal < 3:
                print("   too few for the sensitivity"); continue
            t2, p2 = pred_t(m[2021], m.drop(2021))
            print(f"C2 m_cf(2021) {m[2021]:+.4f} vs placebo mean {m.drop(2021).mean():+.4f} sd {m.drop(2021).std(ddof=1):.4f}: t {t2:+.2f} -> {'pass' if abs(t2) <= 2.57 else 'FAIL'}")
            sl, se = DL.slope(d.drop(2021).to_dict())
            sd_d, sd_b = d.drop(2021).std(ddof=1), real.drop(2021).std(ddof=1)
            c3a, c3b = sd_d <= 0.8 * sd_b, not (abs(sl) >= 1.5 * se)
            print(f"C3 placebo sd of Delta {sd_d:.4f} vs real beta {sd_b:.4f} (ratio {sd_d / sd_b:.2f}, need <= 0.8): {c3a}; Delta slope {sl:+.4f} (se {se:.4f}) not established: {c3b} -> {'pass' if c3a and c3b else 'FAIL'}")
            t4, p4 = pred_t(d[2021], d.drop(2021))
            print(f"C4 Delta_2021 {d[2021]:+.4f}  (placebo Delta: {' '.join(f'{k}:{v:+.3f}' for k, v in d.drop(2021).items())})  t {t4:+.2f} p {p4:.3f} -> {'detected' if d[2021] < 0 and p4 <= 0.05 else 'not detected'}")
            if cap == 0.5:
                ks = sorted(cf["shift"].unique())
                ok5 = True
                for k in ks:
                    mk = cf[cf["shift"] != k].groupby("summer").beta.mean()
                    dk = real - mk
                    ok5 &= np.sign(mk[2021]) == np.sign(m[2021]) and abs(mk[2021] - m[2021]) <= 0.05 and abs(dk[2021] - d[2021]) <= 0.05
                print(f"C5 leave-one-calendar-out keeps sign and within 0.05 for m_cf(2021) and Delta(2021): {bool(ok5)}")
                print("   per-calendar 2021 betas: " + " ".join(f"{k:+d}:{cf[(cf['shift'] == k) & (cf.summer == 2021)].beta.iloc[0]:+.3f}" for k in ks))
                print("   per-year m_cf: " + " ".join(f"{y}:{v:+.3f}" for y, v in m.items()) + " | real: " + " ".join(f"{y}:{v:+.3f}" for y, v in real.items()))


if __name__ == "__main__":
    main()
