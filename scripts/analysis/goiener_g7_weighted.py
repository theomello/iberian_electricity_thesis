"""G7 of docs/specs/2026-11-17-goiener-household-design.md: consumption-weighted household elasticity against the placebo windows. Saved data only.

    .venv/bin/python scripts/analysis/goiener_g7_weighted.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tou_did as T  # noqa: E402

ROOT, DOSE = T.ROOT, 0.784


def wmean(d, weighted):
    return float(np.average(d.y, weights=d.mean_kwh)) if weighted else float(d.y.mean())


def run(real, pl, weighted):
    er = wmean(real, weighted) / DOSE
    ep = np.array([wmean(g, weighted) / DOSE for _, g in pl.groupby("window")])
    return dict(weighted=weighted, eta_real=er, mean_placebo=float(ep.mean()), eta_RI=er - float(ep.mean()), p_one_sided=(1 + np.sum(ep <= er)) / (1 + len(ep)),
                fisher_lo=er - float(np.quantile(ep, 0.975)), fisher_hi=er - float(np.quantile(ep, 0.025)), households=len(real))


def main():
    real = pd.read_parquet(ROOT / "data/goiener/daily/g5_real.parquet")
    pl = pd.read_parquet(ROOT / "data/goiener/daily/g5_placebo.parquet")
    R = pd.DataFrame([run(real, pl, False), run(real, pl, True)])
    pd.set_option("display.width", 200)
    print(R.round(4).to_string(index=False))
    u, w = float(R.eta_RI[0]), float(R.eta_RI[1])
    print(f"G7a unweighted {u:+.4f} within 0.01 of -0.053: {abs(u + 0.053) <= 0.01}")
    cls = "explains the gap" if (w <= -0.080 and R.p_one_sided[1] <= 0.05) else ("partly" if -0.080 < w <= -0.063 else ("no" if abs(w - u) <= 0.01 else "in between, not classified as partly or explains"))
    print(f"G7b weighted {w:+.4f}: weighting {cls}")
    R.round(5).to_csv(T.OUT / "goiener_g7.csv", index=False)


if __name__ == "__main__":
    main()
