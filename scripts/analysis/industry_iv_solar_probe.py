"""docs/specs/2026-11-18-industry-iv-solar-channel-probe-design.md (rules P1-P4).

    .venv/bin/python scripts/analysis/industry_iv_solar_probe.py

Reduced forms of the wind-shape (W1) and solar (S1) instruments on the week-on-week change in ln(L_E / L_M) of the metered load of the interruptibility-service participants (ESIOS 836-846), 2019, plants with a
contractual consumption floor. No price enters. Learner N2 (OLS), 1,000 permutations across days within year-month, seed 20261117, randomization interval by test inversion (`run_sub` with the instrument as
its own regressor, scale 1). Benchmark direct effect D = (slope_S1 - slope_W1) x pi_S with the slopes read from outputs/tables/industry_iv_price_shape_primary_N2.csv (W1 and S1-only rows of the primary
step 1, slope = -sigma) and pi_S the first-stage coefficient of the price-ratio change on S1 (primary sample, N2 residuals). P1 plants D into the probe outcome and requires detection and recovery of the S1
reduced form; P2 (W1 reduced form p above 0.05); P3 (S1 reduced form detected with the sign of D); P4 context (aggregate E3-E6 reduced forms in 2019). Writes
outputs/tables/industry_iv_solar_probe.csv and industry_iv_solar_probe_checks.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import industry_iv_day_level as DL  # noqa: E402
import industry_iv_estimation as E  # noqa: E402
import industry_iv_metered as M  # noqa: E402
import industry_iv_noise_reducers as N  # noqa: E402
import industry_iv_price_shape as PS  # noqa: E402
import tou_did as T  # noqa: E402


class RFSub(E.Sub):
    """Reduced form: the instrument is its own regressor, so the first stage is exact and its F is undefined."""

    def first_stage_F(self, Z):
        return float("nan")


def rf(d, y, z, srcs, mask=None):
    """Reduced form: slope of residualised y on residualised z (z is its own instrument), randomization interval."""
    m = np.ones(len(d), bool) if mask is None else mask
    sub = RFSub(d, y, z, z[:, None], m, [0])
    sub.Zfull = z[:, None]
    r, _ = E.run_sub(sub, srcs, 1.0)
    return dict(slope=r["elasticity"], lo=r["rand_lo"], hi=r["rand_hi"], p_t_rank=r["p_t_rank"], n=r["n"])


def detected(r):
    return bool(r["p_t_rank"] <= 0.05 and (r["lo"] > 0 or r["hi"] < 0))


def main():
    # ---- benchmark D (instrument-step quantities only)
    sl = pd.read_csv(T.OUT / "industry_iv_price_shape_primary_N2.csv")
    s_w1 = -float(sl[(sl.variant == "primary (W1)") & (sl.block == "full")].sigma.iloc[0])
    s_s1 = -float(sl[(sl.variant == "S1 only") & (sl.block == "full")].sigma.iloc[0])
    cfg0, d0, X0, R0, srcs0, XL0 = PS.build("primary", "N2")
    pi_s = float(R0["s"] @ R0["x"] / (R0["s"] @ R0["s"]))
    D = (s_s1 - s_w1) * pi_s
    print(f"slope_S1 {s_s1:.4f}, slope_W1 {s_w1:.4f}, pi_S {pi_s:.4f}  ->  D = {D:.5f} log-ratio points per sd of S1", flush=True)

    # ---- probe frame: interruptible load, 2019
    load = M.interruptible_hourly()
    df = DL.hourly_base(load=load, end="2023-12-31")
    cfg = dict(PS.SAMPLES["primary"], first=M.FIRST, last=M.LAST)
    d = PS.shape_frame(PS.shape_days(df), cfg)
    XL = PS.lin_matrix(d)
    bl, dates = DL.blocks_of(d), d.date.to_numpy()
    Y = np.column_stack([d.d_y, d.d_w, d.d_s]).astype(float)
    R = PS.resid(Y, XL, XL, bl, dates, "N2")
    Ry, Rw, Rs = R[:, 0], R[:, 1], R[:, 2]
    srcs = E.perm_sources(d, np.random.default_rng(N.SEED), E.NPERM)
    print(f"probe sample {len(d)} days {d.date.min().date()} -> {d.date.max().date()}", flush=True)

    rows = []
    # P1 power: plant D (direct, no price) into the probe outcome, refit residual
    yp = np.asarray(d.d_y, float) + D * np.asarray(d.d_s, float)
    Ryp = PS.resid(yp[:, None], XL, XL, bl, dates, "N2")[:, 0]
    p1 = rf(d, Ryp, Rs, srcs)
    rows.append(dict(item="S1 reduced form, planted D", outcome="interruptible 2019", planted=D, **p1))
    rec = bool(p1["lo"] <= D <= p1["hi"])
    # real reduced forms on the probe outcome
    w = rf(d, Ry, Rw, srcs)
    s = rf(d, Ry, Rs, srcs)
    rows += [dict(item="W1 reduced form", outcome="interruptible 2019", planted=np.nan, **w), dict(item="S1 reduced form", outcome="interruptible 2019", planted=np.nan, **s)]
    # P4 context: aggregate E3-E6 reduced forms, same year
    m19 = (d0.date.dt.year == 2019).to_numpy()
    for nm, zk in (("W1", "w"), ("S1", "s")):
        a = rf(d0, R0["y"], R0[zk], srcs0, m19)
        rows.append(dict(item=f"{nm} reduced form", outcome="aggregate E3-E6 2019", planted=np.nan, **a))
    P = pd.DataFrame(rows)
    P.round(6).to_csv(T.OUT / "industry_iv_solar_probe.csv", index=False)

    ch = [("P1 power: planted D detected and recovered", bool(detected(p1) and rec), f"D {D:.5f}; est {p1['slope']:.5f} [{p1['lo']:.5f},{p1['hi']:.5f}], p {p1['p_t_rank']:.3f}")]
    ch.append(("P2 wind is clean (W1 reduced form p above 0.05)", bool(w["p_t_rank"] > 0.05), f"W1 {w['slope']:.5f} [{w['lo']:.5f},{w['hi']:.5f}], p {w['p_t_rank']:.3f}"))
    ch.append(("P3 solar direct effect present (S1 detected, sign of D)", bool(detected(s) and np.sign(s["slope"]) == np.sign(D)), f"S1 {s['slope']:.5f} [{s['lo']:.5f},{s['hi']:.5f}], p {s['p_t_rank']:.3f}; sign of D {np.sign(D):+.0f}"))
    agg = P[P.outcome == "aggregate E3-E6 2019"]
    ch.append(("P4 context (no pass/fail)", None, "; ".join(f"{r.item} on aggregate: {r.slope:.5f} [{r.lo:.5f},{r.hi:.5f}]" for r in agg.itertuples()) + f"; D {D:.5f}"))
    C = pd.DataFrame(ch, columns=["rule", "pass", "detail"])
    C.to_csv(T.OUT / "industry_iv_solar_probe_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 250)
    print(P[["item", "outcome", "planted", "slope", "lo", "hi", "p_t_rank", "n"]].round(5).to_string(index=False))
    print(C.to_string(index=False))


if __name__ == "__main__":
    main()
