"""Run of docs/specs/2026-11-17-industry-iv-planted-effect-design.md (rules P1-P4).

    .venv/bin/python scripts/analysis/industry_iv_planted_effect.py

Plants a same-hour response beta to the day-ahead price in the industrial outcome, d ln L* = d ln L + (beta / pbar) x d p (all rows, or one half of the sample), refits the double-ML residual of the planted outcome,
and runs the wind-speed IV (instruments d_pc, d_pc^2) exactly as industry_iv_wind_speed_estimation.py. Price and instrument residuals are the real run's. Seed 20261117, 1,000 permutations.
Writes outputs/tables/industry_iv_planted_effect.csv and industry_iv_planted_effect_checks.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_instrument_settlement as S  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import industry_iv_second_settlement as S2  # noqa: E402
import tou_did as T  # noqa: E402


def main():
    d = S.build_frame()
    assert d.date.is_monotonic_increasing
    pbar = float(d.p.mean())
    R = S2.residualise(d, False, {"d_pc": d.d_pc, "d_pc2": d.d_pc ** 2})
    Z = np.column_stack([R["d_pc"], R["d_pc2"]])
    X = S2.predictors(d, False)
    order = d.date.rank(method="dense").to_numpy()
    blocks = np.minimum((order / order.max() * 10).astype(int), 9)
    h1 = (d.date < "2021-07-01").to_numpy()
    srcs = E.perm_sources(d, np.random.default_rng(N.SEED), E.NPERM)
    plants = [("pooled", -0.02, np.ones(len(d), bool)), ("pooled", -0.03, np.ones(len(d), bool)), ("pooled", -0.05, np.ones(len(d), bool)), ("pooled", -0.10, np.ones(len(d), bool)),
              ("half 2019-21H1", -0.10, h1), ("half 2021H2-23", -0.10, ~h1)]
    rows = []
    for name, beta, m in plants:
        yp = np.asarray(d.d_lnL, float) + np.where(m, beta / pbar * np.asarray(d.d_p, float), 0.0)
        yres = N.gb_resid(yp[:, None], X, blocks, d.date.to_numpy())[:, 0]
        sub = E.Sub(d, yres, R["p"], Z, np.ones(len(d), bool), [0, 1])
        sub.Zfull = Z
        r, _ = E.run_sub(sub, srcs, pbar)
        expected = beta * (m.mean() if name != "pooled" else 1.0)
        rows.append(dict(plant=name, beta=beta, expected=expected, **r))
        print(name, beta, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("F", "elasticity", "rand_lo", "rand_hi", "p_t_rank")}, flush=True)
    P = pd.DataFrame(rows)
    P.round(5).to_csv(T.OUT / "industry_iv_planted_effect.csv", index=False)
    ch = []
    pooled = P[P.plant == "pooled"]
    p1 = [(bool(r.rand_lo <= r.beta <= r.rand_hi and abs(r.elasticity - r.beta) <= max(0.01, 0.3 * abs(r.beta))), r.beta) for r in pooled.itertuples()]
    ch.append(("P1 recovery (pooled plants)", all(x for x, _ in p1), "; ".join(f"{b}: est {pooled[pooled.beta == b].elasticity.iloc[0]:.4f} [{pooled[pooled.beta == b].rand_lo.iloc[0]:.4f},{pooled[pooled.beta == b].rand_hi.iloc[0]:.4f}] {'ok' if x else 'FAIL'}" for x, b in p1)))
    det = lambda r: bool(r.p_t_rank <= 0.05 and (r.rand_hi < 0 or r.rand_lo > 0))
    p2 = [(det(r), r.beta) for r in pooled.itertuples() if r.beta in (-0.05, -0.10)]
    ch.append(("P2 detection at -0.05 and -0.10", all(x for x, _ in p2), "; ".join(f"{b}: {'detected' if x else 'NOT detected'}" for x, b in p2)))
    hs = P[P.plant != "pooled"]
    p3 = [(bool(abs(r.elasticity - r.expected) <= 0.02), r.plant) for r in hs.itertuples()]
    ch.append(("P3 half-sample", all(x for x, _ in p3), "; ".join(f"{n}: est {hs[hs.plant == n].elasticity.iloc[0]:.4f} vs expected {hs[hs.plant == n].expected.iloc[0]:.4f}" for _, n in p3)))
    dets = [r.beta for r in pooled.itertuples() if det(r)]
    ch.append(("P4 power (no pass/fail)", None, "detected pooled plants: " + (", ".join(str(b) for b in dets) if dets else "none") + "; smallest detected: " + (str(max(dets)) if dets else "none")))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_planted_effect_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 250)
    print(P[["plant", "beta", "expected", "F", "elasticity", "rand_lo", "rand_hi", "p_t_rank"]].round(4).to_string(index=False))
    print(C.to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
