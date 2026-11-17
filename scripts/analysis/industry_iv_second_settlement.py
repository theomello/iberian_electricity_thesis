"""Run of docs/specs/2026-11-17-industry-iv-bid-instrument-second-settlement-design.md (rules S1-S5, J, with its pre-run amendments).

    .venv/bin/python scripts/analysis/industry_iv_second_settlement.py

Candidates C1 (realised wind speed, predictors without realised wind), B0 (bid-curve instruments d_dpw, d_dps), B1 (B0 / hour sd in 2019), B2 (B0 + B0 x lagged offer-curve slope); B0-B2 residualised with the
predictor set plus realised-wind and offer-curve controls. Placebo outcome residualised WITHOUT its own lag (the first settlement's flaw). No elasticity on the real outcome is computed.
Same common sample, blocks, 1,000 permutations (seed 20261117), idle-wind rule (national mean speed below 5 m/s in both weeks) as industry_iv_instrument_settlement.py.
Writes outputs/tables/industry_iv_second_settlement{,_rules,_f3,_joint}.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_estimation as E  # noqa: E402
import industry_iv_instrument_settlement as S  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import tou_did as T  # noqa: E402

NPERM, SEED = 1000, N.SEED


def predictors(d, extended):
    cols = [d.hour, d.dow, d.date.dt.month, d.date.dt.dayofyear, d.d_temp, d.d_dem, d.d_lnL_7, d.d_lnL_14, d.d_lnL_28, d.d_p_7, d.d_p_14, d.d_p_28, d.gas]
    if extended:
        g = d.groupby("date")
        cols += [d.d_wr, d.d_sr, d.wr, d.sr, g.wr.transform("mean"), g.sr.transform("mean"), d.slope, d.a0, g.slope.transform("mean"), g.a0.transform("mean")]
    return np.column_stack(cols)


def residualise(d, extended, Zdict):
    X = predictors(d, extended)
    order = d.date.rank(method="dense").to_numpy()
    blocks = np.minimum((order / order.max() * 10).astype(int), 9)
    names = ["y", "p"] + list(Zdict)
    Y = np.column_stack([np.asarray(d.d_lnL, float), np.asarray(d.d_p, float)] + [np.asarray(v, float) for v in Zdict.values()])
    R = dict(zip(names, N.gb_resid(Y, X, blocks, d.date.to_numpy()).T))
    keep = [i for i in range(X.shape[1]) if i != 6]  # drop d_lnL_7, the placebo outcome
    R["yplac"] = N.gb_resid(np.asarray(d.d_lnL_7, float)[:, None], X[:, keep], blocks, d.date.to_numpy())[:, 0]
    print(f"  placebo residual sd {R['yplac'].std():.4f} vs raw {d.d_lnL_7.std():.4f}; real outcome residual sd {R['y'].std():.4f}", flush=True)
    return R


def block_masks(d):
    hy = np.where(d.date < "2021-07-01", "2019-21H1", "2021H2-23")
    return {"full": np.ones(len(d), bool), "2019-21H1": hy == "2019-21H1", "2021H2-23": hy == "2021H2-23"}


def score(d, R, cand, zkeys, srcs):
    Zf = np.column_stack([R[k] for k in zkeys])
    rows = []
    for bn, mask in block_masks(d).items():
        sub = E.Sub(d, R["yplac"], R["p"], Zf, mask, list(range(Zf.shape[1])))
        sub.Zfull = Zf
        F = sub.first_stage_F(sub.Z0)
        b0 = np.linalg.solve(sub.Z0.T @ sub.Z0, sub.Z0.T @ sub.p)
        beta, se = sub.fast(sub.Z0)
        tp = np.array([(lambda r: r[0] / r[1])(sub.fast(E.Z_full_perm(sub, s))) for s in srcs])
        rows.append(dict(candidate=cand, block=bn, F1=F, partial_R2=float(1 - np.var(sub.p - sub.Z0 @ b0) / np.var(sub.p)), n=len(sub.idx), placebo_slope=beta,
                         placebo_p=(1 + np.sum(np.abs(tp) >= abs(beta / se))) / (NPERM + 1)))
    return rows


def f3(d, R, cand, zkey, srcs):
    idle = ((d.ws < S.IDLE_WS) & (d.ws7 < S.IDLE_WS)).to_numpy()
    z, p = R[zkey], R["p"]
    idx = np.flatnonzero(idle)
    st = E.starts_of(d.date.to_numpy()[idx])
    b_i, t_i = S.t_slope(p[idx], z[idx], st)
    b_f, _ = S.t_slope(p, z, E.starts_of(d.date.to_numpy()))
    tp = np.array([S.t_slope(p[idx], z[s[idx]], st)[1] for s in srcs])
    return dict(candidate=cand, f3_rows=int(len(idx)), f3_coef_idle=b_i, f3_coef_full=b_f, f3_ratio=b_i / b_f, f3_p=(1 + np.sum(np.abs(tp) >= abs(t_i))) / (NPERM + 1),
                f3_status="tested" if len(idx) >= S.MIN_IDLE else "too few rows")


def incremental_F(p, Za, Zb, d):
    """Clustered Wald F of Zb's coefficients in the first stage of p on [Za, Zb]."""
    Z = np.column_stack([Za, Zb])
    b = np.linalg.solve(Z.T @ Z, Z.T @ p)
    e = p - Z @ b
    st = E.starts_of(d.date.to_numpy())
    A = np.linalg.inv(Z.T @ Z)
    sc = np.add.reduceat(Z * e[:, None], st, axis=0)
    V = A @ (sc.T @ sc) @ A
    k = Za.shape[1]
    bb = b[k:]
    return float(bb @ np.linalg.inv(V[k:, k:]) @ bb / Zb.shape[1])


