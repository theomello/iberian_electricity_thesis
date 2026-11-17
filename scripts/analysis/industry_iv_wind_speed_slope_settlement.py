"""Scoring of docs/specs/2026-11-17-industry-iv-wind-speed-slope-design.md (rules S1-S4); first stage and placebo only, no elasticity.

    .venv/bin/python scripts/analysis/industry_iv_wind_speed_slope_settlement.py

X1 = instruments d_pc and d_pc x s (s = standardised offer-curve slope of the same hour 7 days earlier); the slope level (slope7) is added to the double-ML predictors. Common sample, 10 time blocks,
placebo outcome residualised without its own lag, 1,000 permutations, seed 20261117, idle-wind rows (mean national speed < 5 m/s both weeks) as in the settlements. Writes
outputs/tables/industry_iv_wind_speed_slope{,_rules}.csv.
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
    X = np.column_stack([S2.predictors(d, False), d.slope7])
    order = d.date.rank(method="dense").to_numpy()
    blocks = np.minimum((order / order.max() * 10).astype(int), 9)
    Zd = {"d_pc": d.d_pc, "int": d.d_pc * d.slope7z}
    names = ["y", "p"] + list(Zd)
    Y = np.column_stack([np.asarray(d.d_lnL, float), np.asarray(d.d_p, float)] + [np.asarray(v, float) for v in Zd.values()])
    R = dict(zip(names, N.gb_resid(Y, X, blocks, d.date.to_numpy()).T))
    keep = [i for i in range(X.shape[1]) if i != 6]
    R["yplac"] = N.gb_resid(np.asarray(d.d_lnL_7, float)[:, None], X[:, keep], blocks, d.date.to_numpy())[:, 0]
    print(f"placebo residual sd {R['yplac'].std():.4f} vs raw {d.d_lnL_7.std():.4f}", flush=True)
    srcs = E.perm_sources(d, np.random.default_rng(N.SEED), 1000)
    rows = S2.score(d, R, "X1", ["d_pc", "int"], srcs)
    Rr = pd.DataFrame(rows)
    F3 = pd.DataFrame([S2.f3(d, R, "X1 wind component d_pc", "d_pc", srcs), S2.f3(d, R, "X1 interaction", "int", srcs)])
    inc = S2.incremental_F(R["p"], R["d_pc"][:, None], R["int"][:, None], d)
    r = Rr.set_index("block")
    s1 = bool(r.loc["full", "F1"] >= 20 and r.loc["2019-21H1", "F1"] >= 10 and r.loc["2021H2-23", "F1"] >= 10)
    s2 = bool(all(r.loc[b, "placebo_p"] > 0.10 for b in r.index))
    s3 = bool(all(f.f3_status == "tested" and f.f3_p > 0.05 and abs(f.f3_ratio) <= 0.5 for f in F3.itertuples()))
    Q = pd.DataFrame([dict(S1=s1, S2=s2, S3=s3, passes=s1 and s2 and s3, S4_incremental_F_interaction_over_d_pc=inc, S4_adds=bool(inc >= 10))])
    Rr.round(5).to_csv(T.OUT / "industry_iv_wind_speed_slope.csv", index=False)
    Q.to_csv(T.OUT / "industry_iv_wind_speed_slope_rules.csv", index=False)
    F3.round(5).to_csv(T.OUT / "industry_iv_wind_speed_slope_f3.csv", index=False)
    pd.set_option("display.width", 250)
    print(Rr.round(4).to_string(index=False))
    print(F3.round(4).to_string(index=False))
    print(Q.round(3).to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
