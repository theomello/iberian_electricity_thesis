"""Estimation of docs/specs/2026-11-17-industry-iv-wind-speed-estimation-design.md (rules E1-E9).

    .venv/bin/python scripts/analysis/industry_iv_wind_speed_estimation.py

Industrial hourly ln load (ESIOS 1204-1207) on the OMIE day-ahead price, instrument C1 = week-on-week change of min(ws/12, 1)^3 (national mean 100 m wind speed) and its square, common sample of the
first settlement (19,388 weekday hours 2019-2023), week-on-week differences, double ML without realised wind among the predictors (C1's home set). Variants: primary; V1 (FE + temperature, no ML);
single instrument d_pc; years 2019, 2021, 2022, 2023; hour blocks; sub-periods; placebo outcome (7-day-lagged differenced load, residualised without its own lag). Inference as industry_iv_estimation.py
(permutation t-rank and Anderson-Rubin set, 1,000 permutations, seed 20261117). Writes outputs/tables/industry_iv_wind_speed.csv and industry_iv_wind_speed_checks.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

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
    print(f"mean price {pbar:.2f}", flush=True)
    R = S2.residualise(d, False, {"d_pc": d.d_pc, "d_pc2": d.d_pc ** 2})
    Z = np.column_stack([R["d_pc"], R["d_pc2"]])
    # V1: fixed effects and temperature, no machine learning
    ym, hd = N.fe_matrix(d, False)
    X1 = np.column_stack([ym, hd[:, 1:], d.d_temp, d.d_temp ** 2])
    V1 = dict(y=N.ols_resid(d.d_lnL.to_numpy(), X1), p=N.ols_resid(d.d_p.to_numpy(), X1), Z=np.column_stack([N.ols_resid(c, X1) for c in (d.d_pc.to_numpy(), (d.d_pc ** 2).to_numpy())]))
    srcs = E.perm_sources(d, np.random.default_rng(N.SEED), E.NPERM)
    yr, hr = d.date.dt.year.to_numpy(), d.hour.to_numpy()
    allm = np.ones(len(d), bool)
    jobs = [("primary", "full", R["y"], R["p"], Z, allm, [0, 1]),
            ("primary", "d_pc only", R["y"], R["p"], Z, allm, [0]),
            ("primary", "2019-21H1", R["y"], R["p"], Z, (d.date < "2021-07-01").to_numpy(), [0, 1]),
            ("primary", "2021H2-23", R["y"], R["p"], Z, (d.date >= "2021-07-01").to_numpy(), [0, 1]),
            *[("primary", str(y), R["y"], R["p"], Z, yr == y, [0, 1]) for y in (2019, 2021, 2022, 2023)],
            ("primary", "night 0-7", R["y"], R["p"], Z, hr <= 7, [0, 1]),
            ("primary", "day 8-17", R["y"], R["p"], Z, (hr >= 8) & (hr <= 17), [0, 1]),
            ("primary", "evening 18-23", R["y"], R["p"], Z, hr >= 18, [0, 1]),
            ("placebo", "full", R["yplac"], R["p"], Z, allm, [0, 1]),
            ("V1 FE no ML", "full", V1["y"], V1["p"], V1["Z"], allm, [0, 1])]
    rows = []
    for name, block, y, p, Zm, mask, cols in jobs:
        sub = E.Sub(d, y, p, Zm, mask, cols)
        sub.Zfull = Zm
        r, tp = E.run_sub(sub, srcs, pbar)
        if name == "primary" and block == "full":
            r["hansen_J"], r["hansen_p"] = sub.hansen(sub.Z0)
        rows.append(dict(variant=name, block=block, **r))
        print(name, block, {k: (round(float(v), 4) if isinstance(v, (float, np.floating)) else v) for k, v in r.items() if k in ("F", "elasticity", "se_elasticity", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank")}, flush=True)
    Rr = pd.DataFrame(rows)
    Rr.round(5).to_csv(T.OUT / "industry_iv_wind_speed.csv", index=False)

    g = lambda v, b: Rr[(Rr.variant == v) & (Rr.block == b)].iloc[0]
    m = g("primary", "full")
    ch = []
    ch.append(("E1 sign and plausibility", bool(m.elasticity < 0 and abs(m.elasticity) <= 1), f"elasticity {m.elasticity:.4f}"))
    ch.append(("E2 detected", bool(m.p_t_rank <= 0.05 and (m.rand_hi < 0 or m.rand_lo > 0)), f"p_t {m.p_t_rank:.3f}, p_AR0 {m.p_ar0_rank:.3f}, rand [{m.rand_lo:.4f}, {m.rand_hi:.4f}]"))
    pl = g("placebo", "full")
    ch.append(("E3 placebo outcome", bool(pl.p_t_rank > 0.05 and abs(pl.elasticity) < 0.01), f"elasticity {pl.elasticity:.4f}, p_t {pl.p_t_rank:.3f}"))
    s1 = g("primary", "d_pc only")
    ch.append(("E4 overidentification", bool(m.hansen_p > 0.05 and m.rand_lo <= s1.elasticity <= m.rand_hi), f"J {m.hansen_J:.2f} p {m.hansen_p:.3f}; d_pc only {s1.elasticity:.4f} [{s1.rand_lo:.4f},{s1.rand_hi:.4f}]"))
    ys = [g("primary", str(y)) for y in (2019, 2021, 2022, 2023)]
    b_, s_ = np.array([y.slope for y in ys]), np.array([y.se_slope for y in ys])
    wbar = np.sum(b_ / s_ ** 2) / np.sum(1 / s_ ** 2)
    wp = float(stats.chi2.sf(np.sum((b_ - wbar) ** 2 / s_ ** 2), 3))
    ch.append(("E5 stability over years", bool(len(set(np.sign(b_))) == 1 and wp > 0.05), "elasticities " + ", ".join(f"{y.elasticity:.4f}" for y in ys) + f"; equality p {wp:.3f}"))
    ch.append(("E6 hour blocks and sub-periods (exploratory)", None, "; ".join(f"{b} {g('primary', b).elasticity:.4f} [{g('primary', b).rand_lo:.4f},{g('primary', b).rand_hi:.4f}]" for b in ("night 0-7", "day 8-17", "evening 18-23", "2019-21H1", "2021H2-23"))))
    v1 = g("V1 FE no ML", "full")
    ch.append(("E7 variant agreement", bool(m.rand_lo <= v1.elasticity <= m.rand_hi), f"V1 {v1.elasticity:.4f} [{v1.rand_lo:.4f},{v1.rand_hi:.4f}], primary {m.elasticity:.4f} [{m.rand_lo:.4f},{m.rand_hi:.4f}]"))
    ch.append(("E8 calibration of permutation test", bool(0.02 <= m.loo_share_p_lt05 <= 0.10), f"leave-one-out share p<0.05 {m.loo_share_p_lt05:.3f}; share |t|>1.96 {m.perm_share_t_gt196:.3f}"))
    ch.append(("E9 context (no pass/fail)", None, "earlier: forecast instruments +0.005; bid curve -0.036 [-0.080,+0.010]; weekday bound -0.03 [-0.055,+0.006]; Hirth et al. about -0.05 aggregate"))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_wind_speed_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 220)
    print("\n", Rr[["variant", "block", "n", "F", "elasticity", "se_elasticity", "norm_lo", "norm_hi", "ar_lo", "ar_hi", "rand_lo", "rand_hi", "p_t_rank", "p_ar0_rank"]].round(4).to_string(index=False))
    print("\n", C.to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
