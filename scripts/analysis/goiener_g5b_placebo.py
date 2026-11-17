"""G5b of docs/specs/2026-11-17-goiener-household-design.md: placebo check of the share_night / share_peak dependence of the household response. Saved data only.

    .venv/bin/python scripts/analysis/goiener_g5b_placebo.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_did as T  # noqa: E402

ROOT = T.ROOT


def slope(d, c):
    z = (d[c] - d[c].mean()) / d[c].std()
    return float((z * (d.y - d.y.mean())).sum() / (z ** 2).sum())


def gap(d, c):
    q = pd.qcut(d[c], 4, labels=False, duplicates="drop")
    return float(d.y[q == q.max()].mean() - d.y[q == 0].mean())


def main():
    real = pd.read_parquet(ROOT / "data/goiener/daily/g5_real.parquet")
    pl = pd.read_parquet(ROOT / "data/goiener/daily/g5_placebo.parquet")
    rows = []
    for c, sign in (("share_night", 1), ("share_peak", -1)):
        br = slope(real, c)
        bp = np.array([slope(g, c) for _, g in pl.groupby("window")])
        gr = gap(real, c)
        gp = np.array([gap(g, c) for _, g in pl.groupby("window")])
        adj = br - bp.mean()
        p = (1 + np.sum(np.abs(bp - bp.mean()) >= abs(adj))) / (1 + len(bp))
        ok = bool(np.sign(adj) == sign and p <= 0.05)
        rows.append(dict(covariate=c, slope_real=br, slope_placebo_mean=float(bp.mean()), slope_placebo_sd=float(bp.std(ddof=1)), slope_adjusted=adj, p_two_sided=p, gap_real=gr, gap_placebo_mean=float(gp.mean()), expected_sign=sign, passed=ok))
        print({k: (round(v, 4) if isinstance(v, float) else v) for k, v in rows[-1].items()}, flush=True)
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "goiener_g5b.csv", index=False)
    print("G5b:", "both pass, pattern attributed to the reform response" if R.passed.all() else "not both passed: G5 heterogeneity not attributed to the reform")


if __name__ == "__main__":
    main()