def main():
    d = S.build_frame()
    assert d.date.is_monotonic_increasing
    srcs = E.perm_sources(d, np.random.default_rng(SEED), NPERM)
    slz = d.slope7z
    print("home set of C1 (no realised wind)", flush=True)
    Z1 = {"d_pc": d.d_pc, "d_pc2": d.d_pc ** 2}
    # B instruments are also residualised in C1's home set, only for the joint check J(a)
    B0raw = {"d_dpw": d.d_dpw, "d_dps": d.d_dps}
    R1 = residualise(d, False, {**Z1, **{f"B0raw:{k}": v for k, v in B0raw.items()}})
    print("home set of B (with realised wind and offer-curve controls)", flush=True)
    ZB = {"B0:d_dpw": d.d_dpw, "B0:d_dps": d.d_dps, "B1:w": d.c2w, "B1:s": d.c2s, "B2:iw": d.d_dpw * slz, "B2:is": d.d_dps * slz, "C1x:d_pc": d.d_pc, "C1x:d_pc2": d.d_pc ** 2}
    RB = residualise(d, True, ZB)
    rows = score(d, R1, "C1", ["d_pc", "d_pc2"], srcs)
    rows += score(d, RB, "B0", ["B0:d_dpw", "B0:d_dps"], srcs)
    rows += score(d, RB, "B1", ["B1:w", "B1:s"], srcs)
    rows += score(d, RB, "B2", ["B0:d_dpw", "B0:d_dps", "B2:iw", "B2:is"], srcs)
    F3 = pd.DataFrame([f3(d, R1, "C1", "d_pc", srcs), f3(d, RB, "B0", "B0:d_dpw", srcs), f3(d, RB, "B1", "B1:w", srcs), f3(d, RB, "B2", "B0:d_dpw", srcs)])
    R = pd.DataFrame(rows)
    R.round(5).to_csv(T.OUT / "industry_iv_second_settlement.csv", index=False)
    F3.round(5).to_csv(T.OUT / "industry_iv_second_settlement_f3.csv", index=False)
    out = []
    for c in ("C1", "B0", "B1", "B2"):
        r = R[R.candidate == c].set_index("block")
        f = F3[F3.candidate == c].iloc[0]
        s1 = bool(r.loc["full", "F1"] >= 20 and r.loc["2019-21H1", "F1"] >= 10 and r.loc["2021H2-23", "F1"] >= 10)
        s2 = bool(all(r.loc[b, "placebo_p"] > 0.10 for b in ("full", "2019-21H1", "2021H2-23")))
        s3 = bool(f.f3_status == "tested" and f.f3_p > 0.05 and abs(f.f3_ratio) <= 0.5)
        out.append(dict(candidate=c, S1=s1, S2=s2, S3=s3, passes=s1 and s2 and s3, minF=float(min(r.loc["2019-21H1", "F1"], r.loc["2021H2-23", "F1"]))))
    Q = pd.DataFrame(out)
    Q.to_csv(T.OUT / "industry_iv_second_settlement_rules.csv", index=False)
    # J: first stage only, in each home set
    best = Q[(Q.candidate != "C1") & Q.passes].sort_values(["minF"], ascending=False)
    Bz = {"B0": ["B0:d_dpw", "B0:d_dps"], "B1": ["B1:w", "B1:s"], "B2": ["B0:d_dpw", "B0:d_dps", "B2:iw", "B2:is"]}
    J = []
    for c in (best.candidate.tolist() if len(best) else list(Bz)):
        za1 = np.column_stack([R1["d_pc"], R1["d_pc2"]])
        zb_in_c1 = np.column_stack([R1["B0raw:d_dpw"], R1["B0raw:d_dps"]])
        zbB = np.column_stack([RB[k] for k in Bz[c]])
        zc1B = np.column_stack([RB["C1x:d_pc"], RB["C1x:d_pc2"]])
        J.append(dict(candidate=c, passes_rules=bool(c in best.candidate.tolist()), incF_B_over_C1_in_C1set_raw_B0=incremental_F(R1["p"], za1, zb_in_c1, d),
                      incF_C1_over_B_in_Bset=incremental_F(RB["p"], zbB, zc1B, d)))
    JJ = pd.DataFrame(J)
    JJ.round(4).to_csv(T.OUT / "industry_iv_second_settlement_joint.csv", index=False)
    pd.set_option("display.width", 250)
    print(R.round(4).to_string(index=False))
    print(F3.round(4).to_string(index=False))
    print(Q.round(3).to_string(index=False))
    print(JJ.round(3).to_string(index=False))
    print("done")


if __name__ == "__main__":
    main()
